import requests
import feedparser
import os
import json
import datetime

RSS_URL = "https://techcrunch.com/feed/"
PROCESSED_LINKS_PATH = "processed_links.txt"
MAX_ARTICLES_PER_RUN = 10
CATEGORIES = ["AI", "Product", "Funding", "Security", "Other"]

NOTION_VERSION = "2022-06-28"


def load_processed_links():
    if not os.path.exists(PROCESSED_LINKS_PATH):
        return set()

    with open(PROCESSED_LINKS_PATH, "r") as f:
        lines = f.readlines()

    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def append_processed_link(link):
    with open(PROCESSED_LINKS_PATH, "a") as f:
        f.write(link + "\n")


def get_new_articles():
    feed = feedparser.parse(RSS_URL)
    processed = load_processed_links()

    new_articles = []
    for entry in feed.entries:
        link = entry.get("link", "")
        if not link or link in processed:
            continue

        new_articles.append({
            "title": entry.get("title", "Untitled"),
            "link": link,
            "summary": entry.get("summary", ""),
            "published": entry.get("published", ""),
        })

        if len(new_articles) >= MAX_ARTICLES_PER_RUN:
            break

    return new_articles


def summarize_and_categorize(article, api_key):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"

    prompt = f"""Summarize the following tech news article in 1-2 concise sentences,
and classify it into exactly one of these categories: {", ".join(CATEGORIES)}.

Title: {article['title']}
Raw content: {article['summary'][:1000]}

Respond ONLY with a JSON object in this exact shape, no other text:
{{
  "summary": "<1-2 sentence summary>",
  "category": "<one of: {", ".join(CATEGORIES)}>"
}}"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    result = json.loads(text)

    if result.get("category") not in CATEGORIES:
        result["category"] = "Other"

    return result


def parse_published_date(published_str):
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(published_str)
        return dt.date().isoformat()
    except Exception:
        return datetime.date.today().isoformat()


def add_to_notion(article, summary, category, notion_token, database_id):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": article["title"][:200]}}]},
            "Summary": {"rich_text": [{"text": {"content": summary[:2000]}}]},
            "Category": {"select": {"name": category}},
            "URL": {"url": article["link"]},
            "Published": {"date": {"start": parse_published_date(article["published"])}},
        },
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()


def main():
    gemini_key = os.environ["GEMINI_API_KEY"]
    notion_token = os.environ["NOTION_TOKEN"]
    database_id = os.environ["NOTION_DATABASE_ID"]

    new_articles = get_new_articles()
    print(f"Found {len(new_articles)} new article(s) to process.")

    for article in new_articles:
        try:
            result = summarize_and_categorize(article, gemini_key)
            add_to_notion(article, result["summary"], result["category"], notion_token, database_id)
            append_processed_link(article["link"])
            print(f"Added: {article['title']}")
        except Exception as e:
            print(f"Failed to process '{article['title']}': {e}")

    print("Done.")


if __name__ == "__main__":
    main()
