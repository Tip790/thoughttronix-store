# Plan: The ThoughtTronix Store — Customer Wishlist

> Source PRD: `prd/wishlist.md` (follows `prd/core-platform.md` and `prd/account-security.md`)

*The PRD owns the requirements; this plan owns the sequence. Where a phase says "per the PRD," the PRD's wording is authoritative. The suite must be green at every phase boundary.*

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: a new `wishlists` app. Its Python code depends only on `products` and `accounts`. Nothing in `products`, `orders`, `coupons` or `accounts` imports `wishlists`. Catalog templates include the button partial, which is a template include, not an import. The one deliberate exception is the `seed` command, which imports `wishlists` the way it already imports `orders` and `coupons`. No service module and no new dependencies.
- **Models**:
  - `Wishlist`: a one-to-one link to the user (`related_name="wishlist"`, `CASCADE`). It has no name field. It's created lazily through a `for_user` class method, following `Cart`.
  - `WishlistItem`: an FK to `Wishlist` (`related_name="items"`, `CASCADE`), an FK to `Product` (`CASCADE`) and an added-at timestamp. Items are ordered newest first. A database `UniqueConstraint` on (wishlist, product) backs up the rule that a product appears at most once.
  - `add` and `remove` are model methods. `add` is idempotent, and `remove` does nothing when the product isn't on the list.
- **URLs**: all routes are in the `wishlists` namespace and are included in the root URLconf ahead of the `products` slug routes.
  - `/wishlist/` is the wishlist page (`GET`). It takes no user or wishlist id.
  - `/wishlist/add/<pk>/` is Add (`POST`, keyed by product pk).
  - `/wishlist/remove/<pk>/` is Remove (`POST`, keyed by product pk).

  Add and Remove are two endpoints, not a toggle, so the button always does what its label says.
- **Authorization**:
  - All three views use `LoginRequiredMixin`, so anonymous requests are redirected and create nothing.
  - Every lookup goes through `request.user`. No view fetches a wishlist or item by bare id.
  - Product lookups span the whole catalog, unavailable products included, unlike add-to-cart.
  - An unknown product pk returns 404.
- **Page-load state**: a `wishlists` context processor, registered next to the `cart` one, supplies the signed-in user's set of wishlisted product ids in one query. Anonymous visitors get an empty set. Button states and the navbar count both come from it.
- **HTMX**:
  - Signed-in users get a `<button>` that swaps itself out. Signed-out visitors get a plain sign-in link with `next`, never an HTMX button.
  - The button never uses `btn-primary`. It carries `aria-pressed`.
  - Templates follow `docs/TEMPLATES.md`.
- **Admin**: `Wishlist` is registered with an inline for its items, matching the cart's admin. There is no back-office tab.

---

## Phase 1: Save from the product detail page

**User stories**: 2, 3, 4, 5, 6, 7, 8, 17, 18, 20, 21, 22, 23, 25

### What to build

This is the tracer bullet through every layer. It creates:

- the `wishlists` app with both models and their migration
- the admin registration with an items inline
- the Add and Remove endpoints, which share a base view that resolves the product, acts on the requesting user's own wishlist and renders the button partial in its new state
- the wishlist button partial, included on the product detail page

When the product isn't saved, the button reads "♡ Save" in ghost style with `aria-pressed="false"`. When it is saved, the button reads "♥ Saved" in outline style with a semantic-coloured heart and `aria-pressed="true"`. Signed-out visitors see the button as a sign-in link whose `next` points back to the current page. The `wishlists` context processor is registered so the button shows the correct state on page load. Staff and the admin save products like any user.

### Acceptance criteria

- [ ] `Wishlist.for_user` creates exactly one wishlist per user, lazily, and returns the same one on later calls.
- [ ] Adding twice leaves one row. Removing a product that isn't saved does nothing. A duplicate (wishlist, product) row is rejected by the database.
- [ ] Deleting a product removes it from every wishlist.
- [ ] Add returns the button in its "Saved" state with `aria-pressed="true"`. Remove returns it in its "Save" state with `aria-pressed="false"`.
- [ ] Posting Add for an already-saved product (or Remove for an unsaved one) leaves the state matching the button's label. It never flips the other way.
- [ ] An unavailable product can be saved.
- [ ] An unknown product pk returns 404 on both endpoints.
- [ ] Anonymous Add and Remove requests redirect to login and create no rows.
- [ ] The detail page shows the saved state on load for a product saved earlier. For a signed-out visitor it shows a sign-in link with the correct `next`.
- [ ] The context processor returns an empty set for anonymous visitors and the correct id set for a signed-in user.
- [ ] One customer's Add and Remove never touch another customer's rows. A staff user can save a product.
- [ ] `Wishlist` appears in the Django admin with its items inline.
- [ ] The migration applies cleanly to the committed database.

---

## Phase 2: The wishlist page

**User stories**: 9, 10, 11, 12, 13, 14, 18

### What to build

This phase adds the `/wishlist/` page. It extends the base template and opens with the standard heading and one-line description. A wishlist contents partial renders the saved products newest first. Each row shows:

- the product
- an "Unavailable" badge when the product can't be bought right now
- the existing add-to-cart partial, which already renders its disabled state for unavailable products
- the wishlist button, configured to target the contents container and to send the page flag

When the flag is present, Remove returns the contents partial (the remaining rows, or a designed empty state) instead of the button. Adding to the cart from the wishlist leaves the item saved. A second customer fixture is added to the project-level conftest for the privacy tests.

### Acceptance criteria

- [ ] The page lists only the requesting user's items, newest first.
- [ ] Unavailable products show the "Unavailable" badge and a disabled add-to-cart button.
- [ ] Adding a saved product to the cart leaves it on the wishlist.
- [ ] Remove with the page flag returns the contents partial without the removed item. Removing the last item returns the empty state.
- [ ] Remove without the flag still returns the button partial, as in Phase 1.
- [ ] A customer with no wishlist yet sees the empty state.
- [ ] Anonymous visitors to the page are redirected to sign in.
- [ ] Two customers' wishlists never appear on each other's pages.

---

## Phase 3: Navbar link with a live count

**User stories**: 15, 16

### What to build

This phase adds a wishlist badge partial: a "♥ Wishlist" link to `/wishlist/` with a count badge. It's shown next to the cart badge to signed-in users only. The count is the size of the context processor's id set, so it needs no extra query. Every Add and Remove response appends the badge as an out-of-band swap, including the page variant's contents response, so the count updates the moment something is saved or removed.

### Acceptance criteria

- [ ] Signed-in users see the Wishlist link with the correct count on every page. Signed-out visitors don't see it.
- [ ] Add, Remove and the page-variant Remove each include the out-of-band badge with the updated count.
- [ ] Rendering the badge adds no query beyond the context processor's one.

---

## Phase 4: Save from catalog cards

**User stories**: 1 (and 4, 5 on the catalog)

### What to build

This phase includes the wishlist button on every catalog card. Each card's button starts in the right state from the context processor's set, and the button swaps in place without disturbing the card or the page. Signed-out visitors see the sign-in link, whose `next` keeps the current catalog URL, including search and filter parameters.

### Acceptance criteria

- [ ] Each catalog card renders the correct starting state for the signed-in user, including for unavailable products.
- [ ] Saving from a card returns the swapped button and the out-of-band badge.
- [ ] Signed-out visitors see sign-in links whose `next` returns to the same catalog page.
- [ ] The add-to-cart button is still the card's only `btn-primary`.

---

## Phase 5: Account deletion and the demo world

**User stories**: 19, 24

### What to build

- **Account deletion.** `User.anonymize()` deletes the user's wishlist, if there is one, right after deleting the cart, and its items cascade with it. It reaches the wishlist through the reverse relation name, so `accounts` gains no import of `wishlists`. The method's docstring is updated to mention the wishlist.
- **Seed.** The wipe step clears wishlists so reseeding stays idempotent. The demo customer is then given a wishlist of three or four products, at least one of them unavailable.
- **AI-usage log.** The design interview, PRD and plan sessions are appended to `PROMPTS.md`, following its convention.

### Acceptance criteria

- [ ] After `anonymize()`, the user has no wishlist and none of their wishlist items remain. Anonymizing a user without a wishlist succeeds.
- [ ] `accounts` doesn't import `wishlists`.
- [ ] After `seed`, the demo customer has three or four saved products, at least one unavailable. Running `seed` twice gives the same result.
- [ ] Every state is visible right after seeding: saved and unsaved buttons, the navbar count, and the Unavailable badge on the wishlist page.
- [ ] `PROMPTS.md` has new entries appended, and no earlier entries are changed.
