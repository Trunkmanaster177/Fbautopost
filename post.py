
import os
import json
import random
import time
import requests
from cards import make_card

PAGE_ID = os.environ["FB_PAGE_ID"]
PAGE_TOKEN = os.environ["FB_PAGE_TOKEN"]
API_KEY = os.environ["GEMINI_API_KEY"]

NICHE = os.environ.get(
    "NICHE", "personal finance and money-saving tips for beginners"
)
PAGE_NAME = os.environ.get("PAGE_NAME", "")

# A supported model; can be overridden by the GitHub Actions MODEL variable.
MODEL = os.environ.get("MODEL", "gemini-3.5-flash-lite").strip()

MAX_DELAY_MIN = int(os.environ.get("MAX_DELAY_MIN", "90"))
USE_AI_BG = os.environ.get("USE_AI_BG", "1") == "1"
HISTORY = "history.json"

FORMATS = {
    "tips": (
        '"label":"MONEY TIP",'
        '"headline":"max 8 words, a hook",'
        '"points":["3 tips, max 9 words each"]'
    ),
    "myth_fact": (
        '"headline":"max 6 words about a money myth",'
        '"myth":"a common wrong belief, max 16 words",'
        '"fact":"the truth, max 22 words"'
    ),
    "big_stat": (
        '"label":"MONEY RULE",'
        '"big_text":"a famous rule of thumb or simple number, max 3 words",'
        '"headline":"one sentence explaining it, max 14 words"'
    ),
}


def load_history():
    try:
        with open(HISTORY, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def generate(history, fmt):
    recent = [h["topic"] for h in history[-40:]]

    prompt = f"""
You run a Facebook Page in the niche: {NICHE}.

Create ONE original post on a NEW topic, avoiding these recent topics:
{recent}

Rules:
- General educational tips only.
- No guaranteed returns or specific stock/crypto picks.
- Do not invent statistics.
- Keep card text short and punchy.
- "image_prompt": vivid, realistic background photo description.
  Use objects, scenery or hands; no text or faces.
- "post": 80-150 words, first line has a searchable keyword,
  short paragraphs, ends with a question inviting comments,
  then 3-5 relevant hashtags.

Return ONLY valid JSON with these keys:
"topic", "image_prompt", "post", {FORMATS[fmt]}
"""

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{MODEL}:generateContent"
    )

    try:
        response = requests.post(
            url,
            params={"key": API_KEY},
            json={
                "contents": [
                    {"parts": [{"text": prompt}]}
                ],
                "generationConfig": {
                    "responseMimeType": "application/json"
                },
            },
            timeout=60,
        )

        if not response.ok:
            raise RuntimeError(
                f"Gemini API error: HTTP {response.status_code}\n"
                f"Model: {MODEL}\n"
                f"Response: {response.text[:2000]}"
            )

        data = response.json()
        candidates = data.get("candidates", [])

        if not candidates:
            raise RuntimeError(
                f"Gemini returned no candidates: {json.dumps(data)[:2000]}"
            )

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()

        if not text:
            raise RuntimeError(
                f"Gemini returned empty text: {json.dumps(data)[:2000]}"
            )

        item = json.loads(text)

        for key in ("topic", "image_prompt", "post"):
            if not item.get(key):
                raise RuntimeError(
                    f"Gemini response is missing required field: {key}"
                )

        return item

    except requests.RequestException as exc:
        raise RuntimeError(f"Could not connect to Gemini API: {exc}") from exc


def post_photo(image, caption):
    url = f"https://graph.facebook.com/v21.0/{PAGE_ID}/photos"

    response = requests.post(
        url,
        data={
            "caption": caption,
            "access_token": PAGE_TOKEN,
        },
        files={
            "source": ("card.jpg", image, "image/jpeg")
        },
        timeout=120,
    )

    if not response.ok:
        raise RuntimeError(
            f"Facebook API error: HTTP {response.status_code}\n"
            f"Response: {response.text[:2000]}"
        )

    result = response.json()
    print("Facebook response:", json.dumps(result))
    return result


if __name__ == "__main__":
    delay = random.randint(0, MAX_DELAY_MIN * 60)
    print(f"Sleeping {delay // 60} min for a random post time...")
    time.sleep(delay)

    history = load_history()
    fmt = random.choice(list(FORMATS))

    print(f"Generating post using Gemini model: {MODEL}")
    item = generate(history, fmt)

    print("Creating post card...")
    card = make_card(item, fmt, PAGE_NAME, USE_AI_BG)

    print("Publishing to Facebook...")
    result = post_photo(card, item["post"])

    history.append({
        "topic": item["topic"],
        "id": result.get("post_id") or result.get("id"),
        "ts": int(time.time()),
    })

    with open(HISTORY, "w", encoding="utf-8") as f:
        json.dump(history[-200:], f, indent=2, ensure_ascii=False)

    print("Post published and history saved successfully.")
