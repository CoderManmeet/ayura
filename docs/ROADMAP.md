# ROADMAP — Ayura store (v1, 11 Oct 2026)

Ayura is a separate brand built from the Noore Candles codebase: its own repo (Noore's git
history kept, new remote), database, Render backend, Vercel frontend, Cloudinary and Razorpay
accounts. Noore keeps running unchanged. Noore's roadmap is kept, unchanged, at
`docs/archive/ROADMAP-noore-v2.md`; its free-hosting guide at `docs/archive/DEPLOY-FREE-noore.md`.

**Lost reference.** Noore's roadmap pointed to `docs/archive/ROADMAP-v1.md` for its Appendix C
(order state-machine tables) and Appendix E (removal proposals R1-R21). That file was never in
the repository and the owner does not have it (confirmed 11 Oct 2026). The enforced state
machine is `backend/store/order_state.py`; it is the reference from now on. R1-R20 must be
re-listed from the code before any of them is proposed again.

Ayura sells home-made natural skincare, haircare and bodycare: essential-oil blends,
shampoos and similar. No product is licensed as an Ayurvedic (AYUSH) medicine, and every
product is sold as a cosmetic.

## Decisions locked by the owner (11 Oct 2026)

| # | Decision |
|---|---|
| Y1 | Separate repo forked with Noore's history. No multi-brand code |
| Y2 | Not GST-registered at launch. Tax rate 0, prices shown "inclusive of all taxes", no HSN fields (same as Noore P5) |
| Y3 | No AYUSH-licensed products. Every product is a cosmetic, and copy uses cosmetic language only |
| Y4 | Categories can have sub-categories (Skincare → Face → Serums) |
| Y5 | No stored filter attributes (skin type, hair type, concern, dosha). Instead each product gets a short owner-written benefit line, shown on the product card |
| Y6 | The owner creates sizes from the admin area. Each size carries a net quantity in grams **or** millilitres |
| Y7 | Free gift samples: the owner decides per order whether samples go in and which ones; the store tracks which sample recipients later bought the full product |
| Y8 | Kits are assembled from the stock of their component products, not stocked separately |
| Y9 | No refill subscriptions |
| Y10 | The owner sets shipping in the admin area: on/off, flat amount, and optional free shipping above a threshold |
| Y11 | The owner sets an optional COD fee (on/off and amount), meant to nudge customers towards UPI |
| Y12 | No shelf-life rules and no blocking when an expiry date is missing. The owner can record an expiry date before dispatch, and the admin area flags expired or undated stock before shipping |
| Y13 | The owner makes the products at home. Label details (maker name and address, etc.) are store-wide |
| Y14 | Damaged, leaking or other problems are handled through a customer support query system |
| Y15 | Theme and shared UI become brand-neutral: `theme/brand.css`, `.ui-*` classes, `views/ui/kit.jsx` (written approval for the rename, 11 Oct 2026) |
| Y16 | BUILD_LOG gets a reconstructed catch-up section; CLAUDE.md is updated for Ayura (approved) |
| Y17 | Hosting on free tiers; the frontend lives on a `*.vercel.app` address for now |
| Y18 | Test variable names containing "candle" stay. Only strings a shopper can see, and seed slugs, change |
| Y19 | Gift samples are a surprise: the customer is **never** told about them on the order page, in emails or anywhere else (owner, 11 Oct 2026). They show only in the admin area |
| Y20 | Brand assets: tagline "If we wouldn’t use it at home, we don’t bottle it."; WhatsApp 7888548215 (`917888548215` for wa.me); support email stays a placeholder for now; logo supplied 11 Oct 2026 (leaf and gold drop above the word AYURA) |
| Y21 | Palette: option 2, "Turmeric" (off-white, turmeric yellow, deep green, Bricolage Grotesque) |

## Defaults taken on the owner's behalf (cheap to reverse)

| # | Decision | Why | Cost to reverse |
|---|---|---|---|
| Z1 | An already-expired batch is still never allocated to a new order (existing behaviour). `MIN_SHELF_LIFE_ON_DISPATCH_DAYS` defaults to **0** for Ayura, so no other date rule applies, and undated batches sell normally | Shipping expired skincare to a customer is the one thing that should never happen silently. Everything else is a flag, not a block (Y12) | One line |
| Z2 | A sample is a **hidden variant of the real product** (e.g. Face Scrub, "10 ml sample"), with price 0 and its own stock in the ledger. It never appears in the shop or the size picker | Conversion is then simply "later bought any full-size variant of the same product" | Low |
| Z4 | The benefit line is at most 120 characters, entered by the owner. On phones (where hover doesn't exist) it shows under the title. The admin form shows a **soft warning** (it doesn't block saving) for words like cure, treat, heal, clinically proven, guaranteed, 100%, chemical-free, dermatologist | Your guardrail on disease claims, enforced where the copy is typed | Edit a word list |
| Z5 | The COD fee is a separate line, shown on the payment choice and in the total **before** "Place order". Coupons don't discount it, and it doesn't count towards the free-shipping threshold | CLAUDE.md §8 drip pricing: every fee is shown before the customer commits | Low |
| Z6 | Support is **asynchronous query threads** (like email in the account), not live chat | Free Render sleeps and has no websockets; a thread works when you reply hours later | Medium |
| Z7 | A kit's price is set by the owner, not computed from its components. A kit can't contain another kit or a sample | Simple and predictable for the customer | Low |
| Z8 | Ingredients, how to use and cautions are owner-typed text fields. Nothing is generated, and no "free from" or "natural" badge exists unless a later phase adds a stored field for it | Your guardrail: every claim is a stored fact the owner entered | Low |
| Z9 | Copy and seed data do not call products "Ayurvedic" or "natural" until the professional answers L1 and L7 below | A non-AYUSH product described as Ayurvedic is exactly the kind of claim to clear first | Edit copy |

## Legal questions for your professional (not decided in code)

| # | Question |
|---|---|
| L1 | Does making cosmetics at home for sale need a cosmetics manufacturing licence (Cosmetics Rules, 2020), and what must the label then carry? |
| L2 | GST: does selling to customers in other states from your own website require registration even below the turnover threshold? (The same question applies to Noore.) |
| L3 | Legal Metrology: which declarations must appear on the product page (net quantity, MRP, maker's name and address, country of origin, consumer-care contact, manufacture/expiry date)? |
| L4 | Consumer Protection (E-Commerce) Rules: grievance officer details and the return/refund disclosure the site must publish |
| L5 | Trademark: "AYURA" is an existing Japanese skincare brand sold internationally. Is the name clear to use in India (cosmetics class)? |
| L6 | Benefit lines: which wording is cosmetic ("for dry skin", "helps cleanse") and which is a drug claim ("helps with acne / hair fall / dandruff")? |
| L7 | Can a product that isn't AYUSH-licensed be described as "Ayurvedic" anywhere, including the brand tagline? |

## How phases run

Unchanged from CLAUDE.md: one branch per phase (`phase/<id>-<slug>`), database backup
before any migration, full files, one reversible migration per logical change, every new test
shown failing first, a BUILD_LOG section with all ten headings, then stop for approval.
Every phase starts by recording `pytest` (SQLite **and** PostgreSQL) and Playwright counts.
Baseline at the fork: SQLite 197 passed / 2 skipped; PostgreSQL 199 passed; Playwright 20 passed.

Delivery: only changed files, each complete, with its repo path, marked NEW or MODIFIED. Each
file is checked against the version last delivered before it goes out.

Phase order: A → B → C → D → E → F.

---

## A — Fork and rebrand

**Goal.** The repo is Ayura's, looks and reads like Ayura, and no shopper ever sees "Noore",
"candle" or "vendor".

**Owner supplies before the palette checkpoint.** Logo (SVG preferred), favicon (or approval
to derive it from the logo), font names, support email, WhatsApp number, tagline.

**Schema.** None.

**Work.**

1. Fork: exact commands to clone with history, set the new remote, and make a fresh
   `backend/.env` with a **new** `DJANGO_SECRET_KEY` (never Noore's).
2. Docs first:
   - BUILD_LOG section "Reconstructed: commits 947ed05 to c879153 (4–11 Oct 2026)", from the diffs.
   - CLAUDE.md: identity changed to Ayura, the stale §2/§3 lines fixed.
   - This file becomes `docs/ROADMAP.md`; Noore's roadmap moves to the archive.
3. Brand-neutral rename (Y15):
   - `theme/noore.css` → `theme/brand.css`.
   - Colour tokens get role names instead of colour names (`canvas`, `surface`, `muted`, `ink`, `subtle`, `accent`, `line`, …).
   - `.noore-*` → `.ui-*`, `.noore-admin` → `.ui-admin` in `theme/admin.css`.
   - `views/ui/noore.jsx` → `views/ui/kit.jsx`; every importer is updated.
   - The `apiCache` key prefix becomes neutral.
4. **Palette checkpoint (stop):** 2–3 Ayura palette and type options, each screenshotted on home,
   product page and cart at 390 px and 1280 px. You pick one, then it's committed to `brand.css`.
5. Store name, SEO and favicon:
   - `index.html` title, description and theme-color.
   - The API preconnect address is read from `%VITE_API_ORIGIN%`, so the next fork needs no edit there.
   - `favicon.svg` placeholder until your file arrives.
   - `STORE_NAME` defaults set to Ayura (backend settings, `.env.example`, `render.yaml`).
6. Copy: every candle string in the audit becomes neutral store wording. Home, footer, About
   and the policy pages are rewritten for personal care as clearly-marked placeholders
   (`PLACEHOLDER_COPY` stays `true`). The policy pages gain empty, labelled sections for patch
   test/cautions, opened products, and damaged or leaking items (pointing to Contact until F ships).
   No "Ayurvedic", "natural", "chemical-free" or origin claim (Z9).
7. `seed_ayura` (DEBUG only, idempotent), with categories Skincare, Haircare and Bodycare (flat
   until B), about 8 placeholder products in two or three sizes each (e.g. face serum, face
   scrub, moisturiser, hair oil, shampoo, body butter, body oil), opening stock through the ledger, coupon
   `WELCOME10`. Every description is cosmetic language and marked `[PLACEHOLDER COPY]`.
   `seed_noore` stays in the repo (rule 4; removal proposal) but Playwright switches to `seed_ayura`.
8. Deploy: `render.yaml` (`ayura-api`), `keep-awake.yml` default URL, the `deploy/` units renamed
   `ayura-*` with paths `/srv/ayura`. New `docs/DEPLOY-AYURA.md`: Vercel + Render + Neon +
   Cloudinary + GitHub keep-awake, every env var listed with where its value comes from. It
   also covers email: with no provider configured, no email is sent.

**Files touched.** `frontend/index.html`, `public/favicon.svg`, `src/main.jsx`, `src/App.jsx`,
`src/theme/brand.css` (new, replaces `noore.css`), `src/theme/admin.css`, `src/views/ui/kit.jsx`
(new, replaces `noore.jsx`), `src/utils/constants.js`, `apiCache.js`, `image.js`,
`usePageTitle.js`, `src/layouts/LegacyStyles.jsx`, `views/base/StoreHeader.jsx`,
`StoreFooter.jsx`, `NotFound.jsx`, `views/shop/home.jsx`, `Products.jsx`, `ProductDetail.jsx`,
`Cart.jsx`, `Checkout.jsx`, `OrderConfirmation.jsx`, `views/customer/Orders.jsx`,
`OrderDetail.jsx`, `BuyAgainButton.jsx`, `views/auth/login.jsx`, `register.jsx`, `logout.jsx`,
`ClaimAccount.jsx`, `views/policy/About.jsx`, `PolicyPage.jsx`, `Contact.jsx`, `policies.js`,
`views/owner/ShopNotReady.jsx`, `views/vendor/Dashboard.jsx`, `Sidebar.jsx`, `postcss.config.js`,
`.env.example`, `playwright.config.js`, all five `e2e/*.spec.js`; `backend/backend/settings.py`,
`.env.example`, `catalog/management/commands/seed_ayura.py` (new),
`core/management/commands/seed_e2e.py`, `catalog/tests/test_storefront.py`, `tests/test_launch.py`;
`render.yaml`, `.github/workflows/keep-awake.yml`, `deploy/*`, `docs/*`, `CLAUDE.md`.

**Acceptance.**

- The logged-out crawl fails on "noore", "candle" or "vendor" in any text, title, alt, label or
  link, and every title contains the store name.
- No `.noore-` class or `ui/noore` import is left (checked by grep in a test).
- `seed_ayura` refuses outside DEBUG, is idempotent, and no seeded text contains a banned claim
  word (test).
- pytest green on SQLite and PostgreSQL; the build passes; Playwright passes at 390 and 1280 px.

**Stop and ask.** The palette checkpoint. Any copy that would state a claim.

---

## B — Personal-care catalogue

**Goal.** The owner can run a real personal-care catalogue from the admin area without
touching Django admin.

**Schema (additive, one reversible migration each).**

1. `store.Category.parent` (nullable FK to itself). Cycles are refused in validation.
2. `catalog.ProductVariant.net_quantity` (positive int, nullable) and `net_quantity_unit` (`g` or `ml`).
   A data migration copies `weight_grams` into net quantity in grams; its reverse empties only the
   values it wrote. `weight_grams` stays as the shipping weight.
3. `store.Product`: `benefit_line` (120), `ingredients` (text), `how_to_use` (text), `cautions` (text).
4. `addon.ConfigSettings`: `maker_name`, `maker_address`, `country_of_origin`,
   `consumer_care_contact` (blank until supplied; L3).

**Work.**

- Admin area "Sizes" screen per product: add, edit or deactivate a size with label, net quantity,
  unit, price, MRP, SKU and shipping weight. Writes go through the variant model, so price
  history and audit still apply. Deactivating is allowed; deleting is not.
- Admin area "Add stock" screen: made-on date, optional expiry date, quantity, unit cost →
  `receive_production`. A batch's expiry date can be added or corrected later (audited).
- Category management with parent selection; the shop filters by category and sub-category
  (`/shop?category=<slug>` includes children); breadcrumb on the product page.
- Product card shows the benefit line (hover on desktop, always visible on phones); soft-warning
  word list in the add/edit product form (Z4).
- Product page: "Net quantity 100 ml", ingredients, how to use, cautions, and a "Product
  information" block (MRP inclusive of all taxes, maker, origin, consumer care) that shows only
  the fields that are filled.

**Files touched.** `backend/store/models.py`, `store/serializers.py`, `store/owner_views.py`,
`store/admin.py`, `catalog/models.py`, `catalog/admin.py`, `inventory/admin.py`,
`addon/models.py`, `api/urls.py`, the new migrations, `catalog/tests/test_catalogue_b.py` (new);
`frontend/src/views/owner/OwnerSizes.jsx`, `OwnerStock.jsx`, `OwnerCategories.jsx` (new),
`views/vendor/AddProduct.jsx`, `UpdateProduct.jsx`, `Sidebar.jsx`, `views/shop/ProductDetail.jsx`,
`Products.jsx`, `views/ui/kit.jsx`, `src/App.jsx`, `e2e/catalogue.spec.js` (new).

**Acceptance.** The owner creates "Face Serum" with 30 ml and 100 ml from the admin area, adds
stock, and the shopper sees both sizes with "Net quantity 30 ml". A sub-category appears under
its parent in the shop. A benefit line containing "cures" saves, but the form warns first.
Migrations apply and roll back on a copy.

**Stop and ask.** Anything that L3 makes mandatory but you haven't supplied.

---

## C — Owner-set shipping and COD fee

**Goal.** The owner controls shipping and the COD fee from the admin area, and every charge
is shown before the customer commits. **This changes what customers are charged; approved by
the owner in writing on 11 Oct 2026 (Q9).**

**Schema.**

1. `addon.ConfigSettings`: `shipping_enabled` (default True), `free_shipping_enabled` (default
   True), `cod_enabled` (default True), `cod_fee_enabled` (default False), `cod_fee_paise` (default 0).
2. `store.CartOrder.cod_fee_paise` (default 0; paise-only new column).

**Work.**

- `store/pricing.quote()` gains `payment_method`. It adds the COD fee only for COD;
  `total = subtotal - discount + shipping + cod_fee`. It stays the only place totals are computed.
- Checkout: the payment choice shows "Cash on delivery (+ ₹X fee)". Switching method re-quotes
  and the total updates before "Place order". A Razorpay order is always created from the non-COD
  quote.
- Cart: "Shipping ₹X" or "Free"; the free-shipping nudge only when free shipping is enabled.
- Order emails and order pages show the COD fee row when it's not zero.
- Admin area "Store settings" screen for the five settings, audited.

**Files touched.** `backend/addon/models.py`, `store/models.py`, `store/pricing.py`,
`store/views.py`, `store/payment_views.py`, `store/order_state.py`, `store/emails.py`,
`templates/email/order_update.*`, `store/owner_views.py`, `api/urls.py`, migrations,
`tests/test_pricing_c.py` (new); `frontend/src/views/shop/Cart.jsx`, `Checkout.jsx`,
`OrderConfirmation.jsx`, `views/customer/OrderDetail.jsx`, `views/owner/OwnerSettings.jsx` (new),
`Sidebar.jsx`, `App.jsx`, `e2e/checkout.spec.js`.

**Acceptance.**

- Fee off: COD total equals the prepaid total.
- Fee ₹49 on: the COD total is ₹49 more, shown before "Place order", stored on the order, and
  never in the Razorpay amount.
- Shipping off means free; a free-shipping threshold edited in the admin area applies on the next quote.
- An existing order never changes when the settings change.
- The paise mirror check still passes, and a tampered client total is ignored.

---

## D — Dispatch checks, free samples, batch lookup

**Goal.** Nothing leaves expired or undated without the owner seeing it, and gift samples are
sent and measured.

**Schema.**

1. `inventory.MovementKind.SAMPLE_OUT` (outbound).
2. `catalog.ProductVariant.is_sample` (default False; hidden from the shop and the size picker).
3. New `store.OrderSample`: order, variant, qty, added_by, added_at. Unique on (order, variant).
4. `store.CartOrder.sample_decision`: `UNDECIDED` / `NONE` / `ADDED`.

**Work.**

- Handle orders: for each line, the batch(es) FEFO allocated, with "Expired", "No expiry date"
  or "Expires 12 Mar 2027". These are flags, not blocks (Y12). The owner can enter a missing
  expiry date right there (audited).
- Order page "Gift samples":
  - Choose "No samples" or add sample variants with quantities.
  - Stock is reserved now and consumed as `SAMPLE_OUT` on dispatch.
  - Nothing is ever charged; `quote()` doesn't see samples.
  - Never shown to the customer (Y19): not on the order page, not in any email.
- "Samples" report: per sample product, how many orders got it, and how many of those customers
  (matched by account, or the same email or phone) later placed a non-cancelled order with a
  full-size variant of that product, with the conversion % and the list of those orders.
- "Expiry" screen: batches with stock that are expired, expiring within `EXPIRY_ALERT_DAYS`, or
  have no date; write-off through the ledger (`DAMAGE_OUT`), never an edit.
- Batch lookup ("recall"): type a batch code to see every order that received it.
- `MIN_SHELF_LIFE_ON_DISPATCH_DAYS` default becomes 0 (Z1), with a test that an undated or
  in-date batch is allocated and an expired one never is.

**Files touched.** `backend/inventory/models.py`, `inventory/services.py`, `catalog/models.py`,
`store/models.py`, `store/order_state.py`, `store/owner_views.py`, `store/serializers.py`,
`store/emails.py`, `api/urls.py`, migrations, `tests/test_dispatch_samples.py` (new);
`frontend/src/views/owner/OwnerOrderDetail.jsx`, `OwnerOrders.jsx`, `OwnerSamples.jsx`,
`OwnerExpiry.jsx` (new), `Sidebar.jsx`, `App.jsx`, `views/customer/OrderDetail.jsx`,
`e2e/owner.spec.js` (new).

**Acceptance.**

- An order whose batch has passed its expiry shows "Expired" on Handle orders.
- Samples add stock movements exactly once on dispatch, change no total, and can't be added to a
  cancelled order.
- A customer who got a Face Scrub sample and later buys Face Scrub 100 ml counts as converted;
  buying something else does not.
- Batch lookup lists exactly the orders with `SALE_OUT` or `SAMPLE_OUT` from that batch.

---

## E — Kits from component stock

**Goal.** A kit (e.g. "Face routine: cleanser + serum + moisturiser") is sold as one item and
draws stock from its components.

**Schema.**

1. New `catalog.KitComponent`: kit_variant, component_variant, qty (≥1). Unique pair. A kit or a
   sample can't be a component.
2. `catalog.ProductVariant.is_kit` (default False).

**Work.**

- A kit's availability is the minimum over its components of `available_qty // qty`.
- Adding a kit to the cart reserves every component (FEFO) in one transaction, and all or
  nothing; release, expiry and dispatch follow the components. The order line is the kit
  variant at the kit's price.
- Admin area kit builder.
- The product page lists what's inside.

**Files touched.** `backend/catalog/models.py`, `catalog/admin.py`, `inventory/services.py`,
`store/views.py` (`put_in_cart`), `store/order_state.py`, `store/serializers.py`,
`store/owner_views.py`, `api/urls.py`, migrations, `inventory/tests/test_kits.py` (new);
`frontend/src/views/owner/OwnerKits.jsx` (new), `views/shop/ProductDetail.jsx`,
`Sidebar.jsx`, `App.jsx`, `e2e/kits.spec.js` (new).

**Acceptance.**

- Kit availability tracks its scarcest component.
- Two shoppers racing for the last component can't both get it (PostgreSQL concurrency test).
- Cancelling returns every component.
- Dispatch consumes each component exactly once.
- A kit with a sold-out component is "Sold out".

---

## F — Customer support queries

**Goal.** A customer can report a problem (damaged, leaking, anything else), optionally with
photos, and the owner answers from the admin area.

**Schema.** New app `support`:

- `Query`: user nullable, email, phone_e164, order nullable, subject, status OPEN / ANSWERED / CLOSED, timestamps.
- `QueryMessage`: author CUSTOMER / OWNER, body.
- `QueryPhoto`: image, max 3 per message, type and size checked.

`support/tests` is added to `pytest.ini` testpaths (CLAUDE.md trap).

**Work.**

- "Get help" on the contact page and "Report a problem" on each order.
- Signed-in customers see their threads. Guests reach a thread through a signed link sent to
  the order's email (the same pattern as the G3 account link), or by order id + email.
- Owner inbox with unread count; reply, close; audited.
- Emails go through `core.jobs` when a provider is configured; the thread works without email.
- Throttle scope `support`.

**Files touched.** `backend/support/*` (new app), `backend/backend/settings.py`, `api/urls.py`,
`pytest.ini`, `store/emails.py`; `frontend/src/views/support/*` (new),
`views/owner/OwnerSupport.jsx` (new), `views/customer/OrderDetail.jsx`,
`views/policy/Contact.jsx`, `policies.js`, `Sidebar.jsx`, `App.jsx`, `e2e/support.spec.js` (new).

**Acceptance.**

- A customer can't read another customer's thread (403).
- A guest link only opens its own thread and expires.
- A photo that isn't an image is refused.
- An owner reply marks the thread ANSWERED and appears to the customer.

**Stop and ask.** The grievance-officer wording (L4).

---

## Ranked for later (not scheduled)

1. Ingredient search (search also matches the B `ingredients` field). Small, after B.
2. "Pairs well with": owner-set links between products.
3. Opt-in "running low?" reorder reminder from pack size and order date (needs an email provider).
4. WhatsApp order updates (reuses Noore's deferred Meta Cloud API plan).
5. Weight-based shipping for oils and liquids (`weight_grams` already exists).
6. Ingredient glossary page.
7. Stored "free from" / allergen flags, each one an owner-entered fact.

Pushed back:
- The routine quiz and reviews filtered by skin or hair type both need the filter attributes
  you dropped in Y5. Revisit if those come back.
- "Clinically proven" or "dermatologist" badges need evidence fields and a professional's
  sign-off.
- Before/after imagery: never.
