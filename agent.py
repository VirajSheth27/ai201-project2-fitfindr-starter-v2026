"""
The FitFindr planning loop.

Decides which tool to run next based on what the last one returned.

    python agent.py          runs both example paths below
"""

import re

import config  # noqa: F401
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """A fresh session for one user interaction. Single source of truth for a run."""
    return {
        "query": query,                   # what the user typed
        "parsed": {},                     # description / size / max_price
        "search_results": [],             # everything search_listings returned
        "selected_item": None,            # the one chosen, goes into suggest_outfit
        "wardrobe": wardrobe,             # the user's wardrobe
        "outfit_suggestion": None,        # what suggest_outfit returned
        "fit_card": None,                 # what create_fit_card returned
        "last_suggested_item_id": None,   # id of the item suggest_outfit received (criterion 3)
        "last_fit_card_item_id": None,    # id of the item create_fit_card received (criterion 3)
        "error": None,                    # set when the run ended early
    }


# ── query parsing (regex) ─────────────────────────────────────────────────────

_PRICE_RE = re.compile(
    r"(?:under|below|less than|max|up to|<)\s*\$?\s*(\d+(?:\.\d+)?)|\$\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_SIZE_RE = re.compile(r"\bsize\s+([A-Za-z0-9/]+)", re.IGNORECASE)
_FILLER_RE = re.compile(r"\b(looking for|i want|i need|find me|show me)\b", re.IGNORECASE)


def parse_query(query: str) -> dict:
    """Pull description, size, and max_price out of plain text with regex."""
    text = query or ""

    max_price = None
    price_match = _PRICE_RE.search(text)
    if price_match:
        max_price = float(price_match.group(1) or price_match.group(2))
        text = text.replace(price_match.group(0), " ")

    size = None
    size_match = _SIZE_RE.search(text)
    if size_match:
        size = size_match.group(1).upper()
        text = text.replace(size_match.group(0), " ")

    text = _FILLER_RE.sub(" ", text)
    description = re.sub(r"[,\s]+", " ", text).strip()

    return {"description": description, "size": size, "max_price": max_price}


def _no_results_message(parsed: dict) -> str:
    """Say which filter to loosen, by re-running search with one filter removed."""
    desc, size, price = parsed["description"], parsed["size"], parsed["max_price"]

    if not desc:
        return ("I couldn't find any item words in your request. "
                "Try describing the item, e.g. 'graphic tee' or 'wide-leg pants'.")
    if price is not None and search_listings(desc, size, None):
        return (f"Nothing matching '{desc}' is under ${price:.0f}. "
                f"Try raising your max price.")
    if size and search_listings(desc, None, price):
        return (f"Nothing matching '{desc}' comes in size {size}. "
                f"Try a different size, or leave the size out.")
    return (f"No listings matched '{desc}'. Try broader words, "
            f"like 'tee' instead of 'band tee', or 'pants' instead of 'cords'.")


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Each pass round the loop looks at the session and picks the next step.
    BRANCH: if search_listings returns [], set session["error"] and stop.
    suggest_outfit and create_fit_card are never called.
    """
    session = new_session(query, wardrobe)
    next_step = "parse"
    count = 0

    while next_step != "done":
        count += 1
        trace.check_iterations(count)

        try:
            if next_step == "parse":
                session["parsed"] = parse_query(session["query"])
                next_step = "search"

            elif next_step == "search":
                p = session["parsed"]
                session["search_results"] = search_listings(
                    p["description"], p["size"], p["max_price"]
                )
                # ── THE BRANCH ──
                if not session["search_results"]:
                    session["error"] = _no_results_message(p)
                    next_step = "done"
                else:
                    next_step = "select"

            elif next_step == "select":
                session["selected_item"] = session["search_results"][0]
                next_step = "outfit"

            elif next_step == "outfit":
                item = session["selected_item"]          # read from session
                session["last_suggested_item_id"] = item["id"]
                session["outfit_suggestion"] = suggest_outfit(item, session["wardrobe"])
                next_step = "fit_card"

            elif next_step == "fit_card":
                item = session["selected_item"]          # read from session
                session["last_fit_card_item_id"] = item["id"]
                session["fit_card"] = create_fit_card(session["outfit_suggestion"], item)
                next_step = "done"

        except ModelUnavailable as e:
            session["fit_card"] = None
            session["error"] = (
                f"Model error during '{next_step}': the model couldn't be reached "
                f"({type(e).__name__}). Check your API key in .env, then try again."
            )
            next_step = "done"
        except Exception as e:
            session["fit_card"] = None
            session["error"] = (
                f"Unexpected error during '{next_step}': {type(e).__name__}. "
                f"Please try again."
            )
            next_step = "done"

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  ids:      selected={item.get('id')} "
          f"outfit={session['last_suggested_item_id']} "
          f"card={session['last_fit_card_item_id']}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )