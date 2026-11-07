# AI Mountain Man

A tiny 8-bit robot jumps across one pair of mountains per day: how often people post, look up and talk about **artificial intelligence** vs **superintelligence**.

Live: https://smritajain31.github.io/ai-mountain-man/

| Level | What it counts | Split | Refresh |
|---|---|---|---|
| Live wire | Every new public Bluesky post (Jetstream) + new Hacker News items | By language | Seconds, while the page is open |
| 1 · Bluesky | Daily estimates from a 30-minute Jetstream sample every hour | All languages or English | Hourly via GitHub Action |
| 2 · Wiki | Human views of the English Wikipedia articles | None | Hourly, one day behind |
| 3 · HN | Hacker News posts and comments (Algolia) | None | Every 60 s |

Cost: $0. Static GitHub Pages, a scheduled GitHub Action (`.github/workflows/update-data.yml` runs `sample_bluesky.py`), and keyless public APIs.

GitHub pauses scheduled workflows after 60 days without repo activity. Re-enable it from the Actions tab if the Bluesky level stops updating.
