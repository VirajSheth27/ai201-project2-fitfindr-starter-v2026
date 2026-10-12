"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Two run modes:
  normal (default):  criteria 1–4 plus diagnostics
      python run_eval.py --label before
  bad key:           criterion 5 only, run with the API key broken
      $env:FITFINDR_RUN="badkey"; python run_eval.py --label before-c5; Remove-Item Env:FITFINDR_RUN

Scoring rule for criteria 3, 4 and 5 (each says "across 5 distinct matching
queries"): there are 5 scenarios per criterion, one per query. Try column k in
the README run log = scenario k, try 1. Tries 2–5 are extra evidence, reported
but not counted. Decided before running.
"""

import os

# ── Criterion 1: matching query completes all three tools ────────────────────
C1 = [
    {
        "name": "c1 matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
]

# ── Criterion 2: impossible query stops before suggest_outfit ────────────────
C2 = [
    {
        "name": "c2 impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
]

# ── Criteria 3 + 4: 5 distinct matching queries ──────────────────────────────
# C3: select_item id == suggest_outfit item_id == create_fit_card item_id (trace)
# C4: fit card has 2+ title words, $price, platform (case-insensitive)
C3_C4 = [
    {"name": "c3/c4 q1 denim jacket",   "query": "denim jacket under $50",       "wardrobe": "example", "criterion": 3},
    {"name": "c3/c4 q2 red flannel",    "query": "red flannel shirt under $40",  "wardrobe": "example", "criterion": 3},
    {"name": "c3/c4 q3 suede boots",    "query": "tan suede boots under $50",    "wardrobe": "example", "criterion": 3},
    {"name": "c3/c4 q4 corduroy pants", "query": "corduroy wide-leg pants",      "wardrobe": "example", "criterion": 3},
    {"name": "c3/c4 q5 track jacket",   "query": "90s track jacket size M",      "wardrobe": "example", "criterion": 3},
]

# ── Diagnostics: not one of the five, kept as evidence ───────────────────────
DIAGNOSTIC = [
    {
        # Failure mode: empty wardrobe should give general advice, not crash.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
    {
        # Finding from M2: 'boots' ties with 'black', and cheaper shorts win.
        "name": "weak-match ranking (boots query)",
        "query": "black combat boots under $60",
        "wardrobe": "example",
        "criterion": None,
    },
]

# ── Criterion 5: run ONLY with the API key broken ────────────────────────────
C5 = [
    {"name": "c5 q1 cargo pants",   "query": "cargo pants under $40",       "wardrobe": "example", "criterion": 5},
    {"name": "c5 q2 mary janes",    "query": "platform mary janes",         "wardrobe": "example", "criterion": 5},
    {"name": "c5 q3 mesh top",      "query": "mesh top size S",             "wardrobe": "example", "criterion": 5},
    {"name": "c5 q4 crewneck",      "query": "crewneck sweatshirt under $30", "wardrobe": "example", "criterion": 5},
    {"name": "c5 q5 denim vest",    "query": "denim vest",                  "wardrobe": "example", "criterion": 5},
]

if os.environ.get("FITFINDR_RUN") == "badkey":
    SCENARIOS = C5
else:
    SCENARIOS = C1 + C2 + C3_C4 + DIAGNOSTIC

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems