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

**What moves through the session:** `query` → `parsed` (description, size, max_price) → `search_results` → `selected_item` → `last_suggested_item_id` + `outfit_suggestion` → `last_fit_card_item_id` + `fit_card`. Each tool reads its inputs from the session, not from the previous call's return value. If a model call fails, the loop catches `ModelUnavailable`, sets `session["error"]`, leaves `fit_card` as `None`, and stops.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask '...'

```

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

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



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
