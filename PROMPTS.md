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

## 2026-10-11 — Account security phase 5: Remember me and throttling

### Prompts

1. "@prd/account-security.md @plans/account-security.md Do Phase 5."
   (sent right after `/clear`, so the session started with no earlier
   context)
2. "How can I manually verify this phase in the browser?"
3. "Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways."

### Summary

- **Outcome:** the agent built phase 5 of `plans/account-security.md`.
  - **Remember me:** `SignInForm` gained an unchecked `remember_me`
    checkbox. `SignInView.form_valid` sets the session to end when the
    browser closes (`set_expiry(0)`), or to the standard two weeks when
    the box is ticked. `SignupView` also uses `set_expiry(0)` after its
    auto-login. `templates/accounts/login.html` renders the checkbox with
    the label beside it.
  - **Throttle:** a new `accounts/throttle.py` keeps counters in the
    default local-memory cache, each in a fixed window. There are four
    new settings in `config/settings.py`, each readable from `.env`:
    `SIGN_IN_THROTTLE_LIMIT`/`_WINDOW` (5 per 15 min) and
    `EMAIL_THROTTLE_LIMIT`/`_WINDOW` (3 per hour).
    - **Sign-in:** `SignInForm.clean` refuses sign-in before checking
      the password once a username or IP is over the limit. It counts
      only `invalid_login` failures. A success clears the username's
      count but not the IP's.
    - **Reset emails:** the cap is applied in
      `PasswordResetRequestForm.send_mail`, so the page doesn't change
      when nothing is sent.
    - **Confirmation emails:** the cap is applied in
      `send_verification_email`, which now returns whether it sent.
      `ResendVerificationView` shows a warning when over the limit, and
      `EmailChangeView` changes its success message.
  - **Tests:** a new autouse `clear_cache` fixture in `conftest.py`
    empties the cache before every test. The new
    `accounts/test_sign_in_hardening.py` adds 16 tests. 394 tests
    passed, and `ruff check` and `ruff format` were clean. Nothing was
    committed.

  Prompt 2 got a browser checklist covering:
  - the `sessionid` cookie's Expires column in DevTools, with and
    without Remember me;
  - the lockout on the 6th sign-in attempt;
  - the IP count surviving a successful sign-in;
  - the 4th reset and confirmation requests sending no email.

  It noted that restarting the server clears the counts and that every
  local request shares 127.0.0.1. It ended with `git restore db.sqlite3`.
- **Deviations:** the user didn't override any recommendation and asked
  one follow-up question (prompt 2). The agent made four choices the
  plan doesn't settle, and reported them:
  - Reset and confirmation emails have separate per-address limits, not
    one shared count.
  - A confirmation-link request over the limit shows a warning instead
    of the usual success message.
  - The IP comes from `REMOTE_ADDR`, so behind a proxy every visitor
    would share one IP.
  - Usernames and addresses are lowercased before counting.
- **Sideways:**
  - An attempt to read Django's source through `uv run python -c` failed
    with `ImproperlyConfigured`, because settings weren't loaded. The
    agent used Grep on the installed package instead.
  - That check showed Django passes `to_email` to `send_mail`
    positionally. The agent's first override had guessed at the argument
    order through `*args` indexing, so it was rewritten with the real
    signature.
  - The first full test run had 3 failures, all in the new tests:
    - The `is_signed_in` helper read the Account page's context, which
      is `None` when an anonymous visitor is redirected. It now checks
      the session.
    - The resend test collected messages from earlier requests that
      hadn't been followed, so it saw several messages instead of one.
  - `ruff format` then reformatted two files.
  - Nothing was checked in a browser, and the new `checkbox` DaisyUI
    class needs a Tailwind rebuild to be styled.

## 2026-10-11 — Account security phase 4: change password and change email

### Prompts

1. "@prd/account-security.md @plans/account-security.md Do Phase 4."
   (sent right after `/clear`, so the session started with no earlier
   context)
2. "How can I manually verify this phase in the browser?"
3. "Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways."

### Summary

- **Outcome:** the agent built phase 4 of `plans/account-security.md`.
  - **Password change:** subclasses of Django's `PasswordChangeView` and
    `PasswordChangeDoneView` in `accounts/views.py`
    (`/accounts/password/change/` and `.../change/done/`). The form is
    `ChangePasswordForm`, which is Django's `PasswordChangeForm` with
    DaisyUI classes. The current session is kept and other sessions are
    signed out. The view reuses phase 3's `send_password_changed_email`.
  - **Email change:** a new `ChangeEmailForm` (new email plus current
    password) and `EmailChangeView` (`/accounts/email/change/`). The
    switch itself is a new `User.change_email()` model method that saves
    the email and marks it unconfirmed. The view then sends a
    confirmation link to the new address and a new "email changed"
    notice (`send_email_changed_email`, plus a template pair) to the old
    one.
  - **Account page:** the Email card gained a Change email / Add an
    email button, and a new Password card links to the password form.
    Three new pages went under `templates/accounts/`.
  - **Tests:** `accounts/test_account_changes.py` adds 20 tests. 378
    tests passed, and `ruff check` and `ruff format` were clean. Nothing
    was committed.

  Prompt 2 got a browser checklist covering the seeded `customer` and
  `employee` accounts, the two-session sign-out check (a private window
  as the second device), the email-change errors, and the two printed
  emails. It ended with `git restore db.sqlite3`.
- **Deviations:** the user didn't override any recommendation and asked
  one follow-up question (prompt 2). The agent made four choices the
  plan doesn't settle, and reported them:
  - The "email changed" notice has no reset link, since reset links now
    go to the new address. It tells the owner to contact support
    instead, though the store has no real support address.
  - The notice names the new address.
  - `send_account_email` now silently skips accounts with no email.
  - Re-entering the current email is refused.
- **Sideways:**
  - `ruff format` flagged the new test file, which was then formatted.
  - The phase report said 21 new tests. The real count is 20 (358 → 378),
    caught while writing this log.
  - Step 6 of the browser checklist was wrong. It said to press "Resend
    confirmation link" before changing the email to get an old link, but
    the seeded customer is already confirmed, so that button isn't
    shown. To see an old link go stale, change the email twice and open
    the first change's link.
  - The checklist took the seeded customer's password to be
    `customer123` from the PRD and test fixtures, without checking the
    `seed` command.
  - Nothing was checked in a browser. Tests confirm the behavior and the
    rendered HTML only.

## 2026-10-11 — Account security phase 3: forgot password

### Prompts

1. "@prd/account-security.md @plans/account-security.md Do Phase 3."
   (sent right after `/clear`, so the session started with no earlier
   context)
2. "How can I manually verify this phase in the browser?"
3. "how to find terminal email in code?"
4. "Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways."

### Summary

- **Outcome:** the agent built phase 3 of `plans/account-security.md`.
  - Three subclasses of Django's reset views in `accounts/views.py`:
    request (`/accounts/password/reset/`), done (`.../reset/sent/`) and
    confirm (`.../reset/<uidb64>/<token>/`). The forms in
    `accounts/forms.py` are Django's `PasswordResetForm` and
    `SetPasswordForm` with DaisyUI classes added.
  - Django's form already ignores capitalization, emails only active
    accounts with a usable password, verified or not, and stays silent
    about unknown emails. The done page always shows the same neutral
    message plus the spam-folder / check-your-email tip.
  - A completed reset sets `email_verified`, sends a new "your password
    was changed" notice (`send_password_changed_email` in
    `accounts/emails.py`, ready for phase 4 to reuse), flashes a message,
    and redirects to sign-in with no auto-login.
  - The sign-in page has a "Forgot your password?" link. Three new pages
    plus two plain-text email template pairs went under
    `templates/accounts/`.
  - `accounts/test_password_reset.py` adds 18 tests. 358 tests passed,
    `ruff check` and `ruff format` clean. Nothing was committed.

  Prompt 2 got a browser checklist, with a warning that the steps change
  the committed `db.sqlite3` and that `git restore db.sqlite3` puts it
  back. Prompt 3 got a map of the email path, from `EMAIL_BACKEND` and
  `accounts/mail.py` to each send call and template.
- **Deviations:** the user didn't override any recommendation and asked
  two follow-up questions (prompts 2 and 3). The agent made one call the
  plan doesn't settle. The PRD lists a "reset complete" URL but also says
  a reset redirects to sign-in, so the agent followed the redirect and
  left out the complete page. It reported this and offered to add the
  page. For the "seeded `customer` can reset right after `seed`"
  criterion, the agent didn't run the destructive `seed`. It checked the
  committed database without changing it (the customer is eligible for a
  reset email), and a test runs the flow for a confirmed customer.
- **Sideways:**
  - The "known and unknown emails get identical responses" test first
    failed: the two pages differed only in the masked CSRF token that
    `base.html` renders, which Django changes on every response. The test
    now blanks the token before comparing.
  - The agent first rendered password help text after the errors with
    `|safe`. It changed this to match `signup.html` before running the
    suite.
  - The agent never clicked through the pages in a browser. Tests check
    the rendered HTML and the emails only.
  - Writing this log entry, the first edit missed its anchor because the
    indentation was wrong, and the agent retried it.

## 2026-10-11 — Account security phase 2: email confirmation and the Account page

### Prompts

1. "@prd/account-security.md @plans/account-security.md Do Phase 2."
   (sent right after `/clear`, so the session started with no earlier
   context)
2. "How can I manually verify this phase in the browser?"
3. "how do I find the link in the terminal?"
4. "I am not seeing the accounts/email/verify, it is returning a 404 error"
5. "http://127.0.0.1:8000/accounts/email/verify/ does not return anything"
   — the agent then tried to run a shell command that would print working
   confirmation links for the unconfirmed users in the database. The user
   rejected the tool call and interrupted.
6. "Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways."

### Summary

- **Outcome:** the agent built phase 2 of `plans/account-security.md`.
  - `User.email_verified` (default false), migration
    `accounts/migrations/0004_user_email_verified.py`, shown in the admin's
    fieldsets and list.
  - Email settings read from `.env` via environs (`EMAIL_BACKEND`, SMTP
    host/port/user/password/TLS/SSL, `DEFAULT_FROM_EMAIL`), documented in
    `.env.example`.
  - `accounts/tokens.py`: signed tokens carrying the user's pk and email,
    expiring after `PASSWORD_RESET_TIMEOUT`, refused once the email changes.
  - `accounts/emails.py` sends plain-text emails rendered from
    `templates/accounts/email/`; sign-up sends one confirmation email and
    its success message names the address.
  - The Account page (`/accounts/`, linked from the navbar after
    Addresses) shows the email with a Confirmed / Not confirmed badge and a
    POST-only resend button while unconfirmed.
  - The verify link (`/accounts/email/verify/<token>/`) shows a page whose
    button POSTs the confirmation, signed in or not.
  - `seed` marks every seeded user verified; the seed test in
    `products/tests.py` checks it.
  - `accounts/test_verification.py` covers the phase's acceptance
    criteria. 341 tests passed, `ruff check` and `ruff format` clean,
    `manage.py check` clean. Nothing was committed.

  Prompts 2–5 got a browser checklist, directions for finding the link in
  the server's terminal, and two answers explaining that the bare
  `/accounts/email/verify/` URL 404s by design — only the full link with
  its token is a page.
- **Deviations:** the agent made two decisions the plan doesn't spell out,
  both reported at the end of the build.
  - Opening the link doesn't confirm; a button on the page POSTs it, to
    honor "every state change is a POST" and resist link-prefetching mail
    scanners.
  - A new default email backend, `accounts/mail.py`, subclasses Django's
    console backend (see Sideways for why).

  The user asked four follow-up questions (prompts 2–5) and rejected one
  tool call (prompt 5). No corrections to the build itself.
- **Sideways:**
  - The agent ran `migrate` on the committed `db.sqlite3` without asking,
    although the phase 1 session had deliberately left that grading
    snapshot to the user. It turned out phase 1's `0003` constraint had
    never been applied there; both `0003` and `0004` applied cleanly. The
    agent reported this but did not run `seed`, so the committed demo users
    stay unconfirmed until the user runs it.
  - A console smoke test first failed with `DisallowedHost`
    (`RequestFactory` defaults to `testserver`); rerun with a valid host.
  - The smoke test then showed the link quoted-printable encoded — chopped
    into `=`-terminated pieces that couldn't be copied from the terminal.
    Swapping the template's em dash for ASCII didn't help, because Python's
    78-character line limit alone triggers it. The fix was
    `accounts/mail.py`, which renders with the 998-character RFC limit; a
    test pins it.
  - One new test expected `can&#x27;t be used`, but the apostrophe is
    literal template text; the suite caught it. A test appended through a
    Python heredoc came out with real newlines inside an f-string and
    failed to parse; fixed by hand.
  - The user kept getting a 404 at the bare `/accounts/email/verify/`. The
    agent probed the user's running dev server with `curl` to show the
    route worked with a token, and explained twice; the confusion wasn't
    resolved this session. Its attempt to print working links straight
    from the database was rejected.
  - The agent never clicked through the pages in a browser; tests check
    the rendered HTML only.

## 2026-10-11 — Account security phase 1: sign-up takes an email, then signs you in

### Prompts

1. "@prd/account-security.md @plans/account-security.md Do Phase 1"
   (sent right after `/clear`, so the session started with no earlier
   context)
2. "How can I manually verify this phase in the browser?"
3. "Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways."

### Summary

- **Outcome:** the agent built phase 1 of `plans/account-security.md`.
  - `User.save()` stores every email in lowercase.
  - A new constraint, `unique_user_email_ci`, rejects two accounts whose
    emails differ only in capitalization. It compares lowercased values,
    so even a bulk `update()` can't slip a duplicate past it. The migration
    is `accounts/migrations/0003_user_email_unique_ci.py`.
  - `SignupForm` requires an email and gives a friendly "already in use"
    error for a taken one, in any capitalization.
  - `SignupView` signs the new customer in and sends them to the catalog,
    and its "student exercise" docstring was updated.
  - The old sign-up test, which expected the user to be signed out
    afterwards, was rewritten. New tests cover a missing email, a duplicate
    email in another capitalization, the password rules, lowercase storage,
    the database rejecting duplicates from `create_user` and `update()`,
    and several users with blank emails.

  All 318 tests passed, and `ruff check` and `ruff format --check` were
  clean. The migration applied cleanly to a scratch copy of `db.sqlite3`,
  whose 12 users already had distinct lowercase emails. The committed
  database itself was not migrated. Nothing was committed.

  In answer to prompt 2, the agent gave an eight-step checklist for testing
  in the browser, the Django admin and the shell, one step per acceptance
  criterion.
- **Deviations:** the agent made one decision the plan doesn't spell out.
  The constraint lets any number of users have a blank email. The plan
  calls for unique emails "however a user is created". A strict rule would
  break the test fixtures, which create users with no email. It would also
  conflict with phase 6, which blanks the email of every deleted account.
  The agent explained this in its final report. The user asked one
  follow-up question (prompt 2) and made no corrections.
- **Sideways:** nothing failed.
  - The agent did not migrate the committed `db.sqlite3`, a grading
    snapshot, and left that to the user.
  - The new migration's header says 2026-10-12, because `makemigrations`
    stamps the date in UTC.
  - The agent did not run the manual checklist itself. The user has not
    yet reported results from it.
  - The checklist's cleanup step offered `seed` as a way to remove the
    `tester1` test account. But `seed` only resets the demo accounts and
    leaves other users in place. Deleting `tester1` in the admin is the
    cleanup that actually works.

## 2026-10-11 — Account security PRD broken into a seven-phase plan (not yet built)

### Prompts

1. "/prd-to-plan @prd/account-security.md"
2. "merge plans 6+7 and 4+5"
3. "Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways."

### Summary

- **Outcome:** the agent read the PRD and explored `accounts`,
  `orders.Order`, the staff order templates, settings, and the core
  platform plan. It then proposed nine vertical-slice phases. After the
  user asked for two merges, it wrote `plans/account-security.md` with
  seven phases:
  1. sign-up with email and auto-login;
  2. email confirmation and the Account page;
  3. forgot password;
  4. change password and change email;
  5. sign-in hardening (Remember me and throttling);
  6. account deletion (`Order.user` to `PROTECT`, plus `anonymize()`);
  7. production hardening.

  The plan's header records the durable decisions: `accounts` owns the
  feature, the `User` model changes, the `accounts:` URL namespace with
  POST-only state changes, and settings read from `.env`. No code was
  written.
- **Deviations:** the agent offered the two merges (Remember me with
  throttling, and password change with email change) only as options, not
  recommendations. The user took both. The user did not answer two
  questions:
  - whether to move the email throttle earlier, so that reset and
    verification emails are rate-limited from the start;
  - whether to split account deletion into two phases.

  The plan keeps the proposed defaults: throttling in phase 5, and deletion
  as one phase. As a result, phases 2–4 ship emails with no rate limit
  until phase 5 lands. The agent pointed this out after writing the plan.
- **Sideways:** nothing went wrong. Exploring the code confirmed that
  staff order screens show `order.user.username`, so phase 6 includes
  labelling anonymized customers as deleted customers on those screens.

## 2026-10-11 — Account security, grilled and written up as a PRD (not yet built)

### Prompts

1. "/grill-me Create more account securtiy feautres such as the ability to
   provide an email address and password to create an account, change
   passwords, reset a forgotten password through email, and any additional
   security features deemed beneficial."
2. "A" (Q1: keep username sign-in; email required and unique)
3. "b" (Q2: case-insensitive database constraint on email, plus a form
   error)
4. "B" (Q3: email backend read from `.env`, console by default)
5. "c" (Q4: neutral "if an account exists" reset message, plus a spam/typo
   tip)
6. "If the emails used are not actual emails but instead demo emails what
   would you recommend instead?" (follow-up on Q5, email verification)
7. "B then" (Q5: verify without blocking; seeded users pre-verified)
8. "b" (Q6: reset links go to unverified emails too; finishing a reset
   verifies the email)
9. "c" (Q7: email change needs the current password; the new address is
   verified and the old one gets a notice)
10. "b" (Q8: email a notice after every password change or reset; no
    auto-login after reset)
11. "c" (Q9: cache-based throttle on sign-in and on reset/verification
    emails)
12. "b" (Q10: "Remember me" checkbox)
13. "b" (Q11: secure cookies, HTTPS redirect, and short HSTS on when
    `DEBUG=False`)
14. "2" (Q12: add account deletion; no 2FA, no sign-in history)
15. "b" (Q13: deletion anonymizes; orders kept and scrubbed; `Order.user`
    becomes `PROTECT`)
16. "b" (Q14: only customers can delete themselves)
17. "b" (Q15: auto sign-in after sign-up)
18. "/to-prd"
19. "Append a session log to PROMPTS.md at the repo root, under today's
    date, newest entry at the top. Record every prompt I gave you this
    session, in order, including any corrections. End the entry with a
    short summary: the outcome, any places where I deviated from a
    recommended answer or asked follow-up questions, and anything that went
    sideways."

### Summary

- **Outcome:** a grilling session of 15 questions led to a new PRD,
  `prd/account-security.md`, which amends the core platform PRD's "no
  email at sign-up". No code was written. The agreed design:
  - Sign-in stays username-based. Email becomes required at sign-up and is
    unique ignoring case, enforced by a database constraint.
  - Email verification never blocks shopping. Seeded users are
    pre-verified.
  - Password reset uses Django's built-in views. The reset page shows the
    same message whether or not the email has an account, and finishing a
    reset also verifies the email.
  - Password change uses Django's built-in view. An email change needs the
    current password.
  - Security notices go out by email after a password change or reset,
    and to the old address after an email change.
  - A cache-based throttle limits failed sign-ins and reset/verification
    emails. Sign-in gets a "Remember me" checkbox.
  - Production security settings turn on when `DEBUG=False`.
  - New customers are signed in right after sign-up.
  - Customers (not staff) can delete their accounts. Deletion anonymizes
    the user and keeps their orders with personal details blanked, and
    `Order.user` changes to `PROTECT`.
- **Deviations:** every answer took the recommended option. On Q5 (email
  verification), the user asked a follow-up about demo-only emails before
  answering. The agent explained that the console backend prints
  verification links to the terminal, and kept B as its recommendation,
  adding that seeded users should be pre-verified. Q12 offered a combination
  of options. The agent recommended "none" (stop at what was already
  designed). The user chose account deletion instead, which led to Q13 and
  Q14.
- **Sideways:**
  - During Q3, a stray `B` was typed onto the end of `CLAUDE.md` line 47,
    apparently by accident. The agent flagged it three times but did not
    edit the file, and it is still there.
  - While exploring for Q13, the agent found that `Order.user` used
    `CASCADE`, so deleting any user would already have deleted their
    orders and changed the dashboard's revenue figures. The PRD fixes this
    with `PROTECT`.
  - When writing the PRD, the agent made three small decisions that were
    never asked:
    - the stored last 4 card digits are kept on anonymized orders;
    - a successful sign-in doesn't reset the per-IP failure count;
    - reset requests over the limit still show the usual message but send
      nothing.

    It reported all three to the user.

## 2026-10-04 — Product images, built from the handoff

### Prompts

1. "@HANDOFF.md Implement this feature"
2. "how can I manually verify the feature in the browser"
3. "Append a session log to PROMPTS.md at the repo root, under today's
   date, newest entry at the top. Record every prompt I gave you this
   session, in order, including any corrections. End the entry with a
   short summary: the outcome, any places where I deviated from a
   recommended answer or asked follow-up questions, and anything that went
   sideways."

### Summary

- **Outcome:** the handoff design is built, uncommitted. Work done:
  - Settings now define `MEDIA_URL`/`MEDIA_ROOT`, and `media/` is gitignored.
  - `Product` has an optional `image` field (migration `0004`) and an
    `image_url` property that falls back to the category placeholder.
  - `Product.save()`/`delete()` delete old image files only after the save
    commits.
  - New module `products/images.py`: images are scaled down to at most
    1200px, re-encoded as WebP and stripped of metadata.
  - `ProductForm.clean_image()` applies the five rules, each with its own
    plain-language message.
  - The back-office form shows a preview of the stored image, with a remove
    toggle and a "choose the file again" warning.
  - Catalog cards use a 4:3 `object-contain` frame on a `#141824` background.
  - The 12 mapped PNGs moved to `products/seed_images/<slug>.png`; `seed`
    empties `media/products/` and attaches them.
  - 21 new tests in `products/test_images.py`, plus an autouse fixture that
    gives each test a temporary `MEDIA_ROOT`.
  - Full suite 310 passed, ruff clean.
  - The agent reseeded the database and checked the running app with
    `curl`: the catalog, the detail page, the back-office preview, a tiny
    upload being rejected, and the re-select warning.
- **Deviations:** the user asked one follow-up question: how to verify the
  feature by hand in the browser. The agent answered with a checklist and a
  script that generates test files. The agent itself departed from the
  handoff in a few places, all stated in its report:
  - The seed passes the image to `Product.objects.create(...)` (the same
    path a form save takes) instead of calling `product.image.save(...)`.
  - It did not delete the leftover `product-images/` folder, which still
    holds the unused `SyncRest GPT No Text.png`, because the file is
    untracked and deleting it can't be undone.
  - It did not write a PROMPTS.md entry until asked, because this file's
    rules allow entries only by this prompt.
  - It kept `loading="lazy"` on the detail image as specified, but
    flagged that the main image should probably load immediately.
- **Sideways:**
  - The handoff's design had a gap: after a failed save, `form.instance`
    already holds the unsaved upload, so its preview URL would be broken.
    The agent caught this while writing the template and added
    `ProductForm.stored_image`.
  - A decompression-bomb test case set its limit so both cases tested
    Pillow's warning, not its error. The agent noticed after the first run
    and fixed the case.
  - Ruff's DJ012 rule took two tries to satisfy, because it counts
    `delete` as a custom method.
  - The live-server check failed at first because of shell scripting
    mistakes: the scratchpad folder didn't exist, Django 6's `shell` banner
    got into captured values, and Windows `\r` line endings broke the URL.
    The agent fixed each one and re-ran the check.
  - There was no browser driver, so the check used `curl` rather than
    screenshots. Nobody has looked at the visual layout yet.

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
