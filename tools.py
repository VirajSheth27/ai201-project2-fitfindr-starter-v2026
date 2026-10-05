"""
The three FitFindr tools.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── Helpers ───────────────────────────────────────────────────────────────────

STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "under", "over", "size",
    "in", "of", "to", "i", "want", "need", "looking", "something", "some",
    "max", "less", "than", "below", "around", "about",
}


def _size_tokens(size_str) -> set[str]:
    """Split a size into whole tokens.
    "S/M" -> {"S","M"}, "XL (oversized)" -> {"XL","OVERSIZED"}, "US 9" -> {"US","9"}
    """
    return set(re.findall(r"[A-Z0-9]+", str(size_str or "").upper()))


def _size_matches(item_size, wanted: str) -> bool:
    """True if every token of the requested size appears in the listing's size.
    "M" matches "M" and "S/M"; "L" does not match "XL"; "S" does not match "US 9".
    """
    wanted_tokens = _size_tokens(wanted)
    return bool(wanted_tokens) and wanted_tokens.issubset(_size_tokens(item_size))


def _keywords(description: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", (description or "").lower())
    return [
        w for w in words
        if w not in STOPWORDS and len(w) >= 2 and not w.isdigit()
    ]


def _listing_words(item: dict) -> set[str]:
    parts = [
        item.get("title") or "",
        item.get("description") or "",
        item.get("category") or "",
        item.get("brand") or "",          # brand is often None
        " ".join(item.get("style_tags") or []),
        " ".join(item.get("colors") or []),
    ]
    return set(re.findall(r"[a-z0-9']+", " ".join(parts).lower()))

def _score(item: dict, keywords: list[str]) -> int:
    """Title and style_tags hits are worth more than description hits,
    and the whole phrase matching a tag or the title is worth most."""
    strong_text = " ".join([item.get("title") or "", " ".join(item.get("style_tags") or [])]).lower()
    strong_words = set(re.findall(r"[a-z0-9']+", strong_text))
    weak_words = _listing_words(item)

    score = 0
    for k in keywords:
        if _keyword_hit(k, strong_words):
            score += 3
        elif _keyword_hit(k, weak_words):
            score += 1

    phrase = " ".join(keywords)
    if len(keywords) > 1 and phrase in strong_text:
        score += 5
    return score


def _keyword_hit(keyword: str, words: set[str]) -> bool:
    # Simple plural handling: "tees" matches "tee", "tee" matches "tees"
    return (
        keyword in words
        or keyword.rstrip("s") in words
        or keyword + "s" in words
    )


def _format_item(item: dict) -> str:
    brand = item.get("brand") or "no brand listed"
    tags = ", ".join(item.get("style_tags") or [])
    colors = ", ".join(item.get("colors") or [])
    return (
        f"{item.get('title')} ({item.get('category')}, size {item.get('size')}, "
        f"${float(item.get('price', 0)):.0f}, {item.get('condition')} condition, "
        f"brand: {brand}, colors: {colors}, style: {tags})"
    )


def _format_wardrobe_item(piece: dict) -> str:
    # Wardrobe schema may differ from listings, so format whatever fields exist
    return ", ".join(
        f"{k}: {', '.join(v) if isinstance(v, list) else v}"
        for k, v in piece.items()
        if v not in (None, "", []) and k != "id"
    )


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """Return matching listing dicts, best match first. Empty list if none."""
    keywords = _keywords(description)
    if not keywords:
        return []

    scored = []
    for item in load_listings():
        if max_price is not None and float(item["price"]) > max_price:
            continue
        if size and not _size_matches(item.get("size"), size):
            continue

        score = _score(item, keywords)
        if score > 0:
            scored.append((score, item))

    # Highest score first; cheaper wins ties
    scored.sort(key=lambda pair: (-pair[0], float(pair[1]["price"])))
    return [item for _, item in scored][: config.SEARCH_RESULT_LIMIT]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """Return a non-empty string of 1–2 outfit suggestions."""
    pieces = (wardrobe or {}).get("items") or []
    item_text = _format_item(new_item)

    if not pieces:
        prompt = (
            f"Someone is thinking about buying this thrifted item: {item_text}.\n"
            "Their wardrobe is empty, so suggest one or two general outfits built "
            "around this item, naming the kinds of pieces that would pair well "
            "(e.g. 'straight-leg dark jeans', 'white low-top sneakers'). "
            "Keep it under 100 words. Plain text, no markdown headers."
        )
    else:
        wardrobe_text = "\n".join(f"- {_format_wardrobe_item(p)}" for p in pieces)
        prompt = (
            f"Someone is thinking about buying this thrifted item: {item_text}.\n"
            f"Here is what they already own:\n{wardrobe_text}\n\n"
            "Suggest one or two outfits combining the new item with specific "
            "pieces from their wardrobe. Name the wardrobe pieces you use. "
            "Keep it under 100 words. Plain text, no markdown headers."
        )

    result = (generate(prompt) or "").strip()
    if not result:
        # Never return "" — the next tool depends on this
        return f"Style the {new_item.get('title', 'item')} with simple basics in neutral colors."
    return result


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """Return a 2–4 sentence postable caption."""
    if not outfit or not outfit.strip():
        return (
            "Couldn't write a fit card: no outfit suggestion was provided for "
            f"{new_item.get('title', 'this item')}."
        )

    prompt = (
        "Write a 2-4 sentence caption for a social media post by someone who just "
        "BOUGHT this thrifted item and is showing off how they styled it. "
        "They found it on the platform below; they are not selling it.\n"
        f"Item: {new_item.get('title')}\n"
        f"Price: ${float(new_item.get('price', 0)):.0f}\n"
        f"Platform: {new_item.get('platform')}\n"
        f"Style tags: {', '.join(new_item.get('style_tags') or [])}\n"
        f"How they're styling it: {outfit}\n\n"
        "Rules: sound like a real person posting, not a product description. "
        "Mention the item, the price, and the platform exactly once each. "
        "Be specific about the vibe. At most two hashtags. "
        "Return only the caption."
    )
    return (generate(prompt) or "").strip()