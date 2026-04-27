from __future__ import annotations

import contextlib
import io
import os
import re
from pathlib import Path

from google import genai
import yfinance as yf


DEFAULT_SENTIMENT_SCORE = 5
MAX_HEADLINES = 10
_SENTIMENT_PATTERN = re.compile(r"\b([1-9]|10)\b")
MODEL_CANDIDATES = ("gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash")


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Allow .env to fill missing or empty shell variables.
        if key and (key not in os.environ or not str(os.environ.get(key, "")).strip()):
            os.environ[key] = value


def _extract_headlines(symbol: str, max_items: int = MAX_HEADLINES) -> list[str]:
    # yfinance is noisy and may print transient warnings to stdout/stderr.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        news_items = yf.Ticker(symbol).news or []

    headlines: list[str] = []
    for item in news_items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        headlines.append(title)
        if len(headlines) >= max_items:
            break
    return headlines


def _build_prompt(symbol: str, headlines: list[str]) -> str:
    numbered_headlines = "\n".join(f"{idx}. {headline}" for idx, headline in enumerate(headlines, start=1))
    return (
        "You are a strict financial sentiment classifier.\n"
        f"Analyze the latest news headlines for {symbol}.\n"
        "Score overall sentiment on this integer scale only:\n"
        "1 = very negative, 10 = very positive.\n\n"
        "Rules:\n"
        "- Respond with exactly one integer between 1 and 10.\n"
        "- Do not include words, punctuation, markdown, or explanation.\n"
        "- If uncertain, choose 5.\n\n"
        f"Headlines:\n{numbered_headlines}\n"
    )


def _parse_score(raw_text: str) -> int:
    match = _SENTIMENT_PATTERN.search(raw_text)
    if not match:
        return DEFAULT_SENTIMENT_SCORE
    value = int(match.group(1))
    return value if 1 <= value <= 10 else DEFAULT_SENTIMENT_SCORE


def get_ai_sentiment_score(symbol: str, model_name: str = "gemini-2.0-flash") -> int:
    """
    Return an integer sentiment score in range [1, 10].
    Falls back to neutral score 5 on any failure.
    """
    try:
        _load_dotenv(Path(__file__).resolve().parent.parent / ".env")
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            print(f"[WARN] {symbol}: GEMINI_API_KEY missing, fallback score={DEFAULT_SENTIMENT_SCORE}")
            return DEFAULT_SENTIMENT_SCORE

        headlines = _extract_headlines(symbol=symbol, max_items=MAX_HEADLINES)
        if not headlines:
            print(f"[WARN] {symbol}: no headlines found, fallback score={DEFAULT_SENTIMENT_SCORE}")
            return DEFAULT_SENTIMENT_SCORE

        client = genai.Client(api_key=api_key)
        prompt = _build_prompt(symbol=symbol, headlines=headlines)
        model_attempts = [model_name, *MODEL_CANDIDATES]
        tried: set[str] = set()
        response = None
        last_exc: Exception | None = None
        for candidate in model_attempts:
            candidate_clean = candidate.strip()
            if not candidate_clean or candidate_clean in tried:
                continue
            tried.add(candidate_clean)
            try:
                response = client.models.generate_content(model=candidate_clean, contents=prompt)
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
        if response is None:
            if last_exc is not None:
                print(f"[WARN] {symbol}: Gemini call failed ({last_exc}), fallback score={DEFAULT_SENTIMENT_SCORE}")
            return DEFAULT_SENTIMENT_SCORE

        text = str(getattr(response, "text", "") or "").strip()
        if not text:
            # Some Gemini responses may store text in parts; stringify whole response as fallback.
            text = str(response).strip()
        return _parse_score(text)
    except Exception as exc:
        print(f"[WARN] {symbol}: sentiment evaluation failed ({exc}), fallback score={DEFAULT_SENTIMENT_SCORE}")
        return DEFAULT_SENTIMENT_SCORE


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Get AI sentiment score for a ticker.")
    parser.add_argument("symbol", type=str, help="yfinance ticker symbol, e.g. SHELL.AS")
    args = parser.parse_args()
    print(get_ai_sentiment_score(args.symbol))
