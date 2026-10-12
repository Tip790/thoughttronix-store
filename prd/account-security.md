# PRD: The ThoughtTronix Store — Account Security

*A follow-on to the core platform PRD. Where the two disagree on accounts, this one wins.*

---

## Problem Statement

A ThoughtTronix customer account today is a username and a password, and nothing more. That leaves customers exposed in ways they would not tolerate from any other store:

- **A forgotten password is a dead account.** There is no email on file to send a reset link to, and no reset flow to send one with. The customer must make a new account and lose their order history and saved addresses.
- **A password can never be changed.** A customer who suspects their password has leaked has no way to replace it.
- **Nothing slows down a password guesser.** A script can try thousands of passwords against the sign-in page, and seeded demo passwords like `customer123` would fall quickly.
- **Sign-ins last two weeks, everywhere.** Signing in on a library computer leaves that computer signed in for a fortnight.
- **There is no way to leave.** A customer who wants their personal data gone has no way to delete their account, and if staff deleted the user in the admin, every order that customer ever placed would be deleted with it, silently rewriting the store's revenue history.
- **Production would leak secrets in transit.** Session cookies and (future) reset links would travel over plain HTTP if the app were deployed as configured.

## Solution

Customers give an email address when they sign up, and that email becomes the backbone of account recovery and security notices:

- **Sign-up** asks for a username, an email, and a password. The email must not already belong to another account (ignoring capitalization). The new customer is signed in straight away and sent a link to confirm their email. Verification never blocks shopping.
- **Forgot password** sends a single-use reset link to the account's email. The page never reveals whether an email has an account. Using the link also confirms the email.
- **An Account page** lets a signed-in user see their email and whether it is confirmed, resend the confirmation link, change their password, change their email (after re-entering their password), and, for customers, delete their account.
- **Security notices** go out by email whenever a password is changed or reset, and to the *old* address whenever the email is changed, so a real owner learns about an intruder quickly.
- **Sign-in is throttled.** Repeated failures for one username or one IP address are refused for a while, and reset or confirmation emails to one address are rate-limited so nobody's inbox can be flooded.
- **"Remember me"** decides whether a sign-in survives closing the browser.
- **Deleting an account** removes the person but not the business record: the account is scrubbed and deactivated, saved addresses and the cart are deleted, and past orders are kept for the store's books with every personal detail blanked out.
- **Production hardening** switches on automatically when debug mode is off: secure cookies, HTTPS redirect, and a short HSTS policy.

Locally, nothing needs configuring. Emails are printed to the terminal running the dev server, links included, so every flow can be demonstrated with the seeded `@example.com` accounts.

## User Stories

**Visitor (signing up)**

1. As a visitor, I want to give my email address when I create an account, so that I can recover my account if I forget my password.
2. As a visitor, I want to be told if the email I entered is already in use, so that I know to sign in or reset my password instead of making a second account.
3. As a visitor, I want `Casey@Example.com` and `casey@example.com` to count as the same email, so that capitalization never creates a duplicate account.
4. As a visitor, I want my password checked against the store's password rules when I sign up, so that I don't pick one that is trivially guessable.
5. As a new customer, I want to be signed in automatically right after signing up, so that I can go straight to shopping without typing my password again.
6. As a new customer, I want to be told that a confirmation link has been sent to my email, so that I know to look for it.

**Customer (email verification)**

7. As a customer, I want to confirm my email by clicking a link, so that the store knows the address really belongs to me.
8. As a customer, I want to keep shopping before I have confirmed my email, so that verification never stands between me and checkout.
9. As a customer, I want to see on my Account page whether my email is confirmed, so that I know whether I still need to click the link.
10. As a customer, I want to request a fresh confirmation link, so that I can still confirm my email if the first link expired or got lost.
11. As a customer, I want confirmation links to expire after a few days, so that an old email in my inbox can't be used against me forever.

**Customer (signing in)**

12. As a customer, I want to sign in with my username and password, as I always have, so that nothing about signing in changes for existing accounts.
13. As a customer, I want a "Remember me" checkbox on the sign-in form, so that I choose whether to stay signed in after I close the browser.
14. As a customer on a shared computer, I want my session to end when I close the browser unless I ticked "Remember me", so that the next person can't use my account.
15. As a customer, I want sign-in attempts against my username to be refused after several wrong passwords in a short time, so that nobody can guess my password by brute force.
16. As a customer, I want a clear "too many attempts — try again later" message when sign-in is throttled, so that I understand why my correct password isn't working yet.

**Customer (forgotten password)**

17. As a customer who forgot my password, I want to request a reset link by entering my email, so that I can get back into my account.
18. As a customer, I want the reset page to show the same message whether or not my email has an account, so that strangers can't use it to find out who shops here.
19. As a customer who didn't receive a reset email, I want a hint to check my spam folder and make sure I used the email on my account, so that I can fix a typo or find the message.
20. As a customer, I want the reset link to work only once and only for a few days, so that a leaked link stops being dangerous.
21. As a customer who never confirmed my email, I want password reset to still work, and to count as confirming my email, so that skipping the confirmation step never locks me out.
22. As a customer, I want reset requests for my email to be rate-limited, so that nobody can flood my inbox with reset emails.
23. As a customer who just reset my password, I want to be sent to the sign-in page to sign in with my new password, so that I confirm it works.

**Customer (Account page)**

24. As a signed-in user, I want an Account link in the navigation bar, so that I can find my security settings easily.
25. As a signed-in user, I want to change my password by entering my current password and a new one, so that I can replace a password I think has leaked.
26. As a signed-in user who changed my password, I want every other device signed in as me to be signed out, so that anyone using my old password loses access.
27. As a signed-in user who changed my password, I want to stay signed in on the device I'm using, so that I don't have to sign in again right away.
28. As a customer, I want an email notice whenever my password is changed or reset, with a pointer to reset it if it wasn't me, so that I find out quickly if someone else got in.
29. As a customer, I want to change my email address after re-entering my current password, so that I can fix a typo or move to a new address, but someone who borrowed my session can't.
30. As a customer, I want my new email to need confirming, so that the store only trusts addresses I've proven I own.
31. As a customer, I want my old email address to receive a notice when my email is changed, so that I can react if someone hijacked my account.

**Customer (deleting an account)**

32. As a customer, I want to delete my account after re-entering my password, so that my personal data is removed from the store when I no longer want to be a customer.
33. As a customer who deleted my account, I want my name, email, saved addresses, and cart removed, and the name, email, and addresses on my past orders blanked out, so that nothing identifying me is left behind.
34. As a customer who deleted my account, I want to be signed out and told my account is gone, so that I know the deletion worked.

**Employee and admin**

35. As an employee, I want the Account page to tell me to ask an administrator to close my account instead of offering a delete button, so that staff departures are handled by an admin and nobody can lock the team out of the back office.
36. As an employee, I want the same password change, email change, Remember me, and throttling protections as customers, so that my more powerful account is at least as well protected.
37. As an admin, I want a deleted customer's orders to stay in the order list and the dashboard's revenue figures, shown as a deleted customer, so that the store's sales history stays accurate.
38. As an admin, I want it to be impossible to delete a user who has orders, even from the Django admin, so that nobody can wipe sales history by accident.

**Developer and operator**

39. As a developer, I want the app to keep printing emails to the terminal when no email settings are configured, so that every flow works on a laptop with no `.env`.
40. As an operator, I want to send real email by filling in SMTP settings and a from-address in `.env`, so that the same code works in production with no code changes.
41. As a developer, I want the seeded demo users to have confirmed emails, so that password reset works for them right after `seed` with no extra steps.
42. As an operator, I want secure cookies, an HTTPS redirect, and HSTS to switch on automatically when debug mode is off, so that a deployment is safe by default and `check --deploy` passes.
43. As an operator, I want to override each of those production settings from `.env`, so that I can run with debug off on a machine without HTTPS when I need to.
44. As a developer, I want the throttle limits to live in settings, so that tests and deployments can tune them.

## Implementation Decisions

**Identity and the email field**

- Sign-in stays username-based, exactly as in the core platform. Email is an identifier for recovery and notices, not for signing in.
- Email becomes required on sign-up. It is stored lowercase (normalized when saved), and a database constraint on the lowercased email guarantees uniqueness however a user is created: sign-up form, Django admin, seed command, or shell.
- The sign-up form checks for a taken email first and shows a friendly error, so the database constraint is a backstop rather than the user-facing message. Sign-up therefore does reveal that an email is registered; this is an accepted, documented trade-off (see Further Notes).
- All 12 users in the committed database already have distinct, non-empty emails, so the constraint's migration applies cleanly.

**User model changes**

- `accounts.User` gains an `email_verified` boolean, defaulting to false.
- `accounts.User` gains an `anonymize()` model method that performs account deletion (see below). Deletion logic lives on the model, per the project's "logic lives in models" convention. It is not a third deep module.
- `Order.user` changes from `CASCADE` to `PROTECT`. Deleting a user who has orders is refused everywhere; anonymizing is the only supported way to remove a customer.

**Email delivery**

- The email backend and SMTP connection details are read from `.env` via environs, defaulting to the console backend. A `DEFAULT_FROM_EMAIL` setting is added with a working default.
- All account emails are plain text, rendered from Django templates kept with the other accounts templates.
- Tests rely on Django's in-memory test mailbox; no test needs mail configuration.

**Email verification**

- Sending a verification email: on sign-up, on email change, and on request from the Account page.
- Verification links are signed, time-limited tokens. Their lifetime matches Django's password reset timeout (3 days). A link verifies only if the account's email is still the one the link was sent for.
- Verification never blocks sign-in, the cart, or checkout. It only drives the "confirmed / not confirmed" status on the Account page and the resend button.
- Completing a password reset sets `email_verified` to true, since clicking a reset link proves control of that inbox.

**Password reset**

- Uses Django's built-in password reset views and token generator, subclassed within the `accounts` namespace and styled with DaisyUI.
- The request page always shows the same confirmation, whether or not the email matches an account, followed by a tip to check spam and confirm the email used.
- Reset emails go to the account's email whether or not it is verified (only to accounts with a usable password, matching Django's default).
- After a successful reset: mark the email verified, send the "password changed" notice, and redirect to sign-in. Auto-login after reset stays off.

**Password change**

- Uses Django's built-in password change view and form (current password required, new password run through the existing validators). Other sessions are invalidated by Django's session auth hash; the current session is kept.
- A "your password was changed" notice is emailed after every change or reset.

**Email change**

- A form on the Account page takes a new email plus the current password. The form owns validation: correct password, valid email, not already used by another account (case-insensitive).
- On success: the email is updated and marked unverified, a verification link goes to the new address, and a "your email was changed" notice goes to the old address.

**Throttling**

- A small cache-based throttle lives in `accounts`. No new dependency.
- Sign-in: failures are counted per username and per IP address. After 5 failures in 15 minutes from either, sign-in is refused with a "too many attempts" message until the window passes. A successful sign-in does not reset the IP counter.
- Emails: reset and verification requests are limited to 3 per email address per hour. When a reset request is over the limit, the page still shows the same neutral confirmation; no email is sent.
- Limits and windows are settings with working defaults. The default local-memory cache is enough for a single server; counters reset when the server restarts.

**Sessions**

- The sign-in form gains a "Remember me" checkbox, unchecked by default. Unchecked, the session expires when the browser closes; checked, it uses the standard two-week session age.
- New customers signed in automatically after sign-up get the unchecked (browser-session) behavior.

**Sign-up flow**

- After a successful sign-up, the user is signed in immediately and redirected to the catalog with a message saying a confirmation link was sent. This completes the "auto-login after signup" exercise noted in the existing sign-up view; that docstring is updated.

**Account page and URLs**

- A new Account page, linked from the navbar next to Addresses for signed-in users, shows the email and its verification status (with a resend button when unconfirmed) and links to change password, change email, and, for non-staff users, delete account.
- New named URLs in the `accounts` namespace cover: the Account page, email verification (link target) and resend, password change and its done page, password reset request / done / confirm / complete, email change, and account deletion.
- Every state-changing action is a POST.

**Account deletion**

- Available to non-staff users only. The view refuses staff and superusers even if the URL is posted directly; the Account page shows staff a note to ask an administrator. Admins handle staff departures by deactivating them in the Django admin.
- The user confirms by re-entering their current password.
- `anonymize()` runs in a single transaction and:
  - replaces the username with a non-identifying placeholder (for example, `deleted-user-<pk>`);
  - clears email, first name, last name, and job title; sets `email_verified` to false;
  - sets an unusable password and `is_active` to false;
  - deletes the user's saved addresses and cart;
  - blanks the email and the shipping and billing name and address fields on every one of the user's orders.
- Order totals, items, statuses, coupons, and dates are untouched, so the dashboard's figures don't change. Staff order screens show the customer as a deleted customer.
- After deletion, the user is signed out and shown a confirmation message.

**Production settings**

- When debug is off, these default to on: secure session and CSRF cookies, the HTTPS redirect, and HSTS with a short lifetime (on the order of an hour). Each one can be overridden from `.env`.
- With debug on (the local default), behavior is unchanged.

**Seed data**

- The seed command marks every seeded user's email as verified. Demo usernames, emails, and passwords are unchanged.

**Testing**

- Tests follow the project's testing guide. Coverage includes: case-insensitive email uniqueness at the form and database level; sign-up auto-login and verification email; verification token valid / expired / stale-email cases; reset showing the neutral message for unknown emails and marking verification on completion; password change keeping the current session and sending a notice; email change requiring the password and notifying both addresses; throttle limits for sign-in and emails; Remember me session expiry; `anonymize()` leaving no personal data on the user, addresses, cart, or orders while keeping order totals; staff being refused deletion; `Order.user` protection; and production settings switching with debug.

## Out of Scope

- Signing in with an email address, or with "username or email." Sign-in stays username-only.
- Hiding whether an email is registered at sign-up (for example, emailing the existing owner instead of showing "email taken").
- Blocking sign-in or checkout until the email is verified.
- Two-factor authentication.
- A sign-in history or "recent activity" list.
- Staff deleting their own accounts, or any "last superuser" logic.
- Shorter or role-specific session lifetimes for staff.
- Auto-login after a password reset.
- HTML email templates and email branding.
- A shared cache backend (such as Redis) for throttling across multiple servers, and an admin screen for clearing throttles.
- Third-party authentication packages (django-axes, django-allauth, django-otp).
- Restoring an anonymized account.

## Further Notes

- **This PRD amends the core platform PRD.** That PRD says sign-up has "no email — Django's stock signup fields." That line is superseded here; username-based sign-in is unchanged.
- **The sign-up leak is a known trade-off.** The reset page hides who has an account, but sign-up's "email already in use" error does not. Closing that gap would take the "email the existing owner instead" pattern, which was judged too complex for this phase. Most real stores make the same trade-off.
- **Why reset counts as verification.** A reset link is delivered to the same inbox a verification link would be, so clicking it proves the same thing. Without this, a customer who skipped verification and then forgot their password would be locked out for good.
- **Demo behavior.** With no `.env`, every email (verification, reset, notices) is printed to the terminal running the dev server. To demo a flow, copy the link from the terminal into the browser. The seeded `admin`, `employee`, and `customer` accounts can use password reset immediately.
- **Running with debug off locally.** Because the HTTPS redirect turns on when debug is off, a laptop without HTTPS must also turn the redirect off in `.env`.
- **Order card digits.** Anonymization blanks names, emails, and addresses on orders. The stored last four card digits are kept, since they don't identify a person on their own and staff may need them for disputes.
- **HSTS is kept short on purpose.** A long HSTS policy is hard to undo if HTTPS is ever misconfigured; it can be lengthened once a deployment is stable.
