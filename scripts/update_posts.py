import html
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

FEED_URL = "https://techcrunch.com/feed/"
OUTPUT = "data/posts.json"
QUEUE_OUTPUT = "data/pending.json"
USER_AGENT = "TECHNEWS_404/1.0 (+https://github.com/rutaabali3/TECHNEWS_404)"
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MAX_BATCH_PER_RUN = int(os.getenv("MAX_BATCH_PER_RUN", "10"))


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
    for item in root.findall(".//item")[:50]:
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
    return {**item, "title": title, "image": image, "author": author, "description": description, "body": body[:7000]}


def summarize(article, api_key):
    prompt = f"""Create a thorough and accurate news summary of the TechCrunch article below.
Return only one valid JSON object and nothing else. Do not use Markdown fences, commentary, or trailing commas.
The object must contain exactly these keys: summary, key_points, topics.
summary must be 3-4 clear, complete, and informative sentences covering the core news, essential details, background context, and significance. Ensure sentences are complete and do not end abruptly.
key_points must be an array of 2-4 clear, factual takeaway strings.
topics must be an array of 2-5 relevant lowercase topic labels.
Use ordinary double-quoted JSON strings and escape internal quotation marks properly.
Keep names, companies, dates, metrics, and numbers accurate.

TITLE: {article['title']}
AUTHOR: {article['author']}
ARTICLE TEXT:
{article['body']}"""
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.2,
        "max_tokens": 750,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You are a senior technology-news editor providing complete and high-quality summaries. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    endpoint = "https://api.groq.com/openai/v1/chat/completions"
    for attempt in range(3):
        response = requests.post(endpoint, headers=headers, json=payload, timeout=90)
        if response.status_code == 400:
            try:
                error = response.json().get("error", {})
            except ValueError:
                error = {}
            if error.get("code") == "json_validate_failed" and "response_format" in payload:
                # Some Groq/model combinations reject strict JSON mode even when the
                # generated content is recoverable. Retry once in plain text mode and
                # parse the model's JSON ourselves below.
                fallback_payload = dict(payload)
                fallback_payload.pop("response_format", None)
                response = requests.post(endpoint, headers=headers, json=fallback_payload, timeout=90)
            if response.status_code == 400:
                try:
                    detail = response.json().get("error", {}).get("message", "Bad request")
                except ValueError:
                    detail = response.text[:300] or "Bad request"
                raise RuntimeError(f"Groq request rejected: {detail}")
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            try:
                delay = max(2, min(30, float(retry_after))) if retry_after else 5 * (attempt + 1)
            except ValueError:
                delay = 5 * (attempt + 1)
            if attempt < 2:
                time.sleep(delay)
                continue
            raise RuntimeError("Groq rate limit reached after retries; article remains queued")
        response.raise_for_status()
        content = response.json()["choices"][0]["message"].get("content", "").strip()
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE).strip()
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            start, end = content.find("{"), content.rfind("}")
            if start >= 0 and end > start:
                try:
                    result = json.loads(content[start:end + 1])
                except json.JSONDecodeError:
                    result = None
            else:
                result = None
            if result is None:
                match = re.search(r'"summary"\s*:\s*"((?:\\.|[^"\\])*)', content, flags=re.DOTALL)
                if match:
                    try:
                        extracted = json.loads('"' + match.group(1) + '"')
                    except json.JSONDecodeError:
                        extracted = match.group(1).replace('\\"', '"')
                    result = {"summary": extracted, "key_points": [], "topics": ["technology"]}
                else:
                    result = {"summary": content, "key_points": [], "topics": ["technology"]}
        if not result.get("summary"):
            result = {"summary": article.get("description") or article.get("feed_excerpt") or "Summary unavailable; open the original article for details.", "key_points": [], "topics": ["technology"]}
        return result
    raise RuntimeError("Groq request failed")


def groq_keys():
    keys = []
    for index in range(1, 6):
        value = re.sub(r"\s+", "", os.getenv(f"GROQ_API_KEY_{index}", ""))
        if value:
            keys.append(value)
    if not keys:
        legacy = re.sub(r"\s+", "", os.getenv("GROQ_API_KEY", ""))
        if legacy:
            keys.append(legacy)
    return keys


def process_item(item, api_key):
    article = extract_article(item)
    generated = summarize(article, api_key)
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


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def parse_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def save_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    existing = load_json(OUTPUT, {"updated_at": None, "source": "TechCrunch", "posts": []})
    queue_data = load_json(QUEUE_OUTPUT, {"updated_at": None, "items": []})
    queue = queue_data.get("items", [])
    original_queue = list(queue)
    previous_last_processed_at = queue_data.get("last_processed_at")
    keys = groq_keys()
    if not keys:
        raise RuntimeError("No Groq API key configured. Add GROQ_API_KEY_1 or GROQ_API_KEY.")
    for key in keys:
        if not key.startswith("gsk_"):
            raise RuntimeError("Every Groq key must begin with gsk_.")

    known = {post.get("source_url") for post in existing.get("posts", [])} | {item.get("url") for item in queue}
    discovered = 0
    for item in parse_feed():
        if item["url"] not in known:
            queue.append(item)
            known.add(item["url"])
            discovered += 1
    queue = queue[:200]
    now = datetime.now(timezone.utc)
    last_processed_at = parse_timestamp(queue_data.get("last_processed_at"))
    print(f"Queue contains {len(queue)} item(s); discovered {discovered} new feed item(s).")

    fresh = []
    processed_count = 0
    while queue and processed_count < MAX_BATCH_PER_RUN:
        item = queue[0]
        key = keys[processed_count % len(keys)]
        try:
            processed = process_item(item, key)
            fresh.append(processed)
            queue.pop(0)
            last_processed_at = datetime.now(timezone.utc)
            processed_count += 1
            print(f"Summarized ({processed_count}/{MAX_BATCH_PER_RUN}): {item['url']}")
        except Exception as exc:
            print(f"Stopping batch due to error processing {item['url']}: {exc}", file=sys.stderr)
            break

    if fresh:
        fresh.sort(key=lambda post: post.get("published", ""), reverse=True)
        existing["posts"] = (fresh + existing.get("posts", []))[:100]
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_json(OUTPUT, existing)
    queue_payload = {"updated_at": now.isoformat(), "items": queue}
    if last_processed_at:
        queue_payload["last_processed_at"] = last_processed_at.isoformat()
    queue_changed = queue != original_queue
    cooldown_state_changed = (queue_payload.get("last_processed_at") or None) != (previous_last_processed_at or None)
    if queue_changed or cooldown_state_changed:
        save_json(QUEUE_OUTPUT, queue_payload)
    print(f"Added {len(fresh)} post(s); {len(queue)} item(s) remain queued.")


if __name__ == "__main__":
    main()
