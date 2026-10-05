# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
First, initial retrieval uses plain keyword matching against listing descriptions, which can miss relevant items depending on how the query is phrased. 
Second, two of the three tools (suggest_outfit and create_fit_card) rely on LLM generation, which introduces non-deterministic model calls that can occasionally fail
Expecting 5 of 5 assumes perfect keyword matching and 100% LLM API stability.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
Unlike criterion 1, this path relies on a deterministic control flow check directly in Python code. Because no LLM generation or non-deterministic tool calls occur before this early exit, the branching logic is entirely under our control and should execute with 100% reliability.

---

## 3. State persists across tools

Across 5 distinct matching queries, the `id` in `session["selected_item"]["id"]`
matches both the `id` recorded in `session["last_suggested_item_id"]` when
`suggest_outfit` is called and the `id` recorded in
`session["last_fit_card_item_id"]` when `create_fit_card` is called — 5 of 5 times.

**Why this target:**
State propagation is handled by explicit Python dictionary assignments in
`agent.py`. Because passing data between session keys and tool inputs is purely
deterministic code, any failure rate below 100% indicates a bug in the session
management logic rather than model variance.

---

## 4. The fit card names the item, price, and platform

Across 5 distinct matching queries, the text returned by `create_fit_card`
contains all three of the following — 4 of 5 times:

- **Item name:** at least two words from the listing's `title`, case-insensitive
  (e.g. "baby tee" for "Y2K Baby Tee — Butterfly Print").
- **Price:** a `$` followed by the listing's price; `$18` and `$18.00` both count.
- **Platform:** the listing's `platform` value, case-insensitive
  (`ThredUp` counts for `thredUp`).

**Why this target:**
`create_fit_card` relies on the model to write the caption from a prompt that
asks for the item, price, and platform. Because model output is
non-deterministic, it can occasionally leave out a requested field, so 4 of 5
is realistic while still enforcing output quality.

---

## 5. Model failure is handled without a crash

With `CACHE_ENABLED = False` in `config.py` and an invalid API key
(`sk-invalid`) in `.env`, across 5 distinct matching queries the agent catches
the error, sets `session["fit_card"]` to `None`, and prints a user-facing
message containing "error" or "try again", with no Python traceback in the
output — 5 of 5 times.

**Why this target:**
Model calls in `agent.py` are wrapped in explicit `try/except` blocks. Since
catching the exception and updating `session["fit_card"]` is fixed control
flow, failure handling should succeed every time under a bad key. The cache is
off so every query actually reaches the API; otherwise a cached answer would
skip the failure entirely.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
