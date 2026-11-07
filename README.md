# AI Mountain Man

A tiny 8-bit robot jumps across one pair of mountains per day: how often the world writes, looks up and talks about **artificial intelligence** vs **superintelligence**.

Live: https://smritajain31.github.io/ai-mountain-man/

| Level | What it counts | Where | Refresh |
|---|---|---|---|
| 1 · News | News articles containing each term (GDELT) | World or USA | Every 30 min via GitHub Action |
| 2 · Wiki | Human views of the English Wikipedia articles | Global | Hourly, one day behind |
| Live wire | Every new public Bluesky post (Jetstream) + new Hacker News items | Global, by language | Seconds, while the page is open |
| 3 · HN | Hacker News posts and comments (Algolia) | Global | Every 60 s |

Cost: $0. Static GitHub Pages, a scheduled GitHub Action (`.github/workflows/update-data.yml` runs `fetch_gdelt.py`), and keyless public APIs.

Note: GitHub pauses scheduled workflows after 60 days without repo activity. Re-enable it from the Actions tab if the news level stops updating.
