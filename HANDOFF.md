# HANDOFF — Product images

**Next session's job:** implement the product-image design below. The design
was settled in a `/grill-me` interview with the user (2026-10-04); every
decision here is final — don't re-litigate, just build. No code has been
written yet, and no PRD/plan file exists for this feature (this doc is the
only record of the decisions).

Before starting, read `CLAUDE.md`, `docs/TEMPLATES.md` (before touching
templates) and `docs/TESTING.md` (before writing tests).

## The feature (user's words, condensed)

Give catalog products real images from the source PNGs in `product-images/`;
products without an image keep their existing category placeholder (never a
missing file or broken image). Employees can upload product images in the
back office; unusable files are rejected with a plain-language explanation.

## Current state of the working tree (uncommitted, pre-existing)

- `pyproject.toml` / `uv.lock`: `pillow>=12.3.0` already added.
- `config/urls.py`: already serves `settings.MEDIA_URL` from `MEDIA_ROOT`
  under `DEBUG` — **but `config/settings.py` defines neither**, so this must
  be fixed first (empty `MEDIA_URL` makes `static()` raise).
- `product-images/` (untracked): 13 PNGs, ~1122×1402 portrait, 1.7–2.5 MB.

## Agreed design

### 1. Model — one optional image per product
- `Product.image = models.ImageField(upload_to="products/", blank=True)` + migration
  (next is `products/migrations/0004_...`).
- A model property (e.g. `Product.image_url` / `display_image_url`) returns
  `image.url` if set, else the static URL of `category.placeholder_image`
  (`products/models.py:32`). Templates use only this property.
- Add `MEDIA_URL = "media/"` and `MEDIA_ROOT = BASE_DIR / "media"` to
  settings (working defaults, no `.env` required); add `media/` to `.gitignore`.

### 2. Seed mapping
Move `product-images/` → `products/seed_images/` with clean slug filenames,
commit them, delete the old folder. Mapping (source file → seeded product):

| Source file | Product |
|---|---|
| Seraphine GPT Text.png | Seraphine (only the base product) |
| Hush GPT No Text.png | Hush |
| MindSync GPT 2.png | MindSync |
| MindSync Duo.png | MindSync Duo |
| RecallPro.png | RecallPro |
| MoodSet GPT No Text.png | MoodSet |
| DreamWeaver Matrix GPT 3.png | DreamWeaver |
| Veil GPT Text.png | Veil |
| Calm Collar GPT Man.png | Calm Collar |
| CrowdCalm Array No Text.png | CrowdCalm Array |
| SoulSear No Text.png | **SoulSear Mark II** only |
| SyncRest GPT Text.png | SyncRest (the **Text** poster version) |
| SyncRest GPT No Text.png | *unused — don't commit it* |

12 products get images; the other 22 keep placeholders.

### 3. Seed behavior
`products/management/commands/seed.py` (`_create_catalog`, ~line 588):
- Reset step empties `media/products/` (seed is already destructive) so
  reseeding doesn't leave orphaned suffixed copies.
- Attach each mapped image via `normalize_image()` + `product.image.save(...)`
  — the same path uploads take.

### 4. Normalization — `products/images.py: normalize_image()`
Shared by `ProductForm.clean_image()` and `seed`. Pillow: decode, downscale
so the longest side ≤ **1200px** (never upscale), re-encode as **WebP
quality ~85**, which also strips EXIF/GPS metadata. Originals are not kept.
Give it a docstring + type hints.

### 5. Validation — `ProductForm.clean_image()` (`products/forms.py`)
Each rule has its own plain-language error (no exception names):

1. Must decode as JPEG, PNG or WebP (check by decoding, not by extension) →
   "This file isn't a picture we can use. Please upload a JPEG, PNG, or WebP image."
2. A real image in another format (GIF, HEIC, SVG, TIFF, BMP…) → names the
   format, e.g. "We can't use HEIC images. Please save it as a JPEG or PNG and try again."
   (No `pillow-heif` — HEIC is rejected, not supported.)
3. ≤ 10 MB → "This image is 14.2 MB, which is over our 10 MB limit. Please use a smaller file."
4. Shortest side ≥ 400px → "This image is only 250 × 180 pixels, so it would
   look blurry on the product page. Please use one at least 400 pixels on each side."
5. Truncated/corrupt files and decompression bombs → "This image appears to
   be damaged or incomplete. Please try exporting it again."

### 6. Back office editing
- `templates/products/manage_product_form.html`: add
  `enctype="multipart/form-data"`; add `image` to `ProductForm.Meta.fields`;
  make sure `StyledModelForm` styles the file widget sensibly.
- Show a preview of the current image, or "Using the category placeholder".
- File picker to replace; a "Remove image" checkbox reverts to placeholder.
- Old files are deleted from disk on replace, remove, and product delete —
  **only after the DB save commits** (`transaction.on_commit`). Logic lives on
  the model (save/delete hooks comparing old vs. new file), per CLAUDE.md.
- If the form fails on another field, the browser drops the chosen file;
  the error message should tell the employee to re-select it.

### 7. Display
- `templates/products/catalog.html:64` and `templates/products/detail.html:17`
  switch to the new model property.
- Catalog cards: fixed **4:3** frame, `object-contain` (whole image visible,
  never cropped) on a dark background matching the placeholders (`#141824`).
- Detail page: full image, uncropped.
- `alt="{{ product.name }}"`, `loading="lazy"`.

### 8. Tests
- One rejection test per validation rule (1–5), checking the message.
- Normalization: output is WebP, longest side ≤ 1200, metadata stripped, no upscaling.
- Placeholder fallback when `image` is empty.
- File cleanup on replace / remove / delete, and none on a rolled-back save.
- Seed attaches exactly the 12 mapped images.
- Point `MEDIA_ROOT` at a temp dir in tests so they never write to `media/`.

## Finishing up
- `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`
- `uv run python manage.py seed`, then eyeball the catalog/detail/back office.
- Append an entry to `PROMPTS.md` (append only — never rewrite history).
- Commit only when the user asks.

## Suggested skills
- **run** — launch the dev server to visually check cards, detail page, and
  the upload/reject flow in the back office.
- **code-review** — review the diff for correctness before committing.
- **simplify** — a cleanup pass on the changed code once tests pass.
- **grill-me** (project skill) — only if a genuinely new design question
  comes up that this doc doesn't answer; ask the user rather than guessing.
