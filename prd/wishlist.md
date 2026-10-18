# PRD: The ThoughtTronix Store — Customer Wishlist

*A follow-on to the core platform and account security PRDs.*

---

## Problem Statement

A ThoughtTronix customer who finds a product they like but are not ready to buy has nowhere to put it. Today their only options are poor ones:

- **Use the cart as a wishlist.** The cart is for buying. Parking "someday" products there clutters checkout and mixes things the customer wants now with things they might want later.
- **Remember it.** The catalog has search and filters, but a customer has to find the product again from scratch every time.
- **Lose track of products that go out of stock.** An unavailable product cannot be added to the cart, so a customer has no way to mark "I want this when it comes back."

Customers also expect saving a product to be instant. Saving shouldn't reload the page, and it should always be obvious whether a product is already saved.

## Solution

Every signed-in customer has exactly one personal wishlist. It has no name. It's simply "your wishlist."

- **A Save button on every product.** Catalog cards, the product detail page, and the wishlist page show a button that reads "♡ Save" when the product is not on the wishlist and "♥ Saved" when it is. Clicking it adds or removes the product immediately, without reloading the page, and the button changes to show the new state.
- **Any catalog product can be saved**, including products that are currently unavailable.
- **A wishlist page** lists saved products, newest first. Each row shows the product, an "Unavailable" badge when it can't be bought right now, the standard add-to-cart button, and the Saved button. Removing an item takes it off the list on the spot, and removing the last item shows a designed empty state.
- **A navbar link with a count.** Signed-in users see a "♥ Wishlist" link next to the cart, with a badge showing how many products are saved. The count updates the moment something is saved or removed.
- **Signed-out visitors** see the Save button as a link to sign in, which brings them back to the page they were on.
- **Strict privacy.** A customer can only ever see and change their own wishlist. There is no way, by URL or otherwise, to view or modify someone else's. Staff and the admin have their own wishlists like any user, and the store's back office has no view of customers' wishlists.
- **Deleting an account deletes the wishlist** along with the rest of the customer's personal data.
- **The demo world includes a wishlist.** After seeding, the demo customer has a few saved products, one of them unavailable.

## User Stories

1. As a customer, I want to save a product from the catalog page, so that I can come back to it later without searching again.
2. As a customer, I want to save a product from its detail page, so that I can save it while reading about it.
3. As a customer, I want saving and removing to happen without a page reload, so that I don't lose my place while browsing.
4. As a customer, I want the Save button to show whether a product is already on my wishlist, so that I never have to guess.
5. As a customer, I want the button to show the correct state as soon as the page loads, so that products I saved earlier are already marked as saved.
6. As a customer, I want clicking "♥ Saved" to remove the product from my wishlist, so that I can change my mind with one click.
7. As a customer, I want a double-click or a stale browser tab never to do the opposite of what the button says, so that a product I meant to save doesn't get removed.
8. As a customer, I want to save products that are currently unavailable, so that I can keep track of things I want when they come back.
9. As a customer, I want unavailable products on my wishlist clearly labelled, so that I know why I can't add them to my cart.
10. As a customer, I want a wishlist page listing everything I've saved, newest first, so that I can review my saved products.
11. As a customer, I want to add a product to my cart straight from my wishlist page, so that buying something I saved is one click.
12. As a customer, I want a product to stay on my wishlist after I add it to my cart, so that I decide when to take it off.
13. As a customer, I want removing an item on the wishlist page to take it off the list immediately, so that the page always matches my wishlist.
14. As a customer, I want a friendly empty state when my wishlist is empty, so that I know the page works and what to do next.
15. As a customer, I want a Wishlist link in the navbar with a count of saved items, so that I can reach my wishlist from anywhere and see that saving worked.
16. As a customer, I want the navbar count to update the moment I save or remove something, so that it's always accurate.
17. As a customer, I want only one wishlist, so that I never have to choose where to save something.
18. As a customer, I want my wishlist to be private, so that no other customer can see or change what I've saved.
19. As a customer, I want my wishlist deleted when I delete my account, so that none of my personal preferences stay behind.
20. As a signed-out visitor, I want the Save button to take me to sign in and then back to the page I was on, so that I can start saving without losing my place.
21. As a staff member, I want my own wishlist like any other user, so that I can shop the store the same way customers do.
22. As a screen-reader user, I want the Save button announced as an on/off toggle, so that I know whether a product is saved.
23. As the administrator, I want to inspect wishlists in the Django admin, so that I can investigate a customer's problem.
24. As a developer or grader, I want the seeded demo customer to have a wishlist with both available and unavailable products, so that every state of the feature is visible straight after seeding.
25. As a developer, I want a product's deletion to remove it from every wishlist, so that wishlists never point at products that no longer exist.

## Implementation Decisions

**A new `wishlists` app.**
- Its Python code depends only on `products` and `accounts`. Nothing in `products`, `orders`, `coupons` or `accounts` imports `wishlists`. The catalog templates include the wishlist button partial, but that's a template include, not a Python import.
- The one deliberate exception is the `seed` command. It already assembles the whole demo world across apps, and it will import `wishlists` the way it already imports `orders` and `coupons`.
- URLs live under the `wishlists` namespace.

**Models.**
- `Wishlist` has a one-to-one link to the user (reverse name `wishlist`, cascading on user deletion). It has **no name field**: a customer has exactly one wishlist, so its owner identifies it.
- The wishlist is created lazily the first time it's touched, through a `for_user` class method. This follows the cart's pattern.
- `WishlistItem` links a wishlist (reverse name `items`) to a product, records when it was added, and is ordered newest first.
- A database-level unique constraint on the (wishlist, product) pair means a product can appear at most once on a wishlist, even under concurrent requests.
- The product link cascades on delete: deleting a product removes it from every wishlist, the same way carts behave.
- The logic lives on the model, per the architecture convention: `add` is idempotent (adding twice leaves one row), and `remove` does nothing when the product isn't on the wishlist.
- No service module is needed, because no workflow crosses models in more than one app.

**Availability.**
- Add and remove look products up across the whole catalog, not only available products, so any product the public catalog shows can be saved. This is deliberately different from add-to-cart, which only accepts available products.
- Unavailable products stay on a wishlist and are shown with an "Unavailable" badge. The existing add-to-cart button already renders its disabled state for them.

**Endpoints.**
- There are three views, all class-based and all behind `LoginRequiredMixin`.
- **Wishlist page** (`GET`): the signed-in user's own wishlist. It takes no user id or wishlist id in the URL.
- **Add** (`POST`, keyed by product pk) and **Remove** (`POST`, keyed by product pk): two separate endpoints, not a toggle, so the button always does what its label says. Both are idempotent. They share a base view that resolves the product, acts on the requesting user's own wishlist, and renders the response.
- Every lookup goes through the requesting user. No view fetches a wishlist or wishlist item by bare id, so customers cannot reach each other's data.
- A product pk that doesn't exist returns 404.
- Anonymous requests to add or remove are redirected to login by the mixin and never create data. That redirect is a backstop only, because signed-out visitors are never shown an HTMX button.
- **Response from Add:** the button partial in its "Saved" state, plus the navbar badge as an out-of-band swap.
- **Response from Remove:** by default, the button partial in its "Save" state plus the badge. When the request comes from the wishlist page (flagged by a value the button sends), the response is instead the wishlist contents partial (the remaining items, or the empty state) plus the badge.

**State on page load.**
- A `wishlists` context processor supplies the signed-in user's set of wishlisted product ids, or an empty set for anonymous visitors, using one query per request.
- The catalog, detail and wishlist templates use this set to render each button's starting state.
- The navbar badge's count is the size of the same set, so it needs no extra query.
- This mirrors the existing cart-quantities context processor. It is registered in settings alongside it.

**Templates and HTMX.**
- Templates follow the project's template conventions: underscore-prefixed partials that never extend the base template, DaisyUI semantic classes only, and no JavaScript beyond HTMX.
- **Wishlist button partial:**
  - Signed in: a `<button>` that posts to Add or Remove depending on the current state and swaps itself out.
  - Not saved: "♡ Save", ghost style.
  - Saved: "♥ Saved", outline style, with the heart in a semantic colour.
  - It carries `aria-pressed` so assistive technology announces it as a toggle.
  - Signed out: a sign-in link styled as the button, with a `next` parameter pointing back to the current page.
  - It never uses `btn-primary`, because the page's single primary action stays add-to-cart.
- **Wishlist contents partial:** the list of rows, each with the product, an availability badge when needed, the existing add-to-cart partial and the wishlist button (configured to target the contents container), or a designed empty state when the list is empty.
- **Wishlist badge partial:** the navbar "♥ Wishlist" link with a count badge, shown only to signed-in users next to the cart badge. It can be included as an out-of-band swap from any wishlist response.
- **Wishlist page:** extends the base template and opens with the standard heading and one-line description.
- The button is included on catalog cards, the product detail page and wishlist rows.

**Account deletion.**
- `User.anonymize()` deletes the user's wishlist, if one exists, right after deleting the cart. Its items cascade with it.
- It reaches the wishlist through the reverse relation name, so `accounts` gains no import of `wishlists`.
- The method's docstring is updated to mention the wishlist.

**Admin.**
- `Wishlist` is registered in the Django admin with an inline for its items, matching the cart's admin. This is the superuser's existing all-access debugging tool.
- There is no back-office tab.

**Seed.**
- The seed command gives the demo customer a wishlist of three to four products, at least one of them unavailable.
- Wishlists are cleared during the wipe step so reseeding stays idempotent.

**Testing.**
- Testing follows the project's testing conventions: pytest with plain fixtures in the project-level conftest, no factory-boy, and a green suite at every phase boundary.
- A second customer fixture supports the privacy tests.
- Coverage:
  - **Model:** lazy one-per-user creation, idempotent add and remove, the database rejecting a duplicate (wishlist, product) row, and product deletion cascading.
  - **Views:** each response's partial, button state, `aria-pressed` value and out-of-band badge. The wishlist-page remove returns the contents partial, and the empty state after the last item goes. Unavailable products can be saved. Unknown pks return 404.
  - **Access control:** anonymous add and remove redirect and create nothing. The wishlist page shows only the requesting user's items. One customer's actions never touch another customer's rows.
  - **Integration:** the context processor returns an empty set for anonymous visitors and the correct set for signed-in users. Account anonymization deletes the wishlist. Seeding creates the demo wishlist.

## Out of Scope

- **Multiple or named wishlists.** Each customer has exactly one wishlist, and it has no name.
- **Sharing wishlists**, public wishlist links, or gift registries.
- **Staff or back-office visibility** of customers' wishlists, including a back-office tab.
- **Wishlist analytics** such as "most-wishlisted products" on the dashboard. This could be added later as an aggregate that doesn't identify customers.
- **"Move to cart"**, meaning adding to the cart and removing from the wishlist in one action. Adding to the cart from the wishlist leaves the item saved.
- **Saving while signed out** and merging a guest wishlist on sign-in. Signed-out visitors are sent to sign in, and the product is not saved automatically afterwards.
- **Notifications**, such as emailing a customer when a saved product becomes available again or goes on sale.
- **Keeping a placeholder for deleted products.** Deleted products simply disappear from wishlists.
- **Notes, quantities, priorities or manual reordering** of wishlist items.
- **Pagination** of the wishlist page.

## Further Notes

- The feature deliberately mirrors existing patterns so it reads like the rest of the codebase: the cart's lazy one-to-one model, its item model with a uniqueness rule, its HTMX swap-and-out-of-band-badge interactions, its context processor for page-load state, and the owner-scoped lookups used for orders and addresses.
- "Wishlists cannot have unique names" was settled as *wishlists have no name at all*, which satisfies the requirement because there is nothing that could be unique.
- Signed-out visitors never get an HTMX button, because HTMX following a login redirect would swap the whole sign-in page into the button's place.
- This session's design interview and PRD should be logged in the AI-usage log, appended per the project's convention.
