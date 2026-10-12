# Plan: The ThoughtTronix Store — Account Security

> Source PRD: `prd/account-security.md` (amends `prd/core-platform.md` on accounts)

*The PRD owns the requirements; this plan owns the sequence. Where a phase says "per the PRD," the PRD's wording is authoritative. The suite must be green at every phase boundary.*

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: `accounts` owns the whole feature: forms, views, the verification token, the cache-based throttle, the plain-text email templates (kept with the other accounts templates), and `User.anonymize()`. The only change outside `accounts` is `Order.user` in `orders`, plus the staff order screens' display of a deleted customer. No new dependencies and no third-party auth packages.
- **Identity**: sign-in stays username-only. Email is used for recovery and notices only.
- **Models**:
  - `accounts.User` gains `email_verified` (boolean, default false).
  - Emails are normalized to lowercase on save. A database `UniqueConstraint` on the lowercased email backs up the forms' friendly errors.
  - `accounts.User` gains `anonymize()`. This is a model method, not a third deep module.
  - `Order.user` changes from `CASCADE` to `PROTECT`.
- **URLs**: all routes sit under `/accounts/` in the `accounts` namespace. Each is named:
  - the Account page
  - email verification (the link target) and resend verification
  - password change and its done page
  - password reset request, done, confirm and complete
  - email change
  - account deletion

  Every state-changing action is a POST.
- **Authorization**: the Account page and its actions require sign-in. Account deletion refuses `is_staff` and `is_superuser`, even when the URL is posted directly.
- **Tokens**: verification links are signed and time-limited, with the same lifetime as `PASSWORD_RESET_TIMEOUT` (3 days). A link is only valid for the email it was sent to. Password reset uses Django's built-in views and token generator, subclassed within `accounts`.
- **Email**: the backend and SMTP details come from `.env` via environs. The default is the console backend, and `DEFAULT_FROM_EMAIL` has a working default. Emails are plain text, rendered from templates. Tests use Django's in-memory mailbox.
- **Settings**: throttle limits and windows, and the production security flags, are all settings with working defaults. The app still runs with no `.env`.

---

## Phase 1: Sign-up takes an email, then signs you in

**User stories**: 1, 2, 3, 4, 5, 12

### What to build

The sign-up form asks for a username, an email and a password. The email is required and is lowercased whenever a user is saved. A database constraint on the lowercased email guarantees uniqueness however a user is created. The form checks for a taken email first (ignoring case) and shows a friendly "already in use" error. Passwords still go through the existing validators. A successful sign-up signs the new customer in and redirects to the catalog. The sign-up view's docstring is updated, since auto-login is now done. Sign-in for existing accounts is unchanged.

### Acceptance criteria

- [ ] Sign-up without an email is rejected. An email that differs from an existing one only in capitalization is rejected with a friendly error.
- [ ] Saving a user with a mixed-case email stores it lowercase. Creating a duplicate outside the form (in the shell or admin) fails at the database.
- [ ] The migration applies cleanly to the committed database.
- [ ] After sign-up the user is authenticated and lands on the catalog.
- [ ] Existing users sign in with their username and password exactly as before.

---

## Phase 2: Email confirmation and the Account page

**User stories**: 6, 7, 8, 9, 10, 11, 24, 39, 40, 41

### What to build

This phase adds the `email_verified` field, and the email backend and from-address settings (read from `.env`, console by default). Sign-up now sends a verification email and shows a message saying a confirmation link was sent. The link verifies the account if it is unexpired and the account's email still matches the one it was sent to. A new Account page, linked from the navbar next to Addresses for signed-in users, shows the email and whether it is confirmed. When it isn't, a POST button resends the link. Verification never blocks sign-in, the cart or checkout. The seed command marks every seeded user as verified.

### Acceptance criteria

- [ ] Sign-up sends exactly one verification email to the new address, and the success message mentions it.
- [ ] A valid link marks the email verified. Expired, tampered or stale-email links (where the email changed after sending) do not.
- [ ] An unverified customer can add to cart and check out.
- [ ] The Account page shows the confirmation status. The resend button appears only when the email is unconfirmed, and posting to it sends a fresh link.
- [ ] Signed-in users see the Account link in the navbar.
- [ ] With no `.env`, emails print to the console. SMTP settings and the from-address can be set from `.env`.
- [ ] After `seed`, every demo user has `email_verified` set to true.

---

## Phase 3: Forgot password

**User stories**: 17, 18, 19, 20, 21, 23, 28 (the reset half)

### What to build

Django's password reset flow, subclassed within the `accounts` namespace and styled with DaisyUI, linked from the sign-in page. The request page always shows the same confirmation, plus a tip to check the spam folder and the email used, whether or not the email matches an account. Reset emails go to accounts with a usable password, whether or not the email is verified. The link works once and expires after Django's reset timeout. A successful reset marks the email verified, sends a "your password was changed" notice, and redirects to sign-in. There is no auto-login.

### Acceptance criteria

- [ ] A known email and an unknown email produce identical responses. Only the known one sends mail.
- [ ] A used link or an expired link is refused.
- [ ] Completing a reset on an unverified account sets `email_verified` to true.
- [ ] Completing a reset sends the "password changed" notice and redirects to the sign-in page. The user is not signed in.
- [ ] The seeded `customer` can reset their password right after `seed`.

---

## Phase 4: Change password and change email

**User stories**: 25, 26, 27, 28, 29, 30, 31, 36 (password and email change)

### What to build

Both are linked from the Account page.

- **Password change** uses Django's built-in view and form: the current password is required and the new one goes through the validators. Other sessions are invalidated, the current session is kept, and a "password changed" notice is emailed.
- **Email change** is a form that takes a new email plus the current password. The form owns validation: correct password, valid email, and not used by another account (ignoring case). On success the email is updated and marked unverified, a verification link goes to the new address, and a "your email was changed" notice goes to the old address.

Both work the same for customers and staff.

### Acceptance criteria

- [ ] Changing the password keeps the current client signed in, signs out a second client session, and sends a notice.
- [ ] A wrong current password is rejected on both forms.
- [ ] Email change rejects an email already used by another account, in any capitalization.
- [ ] A successful email change sets `email_verified` to false and sends exactly two emails: a verification link to the new address and a notice to the old one.
- [ ] Verification links sent to the old address stop working after the change.
- [ ] Staff users can use both forms.

---

## Phase 5: Sign-in hardening — Remember me and throttling

**User stories**: 13, 14, 15, 16, 22, 36 (Remember me and throttling), 44

### What to build

**Remember me.** The sign-in form gains a "Remember me" checkbox, unchecked by default. Unchecked, the session expires when the browser closes; checked, it uses the standard two-week age. Auto-login after sign-up uses the browser-session behavior.

**Throttle.** A small cache-based throttle in `accounts`, with limits and windows held in settings:

- Sign-in failures are counted per username and per IP. After 5 failures in 15 minutes from either, sign-in is refused with a clear "too many attempts — try again later" message until the window passes. A successful sign-in does not reset the IP counter.
- Reset and verification emails are limited to 3 per address per hour.
- An over-limit reset request still shows the neutral confirmation, but no email is sent.

### Acceptance criteria

- [ ] Signing in without "Remember me" gives a session that expires when the browser closes. Signing in with it gives the two-week session age.
- [ ] A user signed in automatically after sign-up gets a browser-session cookie.
- [ ] The 6th attempt after 5 failures for one username is refused, even with the correct password, and shows the throttle message. The same holds for 5 failures from one IP across different usernames.
- [ ] A successful sign-in does not clear the IP counter.
- [ ] A 4th reset or verification request to one address within the hour sends no email. The reset page's response is unchanged.
- [ ] Tests can tune the limits through settings and clear the cache between tests.

---

## Phase 6: Account deletion

**User stories**: 32, 33, 34, 35, 37, 38

### What to build

- **Protecting orders.** `Order.user` becomes `PROTECT`, so deleting a user who has orders is refused everywhere, including the Django admin.
- **`User.anonymize()`.** In a single transaction, it:
  - replaces the username with a placeholder such as `deleted-user-<pk>`;
  - clears email, names and job title, and sets `email_verified` to false;
  - sets an unusable password and deactivates the account;
  - deletes the user's saved addresses and cart;
  - blanks the email and the shipping and billing name and address fields on all of their orders.

  Order totals, items, statuses, coupons, dates and card last-four are untouched.
- **The delete view.** Customers can delete their account from the Account page after re-entering their password. They are then signed out and shown a confirmation message.
- **Staff.** Staff and superusers see a note on the Account page asking them to contact an administrator, and the view refuses them even when the URL is posted directly.
- **Staff order screens.** These show anonymized customers as a deleted customer.

### Acceptance criteria

- [ ] Deleting a user with orders raises `ProtectedError`. A user without orders can still be deleted.
- [ ] After `anonymize()`, nothing personal is left on the user, their addresses, their cart or their orders.
- [ ] Order totals and dashboard revenue figures are unchanged after anonymizing.
- [ ] A wrong password does not delete the account. A correct one signs the user out with a confirmation message, and the old credentials no longer sign in.
- [ ] Staff and superusers get no delete button, and posting to the delete URL is refused.
- [ ] Anonymized customers' orders still appear in the staff order list and detail pages, labelled as a deleted customer.

---

## Phase 7: Production hardening

**User stories**: 42, 43

### What to build

When `DEBUG` is off, secure session cookies, secure CSRF cookies, the HTTPS redirect and short-lived HSTS (around an hour) all default to on. Each can be overridden from `.env`. With `DEBUG` on, behavior is unchanged. Settings comments say that running with debug off on a laptop without HTTPS also needs the redirect turned off.

### Acceptance criteria

- [ ] With `DEBUG` on, none of the production flags are set.
- [ ] With `DEBUG` off, all four default to on and HSTS has a short lifetime.
- [ ] Each flag can be overridden from the environment.
- [ ] `manage.py check --deploy` reports no security warnings for these settings when `DEBUG` is off and a real `SECRET_KEY` is set.
