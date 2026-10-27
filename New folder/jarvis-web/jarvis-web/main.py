"""J.A.R.V.I.S core server - no API keys. Skills are local logic + free keyless APIs."""
import ast, operator as op, random, re, time, urllib.parse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="J.A.R.V.I.S")
T0 = time.time()
UA = {"User-Agent": "JARVIS-2090/1.0 (personal project)"}
INDEX = Path(__file__).parent / "static" / "index.html"

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I would tell you a UDP joke, but you might not get it.",
    "There are ten kinds of people: those who understand binary and those who don't.",
    "A SQL query walks into a bar, sees two tables and asks: may I join you?",
    "My code works, and I have no idea why. Let's not touch it.",
]
SITES = {"youtube": "https://youtube.com", "google": "https://google.com", "github": "https://github.com",
         "gmail": "https://mail.google.com", "maps": "https://maps.google.com", "spotify": "https://open.spotify.com",
         "linkedin": "https://linkedin.com", "wikipedia": "https://wikipedia.org", "claude": "https://claude.ai"}
HELP = ("I can tell the time and date, do maths, check the weather in any city, look things up on Wikipedia, "
        "open websites, search the web, play videos, and tell jokes. Try: weather in Mumbai, or who is Nikola Tesla.")
OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
       ast.Pow: op.pow, ast.Mod: op.mod, ast.USub: op.neg}


class Ask(BaseModel):
    text: str
    tz: str = "UTC"


def calc(expr: str):
    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and abs(b) > 100:
                raise ValueError
            return OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp):
            return OPS[type(n.op)](ev(n.operand))
        raise ValueError
    return ev(ast.parse(expr, mode="eval").body)


def maybe_math(t: str):
    e = re.sub(r"^(what is|what's|calculate|compute|solve)\s+", "", t)
    for a, b in (("multiplied by", "*"), ("divided by", "/"), ("to the power of", "**"), ("plus", "+"),
                 ("minus", "-"), ("times", "*"), ("over", "/"), ("squared", "**2"), ("modulo", "%")):
        e = e.replace(a, b)
    if re.fullmatch(r"[\d\s+\-*/().%]+", e) and re.search(r"\d", e) and re.search(r"[+\-*/%]", e):
        try:
            v = calc(e)
            return f"{e.strip()} equals {round(v, 6):g}."
        except Exception:
            return "That calculation defeated me."
    return None


def wmo(c: int) -> str:
    return ("clear skies" if c == 0 else "mostly clear skies" if c == 1 else "partly cloudy skies" if c == 2
            else "overcast skies" if c == 3 else "fog" if c in (45, 48) else "drizzle" if c < 60
            else "rain" if c < 70 else "snow" if c < 80 else "rain showers" if c < 90 else "thunderstorms")


async def weather(place: str) -> str:
    async with httpx.AsyncClient(timeout=8, headers=UA) as c:
        r = (await c.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": place, "count": 1})).json()
        if not r.get("results"):
            return f"I couldn't locate {place}."
        p = r["results"][0]
        w = (await c.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": p["latitude"], "longitude": p["longitude"],
            "current": "temperature_2m,weather_code,wind_speed_10m"})).json()["current"]
    return (f"In {p['name']} it is {w['temperature_2m']} degrees Celsius with {wmo(w['weather_code'])}, "
            f"and wind at {w['wind_speed_10m']} kilometres per hour.")


async def wiki(q: str):
    async with httpx.AsyncClient(timeout=8, headers=UA) as c:
        s = (await c.get("https://en.wikipedia.org/w/api.php", params={
            "action": "query", "list": "search", "srsearch": q, "format": "json", "srlimit": 1})).json()["query"]["search"]
        if not s:
            return None
        title = urllib.parse.quote(s[0]["title"].replace(" ", "_"))
        ex = (await c.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}")).json().get("extract", "")
    ex = re.sub(r"\s*\([^)]*\)", "", ex)
    return " ".join(re.split(r"(?<=[.!?])\s+", ex)[:2]) or None


@app.get("/")
def index():
    return FileResponse(INDEX)


@app.get("/api/ping")
def ping():
    return {"ok": True}


@app.post("/api/ask")
async def ask(a: Ask):
    t = a.text.lower().strip().rstrip("?.!")
    try:
        now = datetime.now(ZoneInfo(a.tz))
    except Exception:
        now = datetime.utcnow()
    out: dict = {}
    try:
        if re.match(r"^(hi|hello|hey|good (morning|afternoon|evening))\b", t):
            out["reply"] = "Hello, sir. All systems are online. How may I assist?"
        elif re.search(r"who are you|your name", t):
            out["reply"] = "I am JARVIS, Mark 2090. Just A Rather Very Intelligent System."
        elif re.search(r"\b(what time|the time|current time)\b", t):
            out["reply"] = f"It is {now:%I:%M %p}."
        elif re.search(r"\b(what('s| is) (the )?date|today's date|what day)\b", t):
            out["reply"] = f"Today is {now:%A, %B %d, %Y}."
        elif re.search(r"\b(status|diagnostic)", t):
            out["reply"] = f"All systems nominal. Core online for {int((time.time() - T0) // 60)} minutes."
        elif "joke" in t:
            out["reply"] = random.choice(JOKES)
        elif re.search(r"\b(help|what can you do)\b", t):
            out["reply"] = HELP
        elif (m := maybe_math(t)):
            out["reply"] = m
        elif (m := re.search(r"(?:weather|temperature)\s+(?:in|at|for)\s+(.+)", t)):
            out["reply"] = await weather(m.group(1))
        elif re.search(r"\b(shut ?down|go to sleep|goodbye|power down)\b", t):
            out.update(reply="Standing by. Raise an open palm to wake me.", sleep=True)
        elif (m := re.match(r"play (.+)", t)):
            out.update(reply=f"Searching YouTube for {m.group(1)}.",
                       open="https://www.youtube.com/results?search_query=" + urllib.parse.quote(m.group(1)))
        elif (m := re.match(r"(?:search for|search|google|look up) (.+)", t)):
            out.update(reply=f"Searching for {m.group(1)}.",
                       open="https://www.google.com/search?q=" + urllib.parse.quote(m.group(1)))
        elif (m := re.match(r"(?:open|launch) (.+)", t)):
            site = m.group(1).strip()
            url = SITES.get(site) or f"https://www.google.com/search?q={urllib.parse.quote(site)}"
            out.update(reply=f"Opening {site}.", open=url)
        elif (m := re.match(r"(?:who is|who was|what is|what are|what's|tell me about|define|explain) (.+)", t)):
            out["reply"] = (await wiki(m.group(1))) or f"I found nothing on {m.group(1)}."
        else:
            out["reply"] = "I didn't catch a command in that. Say help to hear what I can do."
    except Exception:
        out["reply"] = "My data link failed on that request. Please try again."
    return out


# Registered last so it never shadows the API routes.
from fastapi.staticfiles import StaticFiles  # noqa: E402
app.mount("/static", StaticFiles(directory=INDEX.parent), name="static")
