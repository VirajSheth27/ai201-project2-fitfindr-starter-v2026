# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

## Data Notes

Notes from reading `data/listings.json` (Milestone 1).

**Listing fields:** `id`, `title`, `description`, `category`, `style_tags` (list),
`size`, `condition`, `price` (float), `colors` (list), `brand` (str or None), `platform`.

**What I noticed:**

- **Sizes are inconsistent.** Examples: `"M"`, `"S/M"`, `"XL (oversized)"`,
  `"W30 L30"`, `"W28"`. A plain substring test would be wrong (`"l" in "xl"` is
  True), so size matching has to compare whole size tokens, not characters.
- **`brand` is often `null`**, so no code or prompt can assume a brand exists.
- **`style_tags` holds multi-word tags** like `"graphic tee"` and `"band tee"`,
  which makes it the most useful field for keyword matching.
- **Some listings describe their own fit**, e.g. the butterfly baby tee is tagged
  `"S/M"` but its description says it fits like a small.
- **Platforms seen:** depop, thredUp, poshmark.

---

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

FitFindr is a thrifting agent. A user types what they want in plain language, like `'vintage graphic tee under $30, size M'`, and the agent parses out a description, size, and price ceiling, then searches the listings data for matches. If it finds something, it takes the best match, suggests one or two outfits using pieces from the user's wardrobe (or general styling advice if the wardrobe is empty), and writes a short caption someone would actually post. If nothing matches, it stops before calling the model and tells the user which filter to loosen: the price, the size, or the keywords.



---

## Tool Inventory

### `search_listings`

- **What it does:** Filters `data/listings.json` by price and size, then ranks what's left by how many query keywords appear in the listing's title, description, category, brand, style_tags, and colors.
- **Inputs:** `description` (str), `size` (str or None), `max_price` (float or None). Size matches when every token of the requested size appears as a whole token in the listing's size, so `"M"` matches `"M"` and `"S/M"` but `"L"` does not match `"XL"`. `max_price` is inclusive.
- **Returns:** `list[dict]` of listing dicts, highest keyword score first and cheaper first on ties, at most `config.SEARCH_RESULT_LIMIT` items. Each dict has `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`.
- **When it has nothing:** Returns `[]`, an empty list. Never `None`, never raises. This also happens when the description has no usable keywords.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the new item, using pieces from the user's wardrobe when there are any.
- **Inputs:** `new_item` (dict, one listing dict from `search_listings`), `wardrobe` (dict with an `items` key holding a list of wardrobe item dicts).
- **Returns:** `str`, a non-empty plain-text suggestion of one or two outfits under about 100 words. With a non-empty wardrobe it names specific pieces the user owns.
- **When it has nothing:** If `wardrobe["items"]` is empty or missing, it returns general styling advice naming kinds of pieces to pair. If the model returns an empty string, it returns a fallback sentence instead. It never returns `""`.

### `create_fit_card`

- **What it does:** Asks the model for a short caption someone would post about the find.
- **Inputs:** `outfit` (str, the output of `suggest_outfit`), `new_item` (dict, the same listing dict).
- **Returns:** `str`, a 2–4 sentence caption that mentions the item, price, and platform once each, with at most two hashtags.
- **When it has nothing:** If `outfit` is empty or whitespace, it returns the message `"Couldn't write a fit card: no outfit suggestion was provided for <title>."` without calling the model.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["message"]` saying which filter to loosen (price, size, or keywords), and stop without calling `suggest_outfit` or `create_fit_card`. Otherwise, store the first result in `session["selected_item"]` and go to `suggest_outfit`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:**  Regex, in `agent.py::parse_query`. A price is pulled from phrases like "under $30" or "$30", a size from "size M", and filler like "looking for" is stripped. What's left becomes the description.

**How the empty-search message is chosen:** `agent.py::_no_results_message` re-runs the search with one filter removed at a time. If dropping the price finds results, it says to raise the price. If dropping the size finds results, it says to change the size. Otherwise it says to use broader words.

**What moves through the session:** `query` → `parsed` (description, size, max_price) → `search_results` → `selected_item` → `last_suggested_item_id` + `outfit_suggestion` → `last_fit_card_item_id` + `fit_card`. Each tool reads its inputs from the session, not from the previous call's return value. If a model call fails, the loop catches `ModelUnavailable`, sets `session["error"]`, leaves `fit_card` as `None`, and stops.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python agent.py
=== A query the data can match ===
  found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop
  ids:      selected=lst_002 outfit=lst_002 card=lst_002
  outfit:   Outfit 1: Pair the Y2K butterfly baby tee with your baggy straight-leg jeans for that classic early-2000s contrast. Add the chunky white sneakers and the black crossbody bag for a casual, effortless streetwear look.

Outfit 2: Tuck the baby tee into your wide-leg khaki trousers, accented by the brown leather belt to tie the earth tones together. Finish the outfit with the black combat boots to add a subtle grunge edge to the sweet butterfly graphic.
  fit card: Still not over scoring this butterfly baby tee on Depop for just $18! I'm totally obsessed with how it looks dressed down with baggy denim and chunky sneakers, but I think styling it with khakis and combat boots for that sweet-meets-grunge vibe is my new favorite combo. #y2kstyle #thriftedfashion

=== A query it can't ===
  stopped: No listings matched 'designer ballgown'. Try broader words, like 'tee' instead of 'band tee', or 'pants' instead of 'cords'.
  fit_card is None — it should still be None here
```

The happy path calls all three tools, and the same item id (`lst_002`) reaches both `suggest_outfit` and `create_fit_card`. The impossible query stops at the branch, and `fit_card` stays `None`.

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print([(i['id'], i['title']) for i in search_listings('graphic tee', max_price=30)])"
[('lst_002', 'Y2K Baby Tee — Butterfly Print'), ('lst_033', 'Vintage Band Tee — Faded Grey'), ('lst_006', 'Graphic Tee — 2003 Tour Bootleg Style'), ('lst_015', 'Vintage Graphic Hoodie — Faded Black'), ('lst_017', 'Mesh Long-Sleeve Top — Black'), ('lst_012', 'Oversized Crewneck Sweatshirt — Vintage Navy'), ('lst_011', 'Low-Rise Cargo Pants — Khaki')]

$ python -c "from tools import search_listings; print(search_listings('sequin ballgown'))"
[]

$ python -c "from tools import search_listings; print([i['size'] for i in search_listings('tee', size='L')])"
['L', 'L']
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Outfit 1: Pair the vintage Levi's with the white ribbed tank top, black cropped zip hoodie layered on top, and chunky white sneakers for a classic streetwear look. Add the black crossbody bag to complete the outfit.

Outfit 2: Combine the jeans with the oversized grey crewneck sweatshirt tucked in slightly at the front, paired with the black combat boots and the brown leather belt for a relaxed, vintage-inspired everyday fit.

$ python -c "from tools import suggest_outfit; from utils.data_loader import get_empty_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_empty_wardrobe()))"
For a casual everyday look, pair the vintage Levi's 501 jeans with a plain white crewneck t-shirt and classic canvas low-top sneakers. Layer with an oversized black leather biker jacket for a touch of edge.

For a slightly smarter weekend outfit, combine the jeans with a relaxed-fit oatmeal knit crewneck sweater and brown leather Chelsea boots. Add a minimal black leather belt to tie the look together. Both outfits offer a timeless streetwear aesthetic that highlights the classic medium wash of the denim.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Run 1: Nothing beats the wash on these vintage Levi's 501s, especially for just $38. I've been living in them with a crisp pair of white sneakers for the ultimate effortless 90s street style. Snagged these over on depop before anyone else could. #vintage #denim
Run 2: <PASTE, with CACHE_ENABLED = False>
Run 3: <PASTE, with CACHE_ENABLED = False>

$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('   ', load_listings()[0]))"
Couldn't write a fit card: no outfit suggestion was provided for Vintage Levi's 501 Jeans — Medium Wash.
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

I also used AI to help generate the code

**Moment 1**

- *What I asked for:* I gave Claude my `search_listings` spec and asked for an implementation.
- *What came back:* Keyword scoring where every hit counted equally, wherever it appeared in the listing. When I tested `'graphic tee'`, a mesh long-sleeve top ranked first, because its description says "layering under a graphic tee", and it beat the real tees on price.
- *What I changed:* I weighted hits in the title and style_tags at 3 and description hits at 1, and added a bonus when the whole phrase matches a tag or the title. The butterfly graphic tee now ranks first, and the mesh top dropped to fifth.

**Moment 2**

- *What I asked for:* I pasted my three acceptance criteria into Claude and asked how it would test each one using only what the sentence said.
- *What came back:* It couldn't test my state criterion, because I compared `item_id`, a field the listings don't have (they use `id`), and nothing recorded what `suggest_outfit` actually received. It also pointed out that checking the item name in the fit card made a "deterministic, 5 of 5" criterion depend on model output, and that a cached answer would hide a bad API key in my error-handling test.
- *What I changed:* I switched to `id`, added `last_suggested_item_id` and `last_fit_card_item_id` to the session so the comparison is observable, dropped the fit card name check from criterion 3, and required `CACHE_ENABLED = False` in criterion 5.


<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

From `results/run_2026-10-12_0457_before.md` (criteria 1–4) and `results/run_2026-10-12_0500_before-c5.md` (criterion 5), produced by `run_eval.py::main` with caching off and temperature 0.9.

**Scoring rule, set in `scenarios.py` before running:** criteria 1 and 2 use one scenario × 5 tries. Criteria 3, 4, and 5 each say "across 5 distinct matching queries", so each has 5 scenarios (one per query), and Try k = scenario k, try 1. Tries 2–5 of those scenarios are reported but not counted.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before suggest_outfit | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Same item id reaches suggest_outfit and create_fit_card | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card names item, $price, platform | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Model failure handled without a crash | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 1 (revised). Fit card is for the item asked about (boots query) | 4 of 5 | FAIL | FAIL | FAIL | FAIL | FAIL | MISSED (0/5) |
| _Diagnostic: empty wardrobe_ | — | advice | advice | advice | advice | advice | no crash, 5/5 |

Extra evidence for criteria 3–5: all 25 tries of the criterion 3/4 scenarios had matching ids and a fit card with the name, price, and platform, and all 25 criterion 5 tries were handled cleanly.

**Real output from one try per criterion**

Criterion 1, `agent.py::run_agent` via `run_eval.py::run_once`, query `vintage graphic tee under $30`, try 1:
```
- stopped early: no
- selected_item: Y2K Baby Tee — Butterfly Print ($18.0, depop)
Fit card:
Still obsessed with how I scored this butterfly baby tee for just $18 on depop. I've been living in it—either dressed down with baggy denim and chunky sneakers or given a little edge tucked into khaki trousers with combat boots. Such a good find for channeling that early 2000s nostalgic street style. #y2k #vintagestyle
```

Criterion 2, `agent.py::run_agent` → `agent.py::_no_results_message`, query `designer ballgown size XXS under $5`, try 1:
```
- stopped early: yes — No listings matched 'designer ballgown'. Try broader words, like 'tee' instead of 'band tee', or 'pants' instead of 'cords'.
- selected_item: (none)
Trace: [1] parse_query → [2] search_listings (via MCP) → out: [] (empty) → branch: empty results, stopping before suggest_outfit
```

Criterion 3, trace from `agent.py::run_agent`, query `denim jacket under $50`, try 1:
```
[3] select_item         → took first result, id=lst_007
[4] suggest_outfit      in: item_id='lst_007', wardrobe_items=10
[5] create_fit_card     in: item_id='lst_007', outfit='…'
```

Criterion 4, `tools.py::create_fit_card`, query `tan suede boots under $50`, try 1 (title words "suede", "chelsea", "boots"; "$44"; "Poshmark"):
```
Score! Snagged these tan suede Chelsea boots on Poshmark for just $44 and I am officially obsessed. I've already been living in them—first paired with my baggy dark wash jeans and black denim jacket for a little western edge, and then dressed down with khaki trousers and an oversized grey crew for that cozy, minimal vibe. #ThriftFinds #EarthTones
```

Criterion 5, `agent.py::run_agent` `ModelUnavailable` handler, query `cargo pants under $40`, try 1:
```
- stopped early: yes — Model error during 'outfit': the model couldn't be reached (ModelUnavailable). Check your API key in .env, then try again.
[4] outfit FAILED → ModelUnavailable, stopping
```

Criterion 1 (revised), query `black combat boots under $60`, try 1:
```
- selected_item: Biker Shorts — Black, Shiny ($14.0, depop)
Fit card: Score! Snagged these shiny black biker shorts on Depop for just $14 and I'm obsessed with how they turned out. …
```

```

---

## Verdicts and Diagnoses

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | Matching query completes all three tools | 4 of 5 | MET (5/5) | All 5 tries ran parse → search → select → suggest_outfit → create_fit_card and returned a fit card. |
| 2 | Impossible query stops before suggest_outfit | 5 of 5 | MET (5/5) | All 5 traces end at search_listings with `[] (empty)`, `fit_card` is None, and the message names a change ("try broader words"). |
| 3 | State persists across tools | 5 of 5 | MET (5/5) | For q1–q5 try 1, the id at select_item, suggest_outfit, and create_fit_card is identical in the trace. |
| 4 | Fit card names item, price, platform | 4 of 5 | MET (5/5) | Each q1–q5 try 1 card contains 2+ title words, `$` + the listing price, and the platform (case-insensitive). |
| 5 | Model failure handled without a crash | 5 of 5 | MET (5/5) | Each c5 try 1 stopped with a message containing "error" and "try again", had no fit card, and logged no crash or traceback. |
| 1R | Fit card is for the item asked about | 4 of 5 | MISSED (0/5) | All 5 boots-query tries selected Biker Shorts. |

**Diagnoses**

I met all five original targets, and some of them were too easy. Criterion 4 came out at 25 of 25 against a target of 4 of 5, so it's the one I'd tighten, for example by also requiring that the card never names a brand the listing doesn't have. Criterion 3 is close to unfailable as built: the trace records `item["id"]` from the same session read that the tool receives, so it mostly confirms the code reads the session rather than testing anything that could vary.

**Criterion 1 (revised), missed 0/5. Place: a tool (`tools.py::search_listings`, via `_score`).** Mechanism: on `black combat boots under $60`, "black" in Biker Shorts — Black's title and "boots" in Suede Chelsea Boots — Tan's title each score +3. The tie goes to the cheaper item ($14 vs $44), and four other black items under $44 also outrank the boots, so the only boot under $60 ranked 6th. The loop then takes result #1 as designed. The branch, the session, and the model all worked; the tool's ranking treats a color word the same as the word naming the item. The original criterion 1 couldn't see this, because it only checked that a fit card came back, which is why I revised it.

**Pattern:** every problem I found traces back to `search_listings` ranking, not the loop. The weak match also explains a smaller oddity in Unit 3, where a mesh top ranked first for "graphic tee" because of a description-only mention.



---

## Loop Trace

`search_listings` runs through the MCP server, shown as `search_listings (via MCP)` in step 2. Traces come from `trace.step()` calls in `agent.py::run_agent`.

**Happy path**

```
$ python app.py ask 'vintage graphic tee under $30' --trace
[1] parse_query
      in:  vintage graphic tee under $30
      out: description='vintage graphic tee', size=None, max_price=30.0
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', size=None, max_price=30.0
      out: 10 items: Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style … +7 more
      →    branch: results found, continuing
[3] select_item
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
      →    took first result, id=lst_002
[4] suggest_outfit
      in:  item_id='lst_002', wardrobe_items=10
      out: Outfit 1: Pair the Y2K butterfly baby tee with your baggy straight-leg jeans for that classic early-2000s cont…
[5] create_fit_card
      in:  item_id='lst_002', outfit='Outfit 1: Pair the Y2K butterfly baby tee with your baggy st…'
      out: Still not over scoring this butterfly baby tee on Depop for just $18! I'm totally obsessed with how it looks d…
```

**Empty search**

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: description='designer ballgown', size='XXS', max_price=5.0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
      →    branch: empty results, stopping before suggest_outfit

  No listings matched 'designer ballgown'. Try broader words, like 'tee' instead of 'band tee', or 'pants' instead of 'cords'.

0 model calls this session
```

The empty path stops at step 2 and makes zero model calls. The happy path runs all five steps. The same item id (`lst_002`) appears at select, `suggest_outfit`, and `create_fit_card`.

### Failure modes, triggered on purpose

**1. Empty search.** `python app.py ask 'designer ballgown size XXS under $5'` stops at the branch (trace above). `fit_card` stays `None`, and no model calls are made.

**2. Empty wardrobe.** `python app.py ask 'denim jacket under $50' --empty-wardrobe` runs normally, and `suggest_outfit` returns general advice instead of crashing or returning `""`:

```
[4] suggest_outfit
      in:  item_id='lst_007', wardrobe_items=0
      out: Since your wardrobe is currently empty, here are two versatile outfits to build around your Wrangler denim jac…
      →    empty wardrobe, general advice
```

**3. Model unavailable.** For the criterion 5 test run (`results/run_2026-10-12_0500_before-c5.md`), changing one character of the key in `.env` did make the model unreachable: all 25 tries raised `ModelUnavailable` through the real API path. My M2 attempt most likely didn't take effect because the edit wasn't saved before running.

```
$ python app.py ask 'tan suede boots under $50' --trace
[1] parse_query
      in:  tan suede boots under $50
      out: description='tan suede boots', size=None, max_price=50.0
[2] search_listings (via MCP)
      in:  description='tan suede boots', size=None, max_price=50.0
      out: 7 items: Suede Chelsea Boots — Tan, Mini Shoulder Bag — Tan Leather, Bucket Hat — Reversible, Brown Plaid … +4 more
      →    branch: results found, continuing
[3] select_item
      out: Suede Chelsea Boots — Tan ($44.0, poshmark)
      →    took first result, id=lst_028
[4] outfit FAILED
      out: Model error during 'outfit': the model couldn't be reached (ModelUnavailable). Check your API key in .env, the…
      →    ModelUnavailable, stopping

  Model error during 'outfit': the model couldn't be reached (ModelUnavailable). Check your API key in .env, then try again.


The `ModelUnavailable` handler in `agent.py::run_agent` catches it, stops the loop, leaves `fit_card` as `None`, and shows no traceback. My first attempt put the forced `raise` at module level in `tools.py`, so it fired on import, before the agent ran, and `app.py` printed the raw `ModelUnavailable: forced for testing`. The empty trace was the clue.

**Finding from failure testing (not fixed in M2):** `python app.py ask 'black combat boots under $60'` reported success but selected **Biker Shorts — Black**. The catalog's only boot under $60, **Suede Chelsea Boots — Tan ($44)**, ranked 6th. In `tools.py::_score`, "black" in the shorts' title and "boots" in the boots' title each score +3, and the tie goes to the cheaper item. The scorer weights a color word the same as the word naming the item, so the agent returns a confident wrong result with no error.

**On the MCP move:** I registered `search_listings` in `mcp_server.py` with a typed signature and a description written for an outside agent (inputs with units, size-matching rule, return fields, empty case). In `agent.py`, `run_agent` and `_no_results_message` now call it through `mcp_client.call_tool` via a `_search()` helper, and a new `except MCPError` handler covers the server being unreachable. Nothing behaved differently afterward. A direct call and an MCP call on the same input returned identical results (`a == b` → `True 7 7`), and the empty case still came back as `[]`. The one fix the move forced was in the description itself: my first draft claimed "One Size" listings match any size request, which the code doesn't do, so I removed it rather than publish a contract the tool breaks.


---

## The Improvement
 
**What I changed:** One change, in tools.py::_score. The last keyword of the parsed description (usually the item noun: "boots", "tee", "jacket") gets a +4 bonus when it appears in the listing's title or style_tags. I also updated the search_listings description in mcp_server.py so the published contract matches the new ranking. No other code changed.
 
**Which failure it was meant to fix:** Criterion 1 (revised), which missed 0/5. On 'black combat boots under $60', "black" and "boots" each scored +3 in a title, the tie went to the cheaper item, and the agent selected Biker Shorts — Black instead of Suede Chelsea Boots — Tan. The diagnosis said the tool weighted a color word the same as the item word, so the fix targets exactly that weighting.
 
### Run Log — After
 
From results/run_2026-10-12_0535_after.md (criteria 1–4) and results/run_2026-10-12_0543_after-c5b.md (criterion 5), same scenarios, caching off, temperature 0.9.
 
| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before suggest_outfit | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Same item id reaches suggest_outfit and create_fit_card | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card names item, $price, platform | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Model failure handled without a crash | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5)* |
| 1 (revised). Fit card is for the item asked about (boots query) | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| Diagnostic: empty wardrobe | — | advice | advice | advice | advice | advice | no crash, 5/5 |
 
*Criterion 5 deviation from my scoring rule: both of my "after" bad-key runs (results/run_2026-10-12_0538_after-c5.md and results/run_2026-10-12_0543_after-c5b.md) failed to pick up the FITFINDR_RUN=badkey switch in scenarios.py, so they ran the criteria 1–4 scenarios with a broken key instead of the five c5 queries. Criterion 5 says "across 5 distinct matching queries", so I scored it on the five c3/c4 queries (denim jacket, red flannel, suede boots, corduroy pants, track jacket), try 1 each, from the c5b run. Every one stopped with "Model error during 'outfit': the model couldn't be reached (ModelUnavailable). Check your API key in .env, then try again.", had no fit card, and none crashed. Across both runs, all 80 model-calling tries were handled the same way, and the impossible query still stopped at the branch. The before and after criterion 5 rows therefore use different queries, which I'm noting because it isn't the mapping I set in advance.
 
**Real output, boots query, try 1 (after):**
 
selected_item: Suede Chelsea Boots — Tan ($44.0, poshmark)\
[3] select_item → took first result, id=lst_028\
Fit card: Score on these vintage tan suede Chelsea boots for just $44 on Poshmark! I'm obsessed with how they pull together both my casual baggy denim look and these relaxed khaki trousers. Total earthy, effortless fall vibes. #thriftedstyle #vintagefashion
 
**Real output, criterion 5, denim jacket query, try 1 (after, from the c5b run):**
 
stopped early: yes — Model error during 'outfit': the model couldn't be reached (ModelUnavailable). Check your API key in .env, then try again.
 
**Did it help, and how do I know:** Yes. The revised criterion 1 went from 0/5 to 5/5: every try on the boots query now selects Suede Chelsea Boots — Tan instead of Biker Shorts. The change didn't break anything else. Criteria 1–4 still pass 5/5, and every other scenario selected the same item before and after (butterfly tee, denim jacket, flannel, Chelsea boots, cords, track jacket), so the bonus only changed rankings where the item word was being outvoted.



---

## What's Still Broken
 
All five original criteria and the revised criterion 1 are met after the fix, so nothing on my criteria list is still missed. These are the problems I found that my criteria don't cover:
 
- **The empty-search message points at the wrong lever.** On 'designer ballgown size XXS under $5', it says "Try broader words, like 'tee' instead of 'band tee'" but never mentions the size XXS or $5 limits, and broader words alone would still fail under them. When I tested the message as a user who can't see the code, the answer was that I'd have to guess and drop filters one at a time. I wrote a fix (a _no_results_message that names the active filters and tests dropping both at once) but didn't apply it, because this unit allows only one improvement and the ranking bug was the one my diagnosis named. Criterion 2 passes on the letter ("names what to change") but not the spirit, so I'd tighten it to "names every active filter when one or more is set."
- **The "last word is the item" rule is a heuristic.** It works when the item noun comes last ("black combat boots"), but a query like "boots in black" would boost "black" instead. Next I'd match keywords against the category field, mapping "boots" to shoes, rather than relying on word order.
- **Search returns weak matches instead of nothing.** If the catalog had no boots at all, the boots query would still return black clothing and report success rather than reaching the empty-search branch. I'd add a minimum score, or require that the item word matches, before a result counts.
- **Two of my criteria were too easy.** Criterion 4 passed 25/25 against a 4/5 target, and criterion 3 is close to unfailable as built. I'd tighten criterion 4 (for example, the card must mention the brand when the listing has one) and make criterion 3 compare the session against what the tool actually logged receiving, not the same variable.
- **My criterion 5 "after" run didn't use the scenarios I planned.** The FITFINDR_RUN switch in scenarios.py didn't take effect in either attempt, and I didn't track down why. Next I'd verify the switch first by printing len(scenarios.SCENARIOS) in the same terminal before running, or pass the run mode as a command-line flag instead of an environment variable.

```


<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
