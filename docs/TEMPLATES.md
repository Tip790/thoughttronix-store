# Template conventions

- Every page extends the project-level `templates/base.html` (DaisyUI navbar,
  footer motto). DaisyUI theme: `night`, set in `assets/css/source.css` and
  `data-theme` on `<html>`.
- Back-office pages extend `templates/backoffice/base.html` — the staff shell
  with the tab rail; the active tab comes from the view's `section` context
  entry.
- HTMX endpoints render partials from `templates/<app>/partials/_<name>.html` —
  prefixed with an underscore, never extending `base.html`.
- Every list view gets a designed empty state, not a blank page.
- Styling is Tailwind + DaisyUI classes only; no crispy-forms, no JavaScript
  beyond HTMX.
-Status and feedback styling uses DaisyUI semantic classes such as alert-*, badge-*, and text-error. Do not use raw Tailwind color classes such as bg-yellow-100 or text-red-500.
-Every data table uses the DaisyUI table class inside an overflow-x-auto wrapper, with the header row inside a thead.
-Every page opens with an h1 using text-3xl font-bold, followed by a one-line description using opacity-70.
-Each page has at most one btn-primary for its main action. Other buttons and button-styled links use btn-ghost or btn-outline.
