# Plan: The ThoughtTronix Store — Product Reviews

> Source PRD: `prd/reviews.md` (follows `prd/core-platform.md`, `prd/account-security.md` and `prd/wishlist.md`)

*The PRD owns the requirements; this plan owns the sequence. Where a phase says "per the PRD," the PRD's wording is authoritative. The suite must be green at every phase boundary.*

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: a new `reviews` app. Its Python code depends on `products`, `orders` and `accounts`. Nothing in `products`, `orders`, `coupons`, `wishlists` or `accounts` imports `reviews`. The product detail template includes the reviews section, which is a template include, not an import, and the product detail view doesn't change. The one deliberate exception is the `seed` command, which imports `reviews` the way it already imports `wishlists`. No service module and no new dependencies.
- **Models**:
  - `Review`: an FK to the user (`related_name="reviews"`, `CASCADE`) and an FK to `Product` (`related_name="reviews"`, `CASCADE`), plus `rating`, `comment`, `created_at` and `updated_at`.
  - `rating` is a small positive integer. Model validators enforce 1–5, and a database `CheckConstraint` backs them up.
  - A database `UniqueConstraint` on (user, product) enforces one review per customer per product, even under concurrent requests.
  - `created_at` uses a default, not auto-now-add, so the seed can backdate reviews. `updated_at` is set on every save. A review counts as "edited" when `updated_at` is meaningfully later than `created_at`.
  - Reviews are ordered newest first by `created_at`, so editing never reorders anything.
  - The reviewer's display name (first name and last initial, falling back to the username) is a model method.
  - Eligibility is a single model-level check (a class method or queryset method). It's true when the user has an order line for the product on an order whose status isn't `CANCELLED`. It's checked on create only. Edit and delete are gated on authorship alone.
  - A queryset method returns a product's average rating and review count in one query.
- **URLs**: all routes are in the `reviews` namespace and are included in the root URLconf ahead of the `products` slug routes. Every route is keyed by product pk and looks the product up across the whole catalog, unavailable products included. An unknown pk returns 404.
  - `/reviews/<pk>/` is the reviews section (`GET`, public).
  - `/reviews/<pk>/create/` is Create (`POST`).
  - `/reviews/<pk>/edit/` is the edit form (`GET`).
  - `/reviews/<pk>/update/` is Update (`POST`).
  - `/reviews/<pk>/card/` is the author's own card (`GET`). It powers Cancel.
  - `/reviews/<pk>/delete/confirm/` is the delete confirmation (`GET`).
  - `/reviews/<pk>/delete/` is Delete (`POST`).
  - `/reviews/<pk>/more/?page=N` is the next batch of other customers' reviews (`GET`, public), using Django's paginator, 10 per page.
- **Authorization**:
  - Every mutation, and every view that returns a form or the author's own card, uses `LoginRequiredMixin`. Anonymous requests are redirected and create nothing.
  - Every lookup of the author's review goes through `request.user`. No customer-facing view fetches a review by bare id. Only the staff-only back-office views (Phase 6) look reviews up by pk.
  - Stale states (the review no longer exists, or already exists on create) return the user's current state for their slot, never an error.
  - Staff and the superuser review like any customer on product pages. Moderation is the back-office Reviews tab (staff, Phase 6) and the Django admin (superuser).
- **Page integration**: the product detail page includes a placeholder that loads `/reviews/<pk>/` once the page loads. That endpoint is the single source for the section's content.
- **HTMX**:
  - The author's slot is one stable element with a fixed id at the top of the section. Every write, edit, cancel, delete and confirm swaps only that element.
  - The summary line updates out of band after every change.
  - Show more appends below the list and replaces only itself.
  - Signed-out visitors are never given an HTMX control. They get a plain sign-in link with `next` pointing back to the product page.
  - The detail page's only `btn-primary` stays add-to-cart. Review controls use ghost or outline styles, and destructive confirmation uses semantic error styling.
  - Templates follow `docs/TEMPLATES.md`.
- **Admin**: `Review` is registered with a list showing product, reviewer, rating and dates, filters by product and rating, and search over the comment.
- **Back office** (Phase 6): a Reviews tab in the `reviews` namespace, every view behind `StaffRequiredMixin`, pk URLs, following the Coupons tab's pattern.
  - `/backoffice/reviews/` is the list (`GET`), filtered by product and rating, paginated.
  - `/backoffice/reviews/<pk>/edit/` is the edit form (`GET`, `POST`).
  - `/backoffice/reviews/<pk>/delete/` is the delete confirmation and delete (`GET`, `POST`).

---

## Phase 1: Read-only reviews section

**User stories**: 1, 2, 3, 5, 6, 7, 8, 34, 37

### What to build

This is the tracer bullet through every layer. It creates:

- the `reviews` app with the `Review` model and its migration
- the admin registration
- the reviews section endpoint
- the section, summary line and review card partials
- the placeholder on the product detail page that loads the section

The summary line shows the average rating and count (for example "★ 4.3 · 12 reviews") or a designed "No reviews yet" empty state. Below it, the first 10 reviews are listed newest first. Each card shows the reviewer's display name, a "Verified purchase" badge, the date, the star rating, the comment, and an "edited" marker when the review was changed after posting. In this phase, reviews exist only through the admin or test fixtures.

The author's slot isn't built yet. The section reserves its place at the top.

### Acceptance criteria

- [ ] The database rejects a second review for the same (user, product) pair and a rating outside 1–5.
- [ ] Deleting a product deletes its reviews.
- [ ] The display name is the first name and last initial ("Mira K."), and falls back to the username when no name is set.
- [ ] The aggregate returns the correct average and count in one query, and handles a product with no reviews.
- [ ] The "edited" rule distinguishes an edited review from one saved only once.
- [ ] The section endpoint renders the summary and up to 10 reviews newest first, or the empty state when there are none.
- [ ] The product detail page loads the section for any visitor, and the product detail view is unchanged.
- [ ] An unknown product pk returns 404.
- [ ] `Review` appears in the Django admin with the agreed columns, the product and rating filters, and comment search.
- [ ] Nothing in `products`, `orders`, `coupons`, `wishlists` or `accounts` imports `reviews`.
- [ ] The migration applies cleanly to the committed database.

---

## Phase 2: Visitor states and writing a review

**User stories**: 4, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 27, 30, 31, 33, 35

### What to build

This phase adds:

- the eligibility check
- the review model form, which owns all validation per the PRD: a trimmed comment of 10–2,000 characters with `maxlength` on the textarea, and a required rating rendered as labelled DaisyUI `rating` radio inputs
- the author's slot, in four states:
  - a sign-in link with `next` for signed-out visitors
  - an "only customers who've bought it can review it" note for signed-in non-buyers
  - the review form for buyers who haven't reviewed the product
  - the author's own card for customers who have
- the Create endpoint

On success, Create returns the author's card plus the summary out of band. On invalid input it returns the form with errors and the submitted values. For an ineligible user it returns the note. If a review already exists (a double submit or a stale tab), it creates nothing and returns the existing card.

The author's own review appears only in their slot, never in the list below it.

Fixtures are added to the project-level conftest: a customer with a non-cancelled order for a product, a customer whose only order for it is cancelled, a customer with no order, and a second customer for privacy tests.

### Acceptance criteria

- [ ] Eligibility is true for PLACED, SHIPPED and DELIVERED orders, and false for CANCELLED orders and no order. An unavailable product can be reviewed by its buyers.
- [ ] The form trims the comment, rejects blank, whitespace-only, under-10 and over-2,000 comments with clear messages, and rejects a missing or out-of-range rating.
- [ ] The rating renders as five labelled radio inputs. The textarea carries `maxlength`.
- [ ] Each of the four visitor states renders correctly in the author's slot. The sign-in link's `next` returns to the same product page, and signed-out visitors get no HTMX control.
- [ ] A successful create returns the author's card and an out-of-band summary with the new average and count.
- [ ] Invalid input returns the form with errors and keeps everything typed.
- [ ] A non-buyer's create creates nothing and returns the note.
- [ ] A second create for the same product creates nothing and returns the existing card.
- [ ] Anonymous create redirects to login and creates nothing.
- [ ] The author's own review is excluded from the list of other customers' reviews.
- [ ] A staff user who bought the product can review it.
- [ ] The add-to-cart button is still the detail page's only `btn-primary`.

---

## Phase 3: Edit and delete your own review in place

**User stories**: 22, 23, 24, 25, 26, 27, 28, 29, 31

### What to build

This phase adds the Edit form, Update, Card, Delete confirmation and Delete endpoints. Every one of them acts only on the requesting user's own review, and every one swaps only the author's slot.

- **Edit** turns the card into a pre-filled form in the same spot.
- **Save** validates and returns the updated card plus the summary out of band, or the form with errors.
- **Cancel** fetches the card and restores it unchanged.
- **Delete** shows the card in its "Delete this review? Yes, delete / Keep it" state. **Keep it** restores the card. **Yes, delete** removes the review and returns the empty form plus the summary out of band.

Acting on a review that no longer exists, for example from a stale tab, returns the user's current slot state (the form or the note) rather than an error. Edit and delete are gated on authorship only, so an author whose order was later cancelled keeps full control.

### Acceptance criteria

- [ ] The edit form is pre-filled with the author's current rating and comment.
- [ ] Update saves the change, returns the updated card with the "edited" marker, and includes the out-of-band summary.
- [ ] Invalid update input returns the form with errors and keeps what was typed.
- [ ] The card endpoint returns the unchanged card, which powers Cancel and Keep it.
- [ ] The delete confirmation returns the card in its confirm state with semantic error styling on the destructive button.
- [ ] Delete removes the review and returns the empty form plus the out-of-band summary.
- [ ] Stale edit, update, card, confirmation and delete requests return the user's current slot state, not an error.
- [ ] One customer can never edit or delete another customer's review.
- [ ] An author whose order was cancelled after reviewing can still edit and delete.
- [ ] Anonymous requests to every endpoint in this phase redirect to login and change nothing.
- [ ] Editing a review doesn't change its position in anyone's list.

---

## Phase 4: Show more reviews

**User stories**: 9, 10

### What to build

This phase adds the "more reviews" endpoint and its batch partial. When other customers' reviews run past the first 10, the section ends with a "Show more reviews" button. Each click appends the next 10 below the existing reviews and replaces only the button, with a new button when more remain. The endpoint is public, uses Django's paginator, and always excludes the requesting user's own review.

### Acceptance criteria

- [ ] The section shows the "Show more reviews" button only when more than 10 other reviews exist.
- [ ] The endpoint returns 10 reviews per page, newest first, continuing from the previous page.
- [ ] The last page returns its reviews without a button.
- [ ] The requesting user's own review never appears in any batch.
- [ ] The endpoint works for anonymous visitors. An unknown product pk returns 404.

---

## Phase 5: Account deletion, the demo world and the AI-usage log

**User stories**: 32, 36

### What to build

- **Account deletion.** `User.anonymize()` deletes all of the user's reviews alongside their addresses, cart and wishlist. It reaches them through the reverse relation name, so `accounts` gains no import of `reviews`. The method's docstring is updated to mention reviews.
- **Seed.** The wipe step clears reviews so reseeding stays idempotent. Using the seed's fixed random source, the seed creates:
  - for the demo customer, one product they've ordered and reviewed, at least one they've ordered but not reviewed, and many they've never ordered
  - one product with more than 10 reviews from seeded customers with mixed ratings, so Show more and a realistic average both appear

  Every seeded review is backed by a non-cancelled order for that reviewer and product.
- **AI-usage log.** The design interview, PRD and plan sessions are appended to `PROMPTS.md`, following its convention.

### Acceptance criteria

- [ ] After `anonymize()`, none of the user's reviews remain. Anonymizing a user with no reviews succeeds.
- [ ] `accounts` doesn't import `reviews`.
- [ ] After `seed`, the demo customer has exactly the agreed states: reviewed, bought but not reviewed, and never bought.
- [ ] After `seed`, one product has more than 10 reviews with mixed ratings.
- [ ] Every seeded review is backed by a non-cancelled order for its reviewer and product.
- [ ] Running `seed` twice gives the same result.
- [ ] Every review state is visible right after seeding.
- [ ] `PROMPTS.md` has new entries appended, and no earlier entries are changed.

---

## Phase 6: Staff moderation in the back office

**User stories**: 28, 38, 39, 40

### What to build

This phase adds a Reviews tab to the back office, beside Products, Orders and Coupons, following the Coupons tab's pattern: full-page class-based views, `StaffRequiredMixin` on every view, pk URLs and `manage_*` names and templates.

- **List:** every review, newest first, showing product, reviewer display name, rating, a comment excerpt and dates. It filters by product and rating and paginates like the other tabs. Each row links to Edit and Delete.
- **Edit:** a pre-filled page using the existing review model form, so the same trimming, length and rating rules apply. Staff can change the rating and comment. The reviewer and product never change. Saving sets `updated_at`, so the ordinary "edited" marker shows. Nothing marks it as a staff edit.
- **Delete:** a confirmation page with semantic error styling on the destructive button, then the review is removed.
- The tab is reached from the back-office navigation. Success messages follow the other tabs.

Nothing changes on the customer-facing product page. Staff still have their own ordinary review slot there.

### Acceptance criteria

- [ ] The Reviews tab appears in the back-office navigation for staff.
- [ ] The list shows every review newest first, and filters by product and by rating.
- [ ] Staff can edit any review's rating and comment. Invalid input re-renders the form with errors and the typed values. The reviewer and product don't change.
- [ ] A staff-edited review shows the "edited" marker on the product page.
- [ ] Staff can delete any review after a confirmation page.
- [ ] Customers are refused, and anonymous visitors are redirected to login, on every back-office review view, and nothing changes.
- [ ] An unknown review pk returns 404.
- [ ] The customer-facing review endpoints are unchanged: one customer still can't reach another's review.
