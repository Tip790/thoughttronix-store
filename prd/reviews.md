# PRD: The ThoughtTronix Store — Product Reviews

*A follow-on to the core platform, account security and wishlist PRDs.*

---

## Problem Statement

A ThoughtTronix shopper deciding whether to buy a product has only the store's own word to go on: its name, tagline, description and price. There is no way to hear from people who have actually bought it.

Customers who have bought something also have nowhere to say what they thought of it. They can't warn other shoppers about a disappointment or recommend something they love.

When reviews do exist, shoppers need to trust them. A review from someone who never bought the product, or one customer posting many reviews of the same product, would make every rating meaningless. Customers also expect to stay in control of what they've written: they want to fix a typo, change their mind about a rating, or take a review down, and nobody else should be able to change their words.

Finally, reading and writing reviews must not interrupt shopping. Writing, editing or deleting a review shouldn't reload the page, jump the customer back to the top, or lose their place in the list.

## Solution

Every product's detail page gains a **Reviews** section.

- **A summary line** at the top of the section shows the average rating and the number of reviews, for example "★ 4.3 · 12 reviews", or a designed "No reviews yet" empty state.
- **Only buyers can review.** A customer can review a product when they have at least one order containing it that hasn't been cancelled. Eligibility is checked when the review is written. If the order is cancelled later, the review stays and its author can still edit or delete it.
- **One review per customer per product.** A review is a star rating from 1 to 5 plus a written comment of 10 to 2,000 characters.
- **The section explains itself to every visitor:**
  - Signed-out visitors see a "Sign in to review" link that brings them back to the same product page.
  - Signed-in customers who haven't bought the product see a short note: only customers who've bought it can review it.
  - Buyers who haven't reviewed it yet see the review form.
  - Customers who have reviewed it see their own review, with Edit and Delete buttons.
- **Your own review has a fixed spot.** It (or the form) sits at the top of the section, in a slot that never moves. Everyone else's reviews follow, newest first.
- **Everything happens in place, without a page reload.**
  - Submitting the form turns it into your review card.
  - **Edit** turns your card into a pre-filled form in the same spot. **Save** turns it back into the updated card, and **Cancel** restores the card unchanged.
  - **Delete** asks for confirmation inside the card ("Delete this review? Yes, delete / Keep it"). Once deleted, the empty form appears in its place.
  - The summary line updates after every change.
  - Invalid submissions show their errors inside the form and keep everything the customer typed.
- **Reviews show who wrote them, privately.** Each review shows the reviewer as first name and last initial (for example "Mira K."), or their username if they haven't set a name. It also shows a "Verified purchase" badge, the date, and an "edited" marker if the review was changed after posting.
- **Long lists load in steps.** The first 10 of other customers' reviews show up front, and a "Show more reviews" button appends the next 10 below without moving anything above it.
- **Deleting an account deletes the customer's reviews**, along with the rest of their personal data.
- **The superuser can remove abusive reviews** in the Django admin. Customers can only ever edit or delete their own.
- **The demo world shows every state.** After seeding:
  - The demo customer has one product they've reviewed, one they've bought but not reviewed, and plenty they've never bought.
  - One product has more than 10 reviews with mixed ratings, so "Show more" appears.

## User Stories

1. As a shopper, I want to read reviews on a product's detail page, so that I can learn what buyers think before I buy.
2. As a shopper, I want to see a product's average rating and review count at a glance, so that I can judge it quickly.
3. As a shopper, I want a clear "No reviews yet" message on products without reviews, so that I know the section works and is simply empty.
4. As a shopper, I want reviews to come only from people who bought the product, so that I can trust them.
5. As a shopper, I want each review marked as a verified purchase, so that I know the reviewer actually bought the product.
6. As a shopper, I want to see each reviewer's first name and last initial, so that reviews feel personal without exposing anyone's full name or login.
7. As a shopper, I want other customers' reviews listed newest first, so that I see current opinions first.
8. As a shopper, I want to see when a review was posted and whether it was edited, so that I can judge how current it is.
9. As a shopper, I want to load more reviews without leaving my place on the page, so that I can keep reading where I was.
10. As a shopper, I want the "Show more reviews" button to disappear when there are no more reviews, so that I know I've seen them all.
11. As a signed-out visitor, I want a "Sign in to review" link that brings me back to the same product page, so that I can review without hunting for the product again.
12. As a customer who hasn't bought a product, I want to be told that only buyers can review it, so that I understand why there's no review form.
13. As a customer who bought a product, I want a review form on its page, so that I can share my opinion.
14. As a customer whose order hasn't shipped yet, I want to be able to review straight away, so that I don't have to wait for delivery.
15. As a customer, I want to rate a product from 1 to 5 whole stars, so that my rating is quick to give and easy to compare.
16. As a customer, I want to write a comment with my rating, so that I can explain my score.
17. As a customer, I want my review rejected with a clear message if my comment is too short or too long, so that I know exactly what to fix.
18. As a customer, I want to keep what I typed when my review has an error, so that I don't have to start over.
19. As a customer, I want my review to appear the moment I submit it, without a page reload, so that I don't lose my place.
20. As a customer, I want only one review per product, so that my opinion counts once and I always know which review is mine.
21. As a customer, I want my own review shown at the top of the reviews section, so that I can find it straight away.
22. As a customer, I want to edit my review in place, so that I can fix a mistake or update my opinion without leaving the page.
23. As a customer, I want to cancel an edit and get my original review back, so that changes I started don't stick by accident.
24. As a customer, I want my review to stay in the same spot while I edit it, so that I never lose track of it.
25. As a customer, I want to be asked to confirm before my review is deleted, so that one misclick doesn't destroy it.
26. As a customer, I want the review form to reappear after I delete my review, so that I can write a new one if I change my mind.
27. As a customer, I want the average rating and count to update the moment I add, edit or delete a review, so that the summary is always accurate.
28. As a customer, I want only myself able to edit or delete my reviews, so that nobody can change my words.
29. As a customer whose order was later cancelled, I want to keep control of the review I already wrote, so that I can still edit or delete it.
30. As a customer, I want to review products that are currently unavailable if I bought them, so that my opinion still counts.
31. As a customer, I want a double-click or a stale browser tab never to create a second review or show an error page, so that the section always shows my real state.
32. As a customer, I want my reviews deleted when I delete my account, so that none of my words stay behind after I leave.
33. As a staff member, I want to review products I've bought like any customer, so that I can shop the store the same way customers do.
34. As the administrator, I want to find and delete reviews in the Django admin, filtered by product and rating, so that I can remove abusive content.
35. As a screen-reader or keyboard user, I want the star rating to be a set of labelled radio buttons, so that I can choose a rating without a mouse.
36. As a developer or grader, I want the seeded demo world to show every review state, so that the whole feature is visible straight after seeding.
37. As a developer, I want deleting a product to delete its reviews, so that reviews never point at products that no longer exist.

## Implementation Decisions

**A new `reviews` app.**
- Its Python code depends on `products`, `orders` and `accounts`. Nothing in `products`, `orders`, `coupons`, `wishlists` or `accounts` imports `reviews`.
- The product detail template includes the reviews section partial. That's a template include, not a Python import. The product detail view doesn't change: the section loads its own data (see **Endpoints**).
- The one deliberate exception is the `seed` command, which already assembles the demo world across apps and will import `reviews` the way it imports `wishlists`.
- URLs live under the `reviews` namespace.

**Model.**
- `Review` links a user (reverse name `reviews`) to a product (reverse name `reviews`). It holds a `rating`, a `comment`, `created_at` and `updated_at`.
- Both foreign keys cascade on delete. Deleting a product deletes its reviews, the same way carts and wishlists behave. Users are almost never truly deleted (see **Account deletion**).
- `rating` is a small positive integer from 1 to 5. Model validators enforce the range, and a database check constraint backs them up.
- `comment` is a text field.
- A database-level unique constraint on the (user, product) pair means one review per customer per product, even under concurrent requests.
- `created_at` uses a default rather than auto-now-add, so the seed can backdate reviews, matching orders. `updated_at` is set on every save. A review counts as "edited" when `updated_at` is meaningfully later than `created_at`.
- Default ordering is newest first by `created_at`, so editing never reorders anything.
- The reviewer's display name (first name and last initial, falling back to the username) is a method on the model, per the architecture convention.

**Eligibility.**
- A single check decides whether a user may create a review for a product. It's true when the user has an order line for that product on an order whose status isn't `CANCELLED`. This matches how the dashboard and coupons already define a sale.
- It's checked only when a review is created. Editing and deleting are gated only on authorship, so a later cancellation never locks an author out of their own review.
- It lives with the model (a class method or queryset method), not a service module: it's a read-only query, not a cross-model workflow.
- Order lines keep their product link while the product exists, so the check queries order lines by product.
- Unavailable products can be reviewed by their buyers.

**Aggregates.**
- A queryset method returns a product's average rating and review count in one query. The summary line uses it. A future catalog-card star display could reuse it.

**Form.**
- A model form for rating and comment owns all validation, per the convention.
- The comment is trimmed. Blank, whitespace-only, or shorter than 10 characters is rejected, and so is longer than 2,000. The textarea carries `maxlength` so the browser stops typing at the limit.
- The rating is required and rendered as DaisyUI `rating` radio inputs. Each star is a real, labelled radio button.

**Endpoints.**
- Every endpoint is a class-based view. Every mutation, and every view that returns a form or the author's own card, sits behind `LoginRequiredMixin`.
- Every lookup of the author's review goes through the requesting user. No view fetches a review by bare id, so customers can never reach each other's reviews.
- Products are looked up by pk, as the wishlist endpoints do, across the whole catalog. An unknown pk returns 404.
- **Reviews section** (GET, keyed by product): renders the whole section, meaning the summary, the visitor's own slot in whichever of the four states applies, and the first page of other customers' reviews. It's the single source for the section's content, used both for the initial page render and after changes.
- **Create** (POST, keyed by product): runs the eligibility check and validates the form. On success, it returns the author's card plus an out-of-band summary update. On invalid input, it returns the form with errors and the submitted values. If the user isn't eligible, it returns the "only buyers" note. If a review already exists (a double submit or a stale tab), it creates nothing and returns the existing card.
- **Edit form** (GET, keyed by product): returns the requesting user's review as a pre-filled form.
- **Update** (POST, keyed by product): validates and saves the requesting user's own review. It returns the card plus the summary out of band, or the form with errors.
- **Card** (GET, keyed by product): returns the requesting user's own card. This powers Cancel on both the edit form and the delete confirmation.
- **Delete confirmation** (GET, keyed by product): returns the card in its "Delete this review?" state.
- **Delete** (POST, keyed by product): deletes the requesting user's own review. It returns the empty form, since an author is necessarily a buyer, plus the summary out of band.
- **Stale states:** acting on a review that no longer exists, for example a delete or edit from a stale tab, returns the user's current state for their slot (the form or the note) rather than an error.
- **More reviews** (GET, keyed by product and page): returns the next 10 of other customers' reviews, plus a new "Show more" button if more remain. It's public, with no login required. Pagination uses Django's paginator. The requesting user's own review is always excluded from this list, because it lives in its own slot.
- Anonymous requests to any login-required endpoint are redirected to login by the mixin and never create data. That's a backstop only: signed-out visitors are never shown an HTMX control.

**Templates and HTMX.**
- Templates follow the project's template conventions: underscore-prefixed partials that never extend the base template, DaisyUI semantic classes only, and no JavaScript beyond HTMX.
- **The author's slot** is one stable element with a fixed id at the top of the section. Every write, edit, cancel, delete and confirm swaps only that element. The summary line updates out of band. Nothing else on the page re-renders, so the scroll position and the place in the list are preserved.
- **Partials:**
  - the reviews section
  - the summary line (also usable as an out-of-band swap), with the empty state when there are no reviews
  - the author's slot in its states: form, card, confirm-delete, sign-in link, and only-buyers note
  - a single review card used for everyone's reviews
  - the "more reviews" batch with its trailing button
- The sign-in link carries a `next` parameter pointing back to the current product page, matching the wishlist's signed-out button.
- **Buttons:** the detail page's single `btn-primary` stays add-to-cart. Review controls use ghost or outline styles. Destructive confirmation uses DaisyUI semantic error styling.
- **Show more** appends the next batch below the existing reviews and replaces only itself, so nothing above it moves.

**Account deletion.**
- `User.anonymize()` deletes all of the user's reviews alongside the addresses, cart and wishlist.
- It reaches them through the reverse relation name, so `accounts` gains no import of `reviews`.
- Every reviewer has ordered, so anonymization (not a real delete) is how a reviewer's account is always removed. The cascade alone would never fire. The method's docstring is updated to mention reviews.

**Admin.**
- `Review` is registered in the Django admin, with a list showing product, reviewer, rating and dates, filters by product and rating, and search over the comment.
- This is the only moderation tool. There's no back-office tab.

**Seed.**
- The demo customer gets one product they've ordered and reviewed, at least one product they've ordered but not reviewed, and many products they've never ordered.
- One product gets more than 10 reviews from seeded customers, with mixed ratings, so "Show more" and a realistic average both appear.
- Every seeded review is backed by a non-cancelled order for that reviewer and product, so the demo world never breaks the eligibility rule.
- Reviews use the seed's fixed random source, so results are deterministic.
- Reviews are cleared during the wipe step, so reseeding stays idempotent.

**Testing.**
- Testing follows the project's testing conventions: pytest with plain fixtures in the project-level conftest, no factory-boy, and a green suite at every phase boundary.
- Fixtures cover a customer with a non-cancelled order for a product, a customer whose only order for it is cancelled, a customer with no order, and a second customer for privacy tests.
- Coverage:
  - **Model:** the database rejects a second (user, product) review and an out-of-range rating. Product deletion cascades. The display-name rule and its fallback work. The aggregate returns the correct average and count, including for no reviews. The "edited" rule works.
  - **Eligibility:** PLACED, SHIPPED and DELIVERED orders qualify, and CANCELLED and no order don't. Unavailable products qualify.
  - **Form:** the comment's trimming, both length limits, and the rating's range.
  - **Views:** each endpoint's partial and out-of-band summary. The four visitor states render correctly. Invalid input keeps the submitted values. Double create returns the existing card and creates nothing. The stale delete and edit fallbacks work. Unknown pks return 404. Pagination returns 10 at a time, drops the button on the last page, and excludes the viewer's own review.
  - **Access control:** anonymous mutations redirect and create nothing. A non-buyer's create creates nothing. One customer can never edit or delete another's review. An author whose order was cancelled after reviewing can still edit and delete.
  - **Integration:** anonymization deletes the user's reviews. Seeding produces the agreed demo states and keeps every review backed by a qualifying order.

## Out of Scope

- **Star ratings on catalog cards** or anywhere outside the product detail page. The aggregate is built so this can follow later.
- **A "My reviews" page** on the customer's account.
- **A back-office Reviews tab** or moderation by ordinary staff. Moderation is the superuser in the Django admin only.
- **Review titles, photos, pros and cons lists**, or any field beyond the rating and comment.
- **Half stars** or any rating scale other than whole stars from 1 to 5.
- **Re-checking eligibility after creation:** hiding or locking reviews when an order is later cancelled.
- **Requiring delivery** before a customer can review.
- **Helpful votes, replies, reporting or flagging** of reviews.
- **Sorting or filtering reviews** by rating, or any order other than newest first.
- **Keeping reviews after account deletion** or showing them under a "former customer" name.
- **Notifications**, such as emailing a customer to review a delivered order, or telling staff about new reviews.
- **Review analytics** on the staff dashboard.
- **Numbered pagination** of reviews. Only "Show more" is provided.

## Further Notes

- The feature deliberately mirrors existing patterns so it reads like the rest of the codebase: the wishlist's owner-scoped lookups, its HTMX partials with out-of-band swaps, its signed-out sign-in link with `next`, and its handling in `anonymize()` through a reverse relation. It also uses the dashboard's and coupons' shared meaning of "sold": any order that isn't cancelled.
- The "without reloading the page or losing the customer's place" requirement drives three choices: the author's review has its own fixed slot so it never moves, edit and delete confirmation happen inside that slot, and long lists grow with "Show more" instead of paging.
- Hiding the review form from people who can't use it is a courtesy, not the security. The server re-checks eligibility and ownership on every request.
- Signed-out visitors are never given an HTMX control, because HTMX following a login redirect would swap the whole sign-in page into the section.
- This session's design interview and PRD should be logged in the AI-usage log, appended per the project's convention.
