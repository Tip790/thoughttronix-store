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

## 2026-10-04 — Product images, grilled and handed off (not yet built)

### Prompts

1. `/grill-me` "create product images for the catalog using the images in
   @product-images\.These images should match the products they are
   associated with, and if a product does not have an image it will keep
   it's existing placeholder instead of a missing file or broken image.
   Emplyess must also be able to upload product images through the back
   office, if an employees provides a file the site cannot use, reject it
   and explain the problem in plain language."
2. Answers to the grilling questions, in order (one reply each):
   1. "A" — one optional `Product.image` `ImageField`, no gallery model
   2. "A" — `SoulSear No Text.png` goes to SoulSear Mark II only
   3. "B" — the SyncRest **Text** (poster) version, not the No Text one
   4. "A" — sources move to `products/seed_images/` and are committed; `seed`
      clears `media/products/` and attaches them
   5. "A" — normalize every image: longest side ≤ 1200px, WebP, metadata
      stripped
   6. "A" — five validation rules, each with its own plain-language message;
      HEIC rejected, not supported
   7. "A" — upload, replace, and remove; old files deleted after the save
      commits
   8. "b" — 4:3 card frame with `object-contain` on a dark background
3. `/handoff` "the next session implements the design we just agreed"
4. "Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways."

### Summary

- **Outcome:** a design only, with no code written. The eight decisions
  above, the file-to-product mapping (12 of 34 products get images), the
  validation messages, and the test list are recorded in `HANDOFF.md` for
  the next session to implement. No PRD or plan file was written.
- **Deviations:** one. On question 3 the agent recommended the SyncRest
  No Text image (it reads better at card size and fits the one-image
  model), and the user chose the Text poster version. Question 8 was then
  decided partly because of that choice: `object-contain` keeps the
  poster's text from being cropped on the cards. Every other answer took
  the recommended option. The user asked no follow-up questions. After the
  grilling, the agent offered to write a PRD and plan or to implement
  right away, and the user chose a `/handoff` instead.
- **Sideways:** nothing failed. While exploring, the agent found that the
  uncommitted `config/urls.py` change already serves `MEDIA_URL`, but
  `config/settings.py` defines neither `MEDIA_URL` nor `MEDIA_ROOT`. This
  gap was already in the working tree, not caused this session; it is
  flagged in `HANDOFF.md` as the first thing to fix. The source-image names
  needed judgment calls: three SoulSear products for one image, two SyncRest
  versions, and filenames with "GPT"/"Text" suffixes. The agent mapped the
  unambiguous names itself and asked the user only about SoulSear and
  SyncRest.

## 2026-09-27 — Discount coupons, grilled then built; then a coupon-failure pop-up

### Prompts

1. `/grill-me` "Add discount coupons via seasonal promotion to be added
   during checkout when a customer types a code, reducing the total of the
   order. Codes expire when the promotions end, with a customer receiving
   a message saying so. Codes will be made and retired by marketing,
   retiring a code should not change any previous order that used it. The
   coupon system supports discounts on orders and discounts on specific
   products, such as a 50% discount on Seraphine for a limited time."
2. Answers to the grilling questions, in order (one reply each):
   1. "A" — one `Coupon` model, no separate `Promotion`
   2. "b" — explicit `scope` (ORDER / PRODUCTS) plus a products M2M
   3. "a" — percentage discounts only
   4. "b" — order-level snapshot plus a per-line `discount`
   5. "a" — soft retire (`is_active`), `Order.coupon` is `PROTECT`
   6. "A plus uppercase normalization" — codes unique forever
   7. "A" — calendar dates, both required and inclusive
   8. "A" — `TIME_ZONE` from `.env`, default `America/Chicago`
   9. "A" — a specific message for each failure reason
   10. "Can B be done without HTMX?" — follow-up question; after the
       answer: "b with the HTMX Apply"
   11. "A" — a failed code at submit blocks the order
   12. "B" — once per customer
   13. "A" — marketing is staff; a Coupons back-office tab
   14. "b" — a new `coupons` app with one-way dependencies
   15. "A" — `ROUND_HALF_UP`
   16. "b" — advertise product promos with a badge
   17. "b" — badges on the detail page and the catalog cards
   18. "A" — the same badge for everyone
   19. "b" — lock a used coupon's terms; dates stay editable
   20. "b" — usage columns on the coupon list only
   21. "c" — seed coupons plus past orders that used them
   22. "C" — the cap depends on scope; then "b" — whole-order cap of 50%
   23. "C" — skip the PRD and plan, implement now
3. `/context` — a built-in command run between the two features, not a
   request to the agent.
4. "on checkout, if a coupon does not work display it in a more noticible
   way, a pop-up if possible" — the agent began editing straight away;
   the user rejected the three in-flight edits and interrupted.
5. `/grill-me` "on checkout, if a coupon does not work display it in a
   more noticible way, a pop-up if possible"
6. Answers, in order: "A" (a modal dialog), "A" (for both Apply and
   submit), "A" (the red field text is the only inline reminder), "B"
   ("Try another code" and "Continue without a coupon" buttons), "B" (the
   on-brand title with the plain reason underneath).
7. "Implement this feature"
8. "Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways."

### Summary

- **Outcome:** a new `coupons` app. `Coupon` supports whole-order and
  product scopes, percent off, and a date run in store time. It carries
  the redemption rule (`Coupon.objects.redeemable`), which raises
  `CouponError` with the customer-facing message, and a single discount
  calculation (`Coupon.discounts`, rounded half-up). The Coupons
  back-office tab supports list with usage columns and an active/retired
  filter, create, edit (terms locked once used), retire/reactivate, and
  delete-if-unused. `place_order`'s `coupon_code` parameter now re-checks
  the code and copies the discount onto `Order` (`discount_amount`,
  `coupon` FK with `PROTECT`, `coupon_code`, `coupon_percent_off`) and
  onto `OrderItem.discount`. Checkout gained a coupon field, an HTMX Apply
  preview, and a submit that blocks the order on a bad code. Live product
  coupons show badges on catalog cards and the detail page, loaded in one
  prefetch with a query-count test. The dashboard's top products now
  subtract line discounts. The seed creates 5 coupons plus past orders
  that used them. `TIME_ZONE` is read from `.env` and defaults to
  `America/Chicago`. CLAUDE.md was updated. Then the pop-up: a DaisyUI
  `<dialog>` modal with no custom JavaScript, shown on failed Apply and on
  failed submit, with "Try another code" / "Continue without a coupon".
  The summary's yellow alert was removed. Suite went 209 → 284 → 289
  passed, ruff clean. Nothing committed.
- **Deviations:** from the recommendation on Q12 (chose once per
  customer over unlimited), Q16 (chose advertising badges over keeping
  codes invisible), Q22 (chose a scope-dependent cap over allowing 1–100%
  everywhere), and the final question (chose to implement now instead of
  writing `prd/coupons.md` and `plans/coupons.md` first; no PRD or plan
  exists for this feature). Follow-up question on Q10 about doing Apply
  without HTMX. Where a reply was terse, the agent assumed the
  recommendation's add-ons were included: cancelled orders give back the
  once-per-customer use (Q12), `coupon_percent_off` is copied and "any
  order locks" (Q19), and the ≥50% warning is kept (Q22b). The
  implementation departs from the agreed design in three places: order
  subtotal is a derived property (`total + discount_amount`) rather than
  a stored field; `products/views.py` imports `coupons` for the badge
  prefetch, though the models keep the one-way direction; and `coupons`
  spells out `"CANCELLED"` rather than importing `orders`, pinned by a
  test.
- **Sideways:** on the pop-up request, the agent jumped straight into
  edits without asking about the design, and the user rejected them and
  re-ran `/grill-me`. The design the grilling produced was close to the
  rejected one but added the two-button choice and the single inline
  reminder. Smaller slips, all caught before the end: a pointless
  `settings` import in `coupons/models.py` (removed at once); one Edit
  failed on a mismatched docstring and was retried; a test expected
  419.99 where the math gives 418.99 (the suite caught it); ruff flagged
  method order (DJ012) and `zip()` without `strict=` (B905), both fixed;
  a new pop-up test compared against the first `</form>`, which is the
  navbar's sign-out form, so it proved nothing until it was tightened;
  and `tailwind build` reported the stylesheet up to date when it lacked
  the modal styles, so it needed `--force`. Neither feature was checked in
  a browser. Tests confirm the rendered HTML only.

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
