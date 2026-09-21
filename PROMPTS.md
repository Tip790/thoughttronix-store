# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-09-20 — Product.is_featured, from model field to Featured badge

### Prompts

1. "In the Product model, add an is_featured field. It is a boolean and
   defaults to non-featured"
2. "The is_featured field does not show up on the website," — correction,
   after the first prompt was implemented as the model field only.
3. "add a Featured badge if the product is featured" — sent after
   interrupting and rejecting the two template edits that were in flight.
4. "Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways."

### Summary

- **Outcome:** `is_featured = BooleanField(default=False)` on `Product`,
  with migration `products/0003_product_is_featured.py` (created and
  applied). Surfaced in four places: a `Featured` badge on the catalog
  card and on the product detail page (whose badge row became
  `flex flex-wrap gap-2` to hold two badges), the field added to
  `ProductForm` so the back-office form renders a toggle for it, and
  `list_display` / `list_filter` in `ProductAdmin`. Suite green at both
  stops — 164 passed after the model change and again at the end. No seed
  data sets the flag, so no badge renders until a product is toggled on.
- **Deviations:** the first prompt was read narrowly as a model-only
  change; the offer to add a `featured()` queryset method or expose the
  field in the back-office form was made but not acted on, which is what
  prompt 2 pushed back on. Closing offers to feature products in the
  `seed` command or add a badge column to the back-office product table
  were left unanswered.
- **Sideways:** the template edits for the badge were issued as an
  assumption about what "does not show up on the website" meant, and were
  rejected mid-call with an interrupt. Prompt 3 then asked for exactly
  that badge, and the same two edits were re-applied unchanged — a round
  trip that a question instead of an assumption would have avoided. Also
  logged: Pylance reported unresolved `django.db` / `django.urls` imports
  in `products/models.py` after the edit; ignored as an editor
  interpreter-path artifact, not a real breakage, since the migration and
  the full suite both ran clean.
