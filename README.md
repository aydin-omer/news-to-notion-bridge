# 🌉 News to Notion Bridge

An automated pipeline that turns a raw tech news feed into a categorized, summarized knowledge base in Notion — connecting three services with no manual work in between.

## What it does

Every Monday, this project automatically:

1. Fetches the latest articles from the **TechCrunch RSS feed**
2. Skips any article it has already processed (tracked in `processed_links.txt`)
3. Sends each new article to **Google's Gemini API**, asking it to write a 1-2 sentence summary and classify the article into one of five categories: `AI`, `Product`, `Funding`, `Security`, `Other`
4. Creates a new row in a **Notion database**, with the title, summary, category, source link, and publish date filled in
5. Records the article as processed, so it's never added twice

The result is a growing, organized Notion database of tech news — built and maintained without ever opening a browser.

## Why

This project demonstrates a common real-world integration pattern: **source → AI processing → destination**. Rather than just moving data from one system to another unchanged, an LLM sits in the middle to add real value — turning a raw, noisy feed into structured, categorized, digestible entries. The same pattern generalizes to countless other pipelines: support tickets into a triaged backlog, competitor announcements into a tracked log, customer feedback into a tagged database, and so on.

## How it works

- **Language:** Python
- **Automation:** [GitHub Actions](https://github.com/features/actions) scheduled workflow (cron job)
- **Source:** TechCrunch RSS feed
- **AI processing:** [Google Gemini API](https://ai.google.dev/) (`gemini-3.5-flash-lite`, free tier)
- **Destination:** [Notion API](https://developers.notion.com/) — a database (table) inside a Notion workspace
- **Deduplication:** a plain text file (`processed_links.txt`), committed back to the repo after each run
- **No server required** — runs entirely on GitHub's free infrastructure

## Architecture

```
.github/workflows/bridge.yml   → Runs weekly: fetch, summarize, write to Notion, commit
bridge.py                      → Fetches RSS, calls Gemini, writes to Notion, tracks processed links
processed_links.txt            → Growing list of article URLs already added to Notion
requirements.txt               → Python dependencies
```

## Setup

If you want to run your own copy of this bridge:

1. Fork or clone this repository
2. Create a free [Notion integration](https://www.notion.so/my-integrations) and copy its **Internal Integration Token**
3. Create a Notion database (as a full-page database, not an inline table) with these exact properties:
   - `Name` (Title — created by default)
   - `Summary` (Text)
   - `Category` (Select, with options: `AI`, `Product`, `Funding`, `Security`, `Other`)
   - `URL` (URL)
   - `Published` (Date)
4. Share that database with your integration: open the database → **Share** → search for and add your integration
5. Get the database ID: the most reliable way is to `POST` to `https://api.notion.com/v1/search` with your token and filter for `{"property": "object", "value": "database"}` — the `id` field in the response is the real database ID. (The ID in a Notion page URL is often the *page's* ID, not the database's, if the table lives inside a regular page.)
6. Go to **Settings → Secrets and variables → Actions** in this repo and add:

   | Secret | Description |
   |---|---|
   | `GEMINI_API_KEY` | A free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey) |
   | `NOTION_TOKEN` | Your Notion integration's Internal Integration Token |
   | `NOTION_DATABASE_ID` | The real database ID, found via the search API above |

7. That's it — the workflow runs automatically every Monday. You can also trigger it manually from the **Actions** tab using **Run workflow**.

## Customization

- **Change the source:** swap `RSS_URL` in `bridge.py` for any other RSS feed
- **Change the categories:** edit the `CATEGORIES` list in `bridge.py` (make sure the Notion `Category` select field has matching options)
- **Change the schedule:** edit the `cron` expression in `.github/workflows/bridge.yml` ([crontab.guru](https://crontab.guru/) is helpful for this)
- **Process more articles per run:** adjust `MAX_ARTICLES_PER_RUN` in `bridge.py`

## Notes

- All credentials are stored securely as GitHub Actions secrets — nothing is hardcoded in the source code.
- If a single article fails to process (a bad summary, a Notion API hiccup), the script logs the failure and continues with the rest rather than stopping the whole run.
- Notion's database ID is easy to get wrong: URLs for tables embedded inside a regular page often show the *page's* ID rather than the database's own ID, which causes a `"is a page, not a database"` error from the API. The search-API method in Setup step 5 avoids this ambiguity entirely.
