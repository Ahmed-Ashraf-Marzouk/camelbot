from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup, Comment
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Optional fallback (recommended for JS-heavy / bot-protected sites)
from playwright.sync_api import sync_playwright


# =============================
# Configuration
# =============================

CONTROL_SELECTOR = (
    "button, a, input, textarea, select, option, label, summary, details, "
    "[role=button], [role=link], [role=textbox], [role=searchbox], "
    "[role=combobox], [role=listbox], [role=checkbox], [role=radio], "
    "[role=tab], [role=menuitem]"
)

KEEP_ATTRS = {
    # Stable HTML attributes
    "id",
    "name",
    "type",
    "placeholder",
    "value",
    "href",
    "for",

    # Accessibility attributes (Playwright-friendly)
    "role",
    "aria-label",
    "aria-labelledby",
    "aria-describedby",

    # Testing hooks (best selectors when present)
    "data-testid",
    "data-test",
    "data-qa",
}

NOISE_TAGS = ("script", "style", "noscript", "svg", "img", "video", "canvas")


# =============================
# Data model
# =============================

@dataclass(frozen=True)
class ControlItem:
    tag: str
    text: Optional[str] = None
    attrs: Optional[Dict[str, str]] = None

    def to_compact_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"tag": self.tag}
        if self.text:
            out["text"] = self.text
        if self.attrs:
            out["attrs"] = self.attrs
        return out


# =============================
# Fetching (Requests + Playwright fallback)
# =============================

def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "close",
            "Upgrade-Insecure-Requests": "1",
        }
    )

    retry = Retry(
        total=4,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_html_requests(url: str, *, timeout: int = 25) -> str:
    session = _build_session()
    resp = session.get(url, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    return resp.text


def fetch_html_playwright(url: str, *, timeout_ms: int = 60_000) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        html = page.content()
        browser.close()
        return html


def fetch_html(url: str) -> str:
    """
    Try Requests first (fast). If the server drops the connection or the site is JS-heavy,
    fall back to Playwright (browser-realistic).
    """
    try:
        return fetch_html_requests(url)
    except Exception:
        return fetch_html_playwright(url)


# =============================
# Minimization / Extraction
# =============================

def _normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def _remove_comments(soup: BeautifulSoup) -> None:
    for node in soup.find_all(string=lambda s: isinstance(s, Comment)):
        node.extract()


def _remove_noise(soup: BeautifulSoup) -> None:
    for tag in soup(NOISE_TAGS):
        tag.decompose()


def _is_hidden(el: Any) -> bool:
    if (el.get("aria-hidden") or "").lower() == "true":
        return True
    if el.name == "input" and (el.get("type") or "").lower() == "hidden":
        return True
    return False


def _filter_attrs(el: Any, keep_attrs: Iterable[str]) -> Dict[str, str]:
    keep = set(keep_attrs)
    out: Dict[str, str] = {}

    for k, v in (el.attrs or {}).items():
        if k in keep or k.startswith("data-test"):
            if v is None:
                continue
            if isinstance(v, list):
                v = " ".join(str(x) for x in v if x is not None)
            out[k] = str(v)

    return out


def extract_controls_inventory(html: str, *, max_text_len: int = 80) -> List[ControlItem]:
    soup = BeautifulSoup(html, "html.parser")
    _remove_comments(soup)
    _remove_noise(soup)

    items: List[ControlItem] = []
    for el in soup.select(CONTROL_SELECTOR):
        if _is_hidden(el):
            continue

        text = _normalize_text(el.get_text(" ", strip=True))
        if text and len(text) > max_text_len:
            text = text[: max_text_len - 1] + "…"

        attrs = _filter_attrs(el, KEEP_ATTRS)

        if not text and not attrs:
            continue

        items.append(ControlItem(tag=el.name, text=text or None, attrs=attrs or None))

    return items


def inventory_to_json(items: List[ControlItem]) -> str:
    payload = [it.to_compact_dict() for it in items]
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


# =============================
# Main
# =============================

def main() -> None:
    url = "https://example.com"  # <-- CHANGE THIS

    os.makedirs("output", exist_ok=True)

    html = fetch_html(url)
    with open("output/page.html", "w", encoding="utf-8") as f:
        f.write(html)

    inventory = extract_controls_inventory(html, max_text_len=80)
    inv_json = inventory_to_json(inventory)

    with open("output/controls_inventory.json", "w", encoding="utf-8") as f:
        f.write(inv_json)

    print("Saved:")
    print(" - output/page.html")
    print(" - output/controls_inventory.json")
    print(f"Controls found: {len(inventory)}")


if __name__ == "__main__":
    main()
