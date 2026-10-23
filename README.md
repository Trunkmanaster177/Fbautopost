# Facebook auto-post bot (free)
3 posts/day at random times via GitHub Actions. Gemini (free tier) writes the caption + card text,
Pillow draws the image card (tips / myth-vs-fact / big-number), Graph API posts it.

Secrets: FB_PAGE_ID, FB_PAGE_TOKEN, GEMINI_API_KEY
Variables: NICHE, PAGE_NAME
Optional env: USE_AI_BG=0 (gradient art only), MAX_DELAY_MIN (default 90)
Test: Actions tab -> "Facebook auto-post" -> Run workflow.
