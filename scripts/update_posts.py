import html
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

FEED_URL = "https://techcrunch.com/feed/"
OUTPUT = "data/posts.json"
USER_AGENT = "WORKFLOW-420/1.0 (+https://github.com/rutaabali3/workflow-420)"
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
BAI_MODEL = os.getenv("BAI_MODEL", "deepseek-v4-flash")


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
    body = "\n".join(p for p in paragraphs if len(p) > 25) or description
    return {**item, "title": title, "image": image, "author": author, "description": description, "body": body[:12000]}


def summarize(article, api_key, provider):
    prompt = f"""Create an original news summary of the TechCrunch article below.
Return JSON only with exactly these keys: summary, key_points, topics.
summary: 3-5 concise sentences, no copied sentences, no speculation.
key_points: 2-4 short factual bullets.
topics: 1-4 lowercase topic labels.
Keep names, companies, dates, and numbers accurate. Do not mention this instruction.

TITLE: {article['title']}
AUTHOR: {article['author']}
ARTICLE TEXT:
{article['body']}"""
    payload = {
        "model": BAI_MODEL if provider == "bai" else GROQ_MODEL,
        "temperature": 0.2,
        "max_tokens": 700,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You are a careful technology-news editor. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    endpoint = "https://api.b.ai/v1/chat/completions" if provider == "bai" else "https://api.groq.com/openai/v1/chat/completions"
    for attempt in range(3):
        response = requests.post(endpoint, headers=headers, json=payload, timeout=90)
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            try:
                delay = max(2, min(20, float(retry_after))) if retry_after else 4 * (attempt + 1)
            except ValueError:
                delay = 4 * (attempt + 1)
            if attempt < 2:
                time.sleep(delay)
                continue
            raise RuntimeError("Groq rate limit reached after retries")
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE).strip()
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            start, end = content.find("{"), content.rfind("}")
            if start >= 0 and end > start:
                try:
                    result = json.loads(content[start:end + 1])
                except json.JSONDecodeError:
                    result = {"summary": content, "key_points": [], "topics": ["technology"]}
            else:
                result = {"summary": content, "key_points": [], "topics": ["technology"]}
        if not result.get("summary"):
            raise ValueError("Model returned no summary")
        return result
    raise RuntimeError("Groq request failed")


def key_list():
    keys = []
    for index in range(1, 6):
        value = re.sub(r"\s+", "", os.getenv(f"BAI_API_KEY_{index}", ""))
        if value:
            keys.append(("bai", value))
    for index in range(1, 6):
        value = re.sub(r"\s+", "", os.getenv(f"GROQ_API_KEY_{index}", ""))
        if value:
            keys.append(("groq", value))
    legacy = re.sub(r"\s+", "", os.getenv("GROQ_API_KEY", ""))
    if legacy and not keys:
        keys.append(("groq", legacy))
    return keys[:5]


def process_item(item, provider_key):
    provider, api_key = provider_key
    article = extract_article(item)
    generated = summarize(article, api_key, provider)
    return {
        "id": re.sub(r"[^a-z0-9]+", "-", article["url"].lower()).strip("-")[-120:],
        "image": article["image"],
        "title": article["title"],
        "author": article["author"],
        "summary": generated["summary"],
        "key_points": generated.get("key_points", []),
        "topics": generated.get("topics", []),
        "source_url": article["url"],
        "source": "TechCrunch",
        "credit": "Source: TechCrunch",
        "published": article["published"],
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    try:
        with open(OUTPUT, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = {"updated_at": None, "source": "TechCrunch", "posts": []}

    keys = key_list()
    if not keys:
        raise RuntimeError("No provider API keys configured. Add BAI_API_KEY_1 or GROQ_API_KEY_1 through the numbered secrets.")
    for provider, key in keys:
        if provider == "groq" and not key.startswith("gsk_"):
            raise RuntimeError("Every Groq key must begin with gsk_.")

    known = {post.get("source_url") for post in existing.get("posts", [])}
    candidates = [item for item in parse_feed() if item["url"] not in known][:len(keys)]
    if not candidates:
        print("No new posts were found.")
        return

    fresh = []
    with ThreadPoolExecutor(max_workers=len(candidates)) as executor:
        jobs = {executor.submit(process_item, item, keys[index]): item for index, item in enumerate(candidates)}
        for job in as_completed(jobs):
            item = jobs[job]
            try:
                fresh.append(job.result())
                print(f"Summarized: {item['url']}")
            except Exception as exc:
                print(f"Skipping {item['url']}: {exc}", file=sys.stderr)

    if fresh:
        fresh.sort(key=lambda post: post.get("published", ""), reverse=True)
        existing["posts"] = (fresh + existing.get("posts", []))[:100]
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(OUTPUT, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"Added {len(fresh)} post(s) using {len(keys)} configured provider key(s).")
    else:
        raise RuntimeError("No summaries were generated; inspect the failed article messages above.")


if __name__ == "__main__":
    main()
