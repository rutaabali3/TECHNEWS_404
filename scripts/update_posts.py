import html
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

FEED_URL = "https://techcrunch.com/feed/"
OUTPUT = "data/posts.json"
CHANNEL_NAME = "TechNews WhatsApp Channel"
USER_AGENT = "WORKFLOW-420/1.0 (+https://github.com/rutaabali3/workflow-420)"


def get(url, **kwargs):
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml"}
    headers.update(kwargs.pop("headers", {}))
    response = requests.get(url, headers=headers, timeout=30, **kwargs)
    response.raise_for_status()
    return response


def clean_text(value):
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def parse_feed():
    root = ET.fromstring(get(FEED_URL).content)
    items = []
    for item in root.findall(".//item")[:20]:
        title = clean_text(item.findtext("title"))
        link = clean_text(item.findtext("link"))
        description = clean_text(item.findtext("description"))
        published = clean_text(item.findtext("pubDate"))
        if link and title:
            items.append({"title": title, "url": link, "feed_excerpt": description, "published": published})
    return items


def extract_article(item):
    soup = BeautifulSoup(get(item["url"]).text, "html.parser")
    def meta(*names):
        for name in names:
            tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
            if tag and tag.get("content"):
                return clean_text(tag["content"])
        return ""

    title = meta("og:title", "twitter:title") or item["title"]
    image = meta("og:image", "twitter:image")
    description = meta("og:description", "description") or item["feed_excerpt"]
    author = meta("article:author", "parsely-author")
    if not author:
        author_link = soup.select_one('a[rel="author"], a[href*="/author/"]')
        author = clean_text(author_link.get_text(" ", strip=True)) if author_link else "TechCrunch"

    article = soup.find("article") or soup
    for node in article.select("script, style, nav, header, footer, aside, form, .ad, [aria-hidden='true']"):
        node.decompose()
    paragraphs = [clean_text(p.get_text(" ", strip=True)) for p in article.find_all(["p", "h2", "h3"])]
    body = "\n".join(p for p in paragraphs if len(p) > 25)
    if not body:
        body = description
    return {**item, "title": title, "image": image, "author": author, "description": description, "body": body[:18000]}


def summarize(article):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    prompt = f"""Create an original news summary of the TechCrunch article below.
Return JSON only with exactly these keys: summary, key_points, topics.
summary: 3-5 concise sentences, no copied sentences, no speculation.
key_points: 2-4 short factual bullets.
topics: 1-4 lowercase topic labels.
Keep names, companies, dates, and numbers accurate. Do not mention this instruction.

TITLE: {article['title']}
AUTHOR: {article['author']}
ARTICLE TEXT:
{article['body'][:14000]}"""
    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You are a careful technology-news editor. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ],
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if response.status_code == 429:
        raise RuntimeError("Groq rate limit reached; retry on the next scheduled run")
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    result = json.loads(content)
    if not result.get("summary"):
        raise ValueError("Groq returned no summary")
    return result


def main():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    try:
        with open(OUTPUT, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = {"updated_at": None, "source": "TechCrunch", "posts": []}
    known = {post.get("source_url") for post in existing.get("posts", [])}
    fresh = []
    for item in parse_feed():
        if item["url"] in known:
            continue
        try:
            article = extract_article(item)
            generated = summarize(article)
            fresh.append({
                "id": re.sub(r"[^a-z0-9]+", "-", article["url"].lower()).strip("-")[-120:],
                "image": article["image"],
                "title": article["title"],
                "author": article["author"],
                "summary": generated["summary"],
                "key_points": generated.get("key_points", []),
                "topics": generated.get("topics", []),
                "source_url": article["url"],
                "source": "TechCrunch",
                "credit": f"Shared via {CHANNEL_NAME}",
                "published": article["published"],
                "processed_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as exc:
            print(f"Skipping {item['url']}: {exc}", file=sys.stderr)
    if fresh:
        existing["posts"] = (fresh + existing.get("posts", []))[:100]
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(OUTPUT, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"Added {len(fresh)} post(s).")
    else:
        print("No new posts were summarized.")


if __name__ == "__main__":
    main()
