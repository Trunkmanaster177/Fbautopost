import os, json, random, time, requests
from cards import make_card

PAGE_ID = os.environ["FB_PAGE_ID"]
PAGE_TOKEN = os.environ["FB_PAGE_TOKEN"]
API_KEY = os.environ["GEMINI_API_KEY"]
NICHE = os.environ.get("NICHE", "personal finance and money-saving tips for beginners")
PAGE_NAME = os.environ.get("PAGE_NAME", "")
MODEL = os.environ.get("MODEL", "gemini-2.5-flash")
MAX_DELAY_MIN = int(os.environ.get("MAX_DELAY_MIN", "90"))
USE_AI_BG = os.environ.get("USE_AI_BG", "1") == "1"
HISTORY = "history.json"
def load_history():
    try:
        return json.load(open(HISTORY))
    except Exception:
        return []

FORMATS = {
    "tips": '"label":"MONEY TIP","headline":"max 8 words, a hook","points":["3 tips, max 9 words each"]',
    "myth_fact": '"headline":"max 6 words about a money myth","myth":"a common wrong belief, max 16 words","fact":"the truth, max 22 words"',
    "big_stat": '"label":"MONEY RULE","big_text":"a famous rule of thumb or simple number, max 3 words, e.g. 50/30/20 or 24 HOURS","headline":"one sentence explaining it, max 14 words"',
}

def generate(history, fmt):
    recent = [h["topic"] for h in history[-40:]]
    prompt = f"""You run a Facebook Page in the niche: {NICHE}.
Create ONE original post on a NEW topic (not in this list: {recent}).
Rules:
- General educational tips only. No guaranteed returns, no specific stock/crypto picks, no invented statistics.
- Keep the card text short and punchy.
- "image_prompt": short description of a vivid, realistic background photo that matches the topic (objects, scenery or hands; no text, no faces).
- "post": caption, 80-150 words, first line has a searchable keyword, short paragraphs, ends with a question inviting comments, then 3-5 hashtags.
Return ONLY JSON with these keys: "topic", "image_prompt", "post", {FORMATS[fmt]}"""
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        params={"key": API_KEY},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"responseMimeType": "application/json"}},
        timeout=60)
    r.raise_for_status()
    return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])

def post_photo(image, caption):
    r = requests.post(
        f"https://graph.facebook.com/v21.0/{PAGE_ID}/photos",
        data={"caption": caption, "access_token": PAGE_TOKEN},
        files={"source": ("card.jpg", image, "image/jpeg")}, timeout=120)
    print(r.status_code, r.text)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    delay = random.randint(0, MAX_DELAY_MIN * 60)
    print(f"Sleeping {delay//60} min for a random post time...")
    time.sleep(delay)
    history = load_history()
    fmt = random.choice(list(FORMATS))
    item = generate(history, fmt)
    card = make_card(item, fmt, PAGE_NAME, USE_AI_BG)
    res = post_photo(card, item["post"])
    history.append({"topic": item["topic"], "id": res.get("post_id") or res.get("id"),
                    "ts": int(time.time())})
    json.dump(history[-200:], open(HISTORY, "w"), indent=2)
