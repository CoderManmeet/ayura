# BUILD LOG

Ayura (forked from the Noore Candles store on 11 Oct 2026): a single-brand D2C store built on the
Django + React ecommerce codebase. Newest phase first. Every phase ends with the ten sections
required by CLAUDE.md.

---

## Ayura fork: decisions (11 Oct 2026)

On 11 Oct 2026 the owner forked this store into **Ayura**, a separate brand selling home-made
skin, hair and body care. Noore keeps running from its own repository, unchanged. Everything in
this log below this point is Noore's history and stays as it was written. The full Ayura plan,
the owner's answers (Y1-Y20), the defaults taken (Z1-Z9) and the legal questions (L1-L7) are in
`docs/ROADMAP.md`.

| # | Question | Decision | Why | Cost to reverse |
|---|---|---|---|---|
| K1 | Theme names | Brand-neutral: `theme/brand.css` (was `noore.css`), `views/ui/kit.jsx` (was `noore.jsx`), `.ui-*` classes (were `.noore-*`), colour tokens named by role (`canvas`, `panel`, `soft`, `muted`, `subtle`, `accent`) instead of by colour (`cream`, `sand`, `linen`, `oat`, `stone`, `clay`), `font-display` / `font-body` (were `font-serif` / `font-sans`). **Approved in writing by the owner, 11 Oct 2026** (rule 4: a component file is renamed) | A third brand then changes one file | Medium (a rename back) |
| K2 | Typefaces | Bundled npm `@fontsource` packages, loaded from `src/theme/brand-fonts.js`. Never `@import`ed from CSS: Tailwind inlines the import and leaves the font files' relative URLs pointing at the wrong folder (found while building; the fonts 404'd) | No font service request, no tracking | Low |
| K3 | Small labels | The repeated inline "tiny uppercase tracked" pattern became one class, `.ui-caption`, whose case, size and spacing are set in the theme | The look of every label is a theme decision, not a component one | Low |
| K4 | `index.html` brand values | Filled at build time by a small Vite plugin (`brand-html` in `vite.config.js`): title and description from `VITE_STORE_NAME` / `VITE_STORE_DESCRIPTION`, theme-color from `--color-canvas` in `brand.css`, API preconnect worked out from `VITE_API_BASE_URL` | Noore's file hard-coded its own API address and colour | Low |
| K5 | "Net weight" row on the product page | **Removed from the page** (the `weight_grams` field stays): the seeded sizes are millilitres, and showing a shipping weight as a net quantity would be a false label. Phase B adds a real net quantity with a unit | Legal Metrology territory (L3); never show a number that is not the declared one | One line |
| K6 | Candle-only database fields | None exist. Candle facts lived only in seed data and copy, so **no removal migration was needed** | Audited in Step 0 | n/a |
| K7 | Seed catalogue | `seed_ayura`: 3 categories, 8 placeholder products, 15 sizes, stock with best-before dates, `WELCOME10`, simple drawn placeholder pictures (Pillow) unless `--no-pictures`. A banned-claim word list is enforced by a test. `seed_noore` stays in the repository (rule 4; removal proposal) | Playwright and local development need a personal-care catalogue | Low |
| K8 | `keep-awake.yml` default address | Removed. Without the `API_BASE_URL` variable it says so and does nothing | A copied workflow pinged Noore's backend by default | Low |
| K9 | `render.yaml` build command | `bash build.sh` (was `./build.sh`) | `build.sh` is committed without the executable bit, so `./build.sh` fails on a fresh Render build | One line |
| K10 | `backend/static/` | Kept in git with `.gitkeep` | Git does not track empty folders, so a fresh clone had no `static/`, and `check --deploy` (and `test_django_deployment_check_passes_with_production_settings`) failed. Noore has the same latent problem | Delete one file |
| K11 | Django admin (/admin/) branding | Jazzmin titles read `STORE_NAME` (were the course author's "Desphixs" and "Modern Marketplace") | No marketplace wording anywhere | Low |
| K12 | Shop name in `seed_e2e` | `settings.STORE_NAME` | No old brand in test data the browser shows | Low |
| K13 | Noore docs | Moved, unchanged, to `docs/archive/ROADMAP-noore-v2.md` and `docs/archive/DEPLOY-FREE-noore.md`. `docs/DEPLOY.md` (paid server) renamed to Ayura paths and names | One roadmap and one free-deploy guide per repository | Low |
| K15 | Palette | **Option 2, "Turmeric"**, chosen by the owner on 11 Oct 2026 from three screenshotted options: off-white canvas, turmeric-yellow panels, deep green ink, Bricolage Grotesque for everything. The ink was set to the logo's own green (`#2b4732`) | Owner's choice | Edit the BRAND block |
| K16 | Logo | The owner's logo image (1024 px PNG on a cream background) was cut into transparent files in `frontend/public/brand/`: `logo-wordmark.png` (header), `logo-full.png` (footer), `logo-mark.png` (icons). A small four-point sparkle in the bottom-right corner, which looks like an image generator's watermark, was left out. Icons: `favicon.svg` (the mark embedded), `favicon.png`, `apple-touch-icon.png` | The header needs the word alone at small sizes; the stacked logo is unreadable at 24 px | Replace the files (same names) |
| K17 | Logo on yellow | Never. The logo's gold drop disappears on the panel yellow; it is only placed on the canvas and soft colours (noted in the theme file and `public/brand/README.md`) | Seen in the preview | n/a |
| K14 | `backups/` | Added to `.gitignore`. `backups/db-20261004-130927.sqlite3` is **still tracked** (it was committed in 435cbd8); it holds only the course demo data (one demo account, one demo order). Removing it from the repository is a removal proposal; purging it from history would be a history rewrite (CLAUDE.md section 5) and is not proposed | CLAUDE.md says backups are git-ignored; they were not | n/a |

---

## Phase F decisions (13 Oct 2026)

The grievance-officer wording was a stop-and-ask (ROADMAP L4). **Asked and answered by the owner
on 13 Oct 2026: owner-entered fields, shown only when filled.** No legal wording is written by
this codebase; see F13.

| # | Question | Decision | Why | Cost to reverse |
|---|---|---|---|---|
| F1 | How a thread is addressed | By a random 10-character `ref` (lower-case letters, like an order's `oid`), never by its database id | It is printed in emails and read out over the phone; a sequential id would let anyone count the store's complaints | n/a |
| F2 | Is the reference itself access? | **No.** The ref identifies a thread; reading one needs an account that owns it, a signed link, or staff. A bare ref gets 403 | It is shown in emails and support chat and is not secret. Proven by a test and in the e2e suite | n/a |
| F3 | A missing thread vs someone else's | **Identical 403 and identical body.** Probing cannot discover which references exist | Otherwise the endpoint is an oracle for how many queries the store has | One branch |
| F4 | How a guest gets back in | A signed, time-limited token naming ONE query (`django.core.signing`, the G3 account-link pattern), shown on screen as soon as they send and emailed as well | A guest has no account to sign in to. Showing it on screen means a thread survives the email never arriving | Low |
| F5 | Is the reference in the guest's link? | **No.** The link is `/support/thread?token=...` with no ref in it, and a separate endpoint resolves the token server-side | A link with a reference in it invites editing that reference. With none there, there is nothing to tamper with except the signature | One endpoint |
| F6 | Link lifetime | `SUPPORT_LINK_HOURS`, default **720 (30 days)** | Long enough for a damaged parcel to be sorted out; short enough that an old forwarded email stops opening the thread | One default |
| F7 | A guest who lost the link | Order number **plus** the email on that order returns it. The answer is the same whichever half is wrong | The same bar as the existing guest order page (orders are addressable by their random oid), with the order's email on top. The identical answer stops it being used to test whether an address shops here | Low |
| F8 | Who may read a thread | Its account (matched by user, or by the account's email for a thread opened as a guest before the account existed), a valid link, or staff. **Another signed-in customer gets 403** | Roadmap acceptance line. Proven load-bearing by removing the check: 2 tests fail | One function |
| F9 | Are photos really photos? | The bytes are opened and verified with Pillow. The file's name and the content type the browser claims are **never** trusted, and a refused upload stores **nothing** — not a row, not a file, not the thread | A PDF renamed `.png` arrives with `image/png` because the browser guesses from the extension. Caught while writing the e2e test, which is exactly how an attacker would send it | One function |
| F10 | Photo limits | 3 per message, 5 MB each (`SUPPORT_MAX_PHOTOS_PER_MESSAGE`, `SUPPORT_PHOTO_MAX_MB`). Checked in the browser **and** on the server | The browser check saves the customer a wasted upload; the server check is the gate. The shipped defaults are proven by a test run in a clean interpreter | Two defaults |
| F11 | Messages append-only | `QueryMessage` subclasses `core.models.AppendOnlyModel`; the Django admin shows it read-only | What the store told a customer is a record. It is never edited or quietly removed | A base class |
| F12 | Closing a thread | Never the last word: a customer who writes back **reopens** it, and it returns to the inbox with `owner_unread` set | A closed-but-unsolved problem would otherwise vanish. Confirms with an audit row whose reason says "reopened a closed query" | Low |
| F13 | Grievance officer (L4) | Six **owner-entered** fields on `addon.ConfigSettings`, all blank on a fresh install. The Contact page renders the block **only once a name is filled in**, and only the fields she filled. This codebase writes no grievance wording at all | A legal statement is a stop condition (CLAUDE.md §7). Blank-by-default means nothing is ever published on the owner's behalf; the heading "Grievance officer" is the only text this repository contributes | Six columns |
| F14 | Is email required for support to work? | **No.** Email is queued through `core.jobs` after the thread exists, so a store with no provider configured still has a working inbox. Proven by a test that makes every send fail and then answers the thread anyway | Free hosting may have no mail provider for a while; a customer must never lose a report to a mail-server error | n/a |
| F15 | What goes in an email | The reference, the subject and the link. **Not the message bodies** | The conversation lives in the admin area. Copying a customer's words into a third-party mail provider's logs is not needed for them to click through | Low |
| F16 | Telling the owner by email | Only when `SUPPORT_NOTIFY_EMAILS` is set; blank by default sends nothing | The inbox with its unread badge is the system of record. A default address would be a guess | One setting |
| F17 | Unread tracking | **Two independent flags** (`owner_unread`, `customer_unread`), not one "last read by" | One flag means the owner opening a thread clears the customer's badge, and the reverse. Reading is not audited: it is not a state change | Two columns |
| F18 | Throttle scope | New `support` scope, default **20/min**, on every customer-facing support endpoint. The owner's screens sit under the ordinary signed-in limit | Opening a thread is public by necessity and carries file uploads. A test asserts each view names the scope, because one that forgot would silently fall back to the far looser anonymous limit | One setting |
| F19 | Where the `support` app sits | A new Django app, with `support/tests` added to `pytest.ini` testpaths | CLAUDE.md §2 trap: a test file in a new app is silently not collected until its directory is listed. Shown: at `31e5d5d` the suite collects 275 tests and never looks at `support/` | One line |
| F20 | FormData and the shared Axios instance | Every support upload passes `Content-Type: multipart/form-data` per request | The shared instance sets `application/json` for all requests, which strips the multipart boundary and makes files vanish **silently**. Found by the e2e test; every existing upload in this project passes the header the same way | One constant |

---

## PHASE F follow-up — a shipped-default test that was reading the local .env (13 Oct 2026)

Reported by the owner right after applying Phase F: `python -m pytest -q` gave
**1 failed, 324 passed, 4 skipped**, with
`tests/test_dispatch_samples.py::test_the_shipped_shelf_life_default_is_zero_days` asserting
`'30' == '0'`.

**Two separate things, one symptom.**

1. **The owner's `backend/.env` still had `MIN_SHELF_LIFE_ON_DISPATCH_DAYS=30`**, the Phase C
   value. APPLY-PHASE-D.md section 4 asked for it to be set to 0 and it was missed. This is not
   only a test failure: with 30 in force the store holds back any batch with under a month of
   shelf life left, which is not the behaviour ROADMAP Z1 settles on. Fixed by the owner setting
   it to 0 (or deleting the line).

2. **The test could never have done what it claimed.** Its docstring said it read the setting
   "in a fresh interpreter with the variable unset, so a value in anyone's own .env cannot hide
   a change to the default the store ships with". It did run a subprocess with the variable
   removed — but `environs.Env.read_env()` searches upward from **settings.py's own directory**,
   not the working directory, so `backend/.env` was always found and loaded anyway. The test was
   reading the local value the whole time. It passed on the build machine only because that
   `.env` happened to say 0.

**The fix.** `backend/settings.py` now honours `DJANGO_ENV_FILE`: named, it loads that file
instead (no upward search); pointed at a path that does not exist, it loads **no** env file and
every value falls back to the default written in the code. A new session-scoped
`shipped_setting` fixture in `conftest.py` uses that to read any setting as a fresh install has
it, supplying its own `DJANGO_SECRET_KEY` because the `.env` that normally provides one is
deliberately not loaded.

The same latent flaw was in Phase F's own
`test_the_shipped_photo_limits_are_three_and_five_mb`, which passed only because no `.env` in
play happened to set the `SUPPORT_*` variables. It now uses the fixture too, and also checks
the shipped `support` throttle rate.

**Files modified**

- `backend/backend/settings.py` — `DJANGO_ENV_FILE` support (additive; unset behaves exactly as before).
- `backend/conftest.py` — the `shipped_setting` fixture.
- `backend/tests/test_dispatch_samples.py` — the shelf-life test now really isolates `.env`,
  plus `test_a_local_env_file_cannot_disguise_a_shipped_default`, which proves the isolation
  itself works (set the variable and the subprocess reports it; unset it and the shipped 0 comes
  back). Without that, the first test could quietly regress to reading `.env` again.
- `backend/support/tests/test_support.py` — `test_the_shipped_photo_and_link_limits` rewritten
  on the fixture.
- `backend/.env.example` — `DJANGO_ENV_FILE` documented, commented out.

**Verified**

- Reproduced the owner's failure exactly by setting the build machine's own `.env` to 30.
- With `.env` **still at 30**, the whole suite passes: **326 passed, 4 skipped**. That is the
  real check — no test anywhere now depends on the local `.env` value.
- The new isolation proven load-bearing by changing the shipped default in `settings.py` to 30:
  both tests fail, and pass again when it is restored.
- `.env` back at 0: **326 passed, 4 skipped** (SQLite), **330 passed** (PostgreSQL 16),
  `npm run build` succeeds, `npx playwright test` **34 passed**.

No migration. No behaviour change for any customer: the only runtime change is that a setting
may now be read from a file named by `DJANGO_ENV_FILE`, and nothing sets that in production.

---

## PHASE F — Customer support queries (COMPLETED)

### 1. PHASE COMPLETED

**Phase F**, branch `phase/F-support`, built on Phase E `31e5d5d`.

- **A customer can report a problem**, with photos, from the Contact page ("Get help") or from
  an order ("Report a problem with this order"). They get a reference and a conversation both
  sides can read, rather than an email that may or may not be answered.
- **No account needed.** A guest is handed a signed link to their own thread, on screen and by
  email. That link opens that one conversation and nothing else, and expires after 30 days.
  Lost it? The order number plus the email they ordered with gives it back.
- **A signed-in customer** sees every thread under "My conversations", including ones they
  opened as a guest with the same email before the account existed.
- **The owner answers from the admin area.** A new **Support** screen with an unread count in
  the sidebar: the inbox, the whole conversation with the customer's photos, reply, reply and
  close, close without replying, reopen. Every change is audited.
- **Closing is not the last word**: a customer who writes back reopens the thread.
- **Email is a courtesy, never a dependency**: the thread works with no provider configured.
- **The grievance-officer block (L4) publishes nothing.** Six fields the owner types herself,
  blank on a fresh install, shown on the Contact page only once she has filled the name in.
- **Nothing is deleted or renamed.** One new app, one new table group, six new nullable
  columns on the settings row, nine new endpoints.

### 2. FILES CREATED

Backend, the new `support` app:

- `backend/support/__init__.py`, `backend/support/apps.py`
- `backend/support/models.py` — `Query`, `QueryMessage` (append-only), `QueryPhoto`
- `backend/support/services.py` — every write to a thread, and the photo checks
- `backend/support/links.py` — the signed guest link
- `backend/support/emails.py` — the two background email jobs
- `backend/support/serializers.py` — the customer's view and the owner's view
- `backend/support/views.py` — the customer-facing endpoints
- `backend/support/owner_views.py` — the owner's inbox
- `backend/support/admin.py` — the Django admin fallback, messages read-only
- `backend/support/migrations/__init__.py`, `backend/support/migrations/0001_initial.py`
- `backend/support/tests/__init__.py`, `backend/support/tests/test_support.py` — 54 tests
- `backend/addon/migrations/0008_grievance_officer.py`
- `backend/templates/email/support_update.txt`, `backend/templates/email/support_update.html`

Frontend:

- `frontend/src/views/support/supportApi.js` — the one place the three ways into a thread live
- `frontend/src/views/support/PhotoPicker.jsx`
- `frontend/src/views/support/NewQuery.jsx` — "Get help"
- `frontend/src/views/support/Thread.jsx` — one conversation, by account or by link
- `frontend/src/views/support/MyQueries.jsx`
- `frontend/src/views/support/FindThread.jsx`
- `frontend/src/views/owner/OwnerSupport.jsx` — the inbox and one thread
- `frontend/src/views/policy/GrievanceOfficer.jsx` — renders nothing until the owner fills it in
- `frontend/e2e/support.spec.js` — 3 Playwright tests

### 3. FILES MODIFIED

- `backend/backend/settings.py` — `support` in `INSTALLED_APPS`; the `support` throttle rate;
  `SUPPORT_LINK_HOURS`, `SUPPORT_MAX_PHOTOS_PER_MESSAGE`, `SUPPORT_PHOTO_MAX_MB`,
  `SUPPORT_NOTIFY_EMAILS`.
- `backend/pytest.ini` — `support/tests` added to `testpaths` (F19).
- `backend/api/urls.py` — the nine new routes.
- `backend/addon/models.py` — the six owner-entered grievance fields, blank by default (F13).
- `backend/store/owner_settings.py` — those fields on GET and PATCH, audited; the new
  `COUNTS` handling for `grievance_response_days`.
- `backend/.env.example` — `THROTTLE_SUPPORT` and the four `SUPPORT_*` variables.
- `frontend/src/App.jsx` — five lazy routes (`/support/new`, `/support/find`,
  `/support/thread`, `/support/thread/:ref`, `/support/mine`) and two admin-area ones.
- `frontend/src/views/vendor/Sidebar.jsx` — **Support** in the daily group, with the unread badge.
- `frontend/src/views/policy/Contact.jsx` — the "Get help" panel and the grievance block.
- `frontend/src/views/customer/OrderDetail.jsx` — "Report a problem with this order", and the
  threads already opened about it.
- `frontend/src/views/owner/OwnerSettings.jsx` — the grievance-officer card.
- `frontend/playwright.config.js` — `support.spec.js` added to `testMatch`.
- `docs/BUILD_LOG.md` — this section.

New endpoints:

| Method | Path | Access | What |
|---|---|---|---|
| POST | `support/queries/` | anyone | start a thread (multipart with photos, or JSON) |
| GET | `support/queries/mine/` | signed in | my own threads |
| GET/POST | `support/queries/<ref>/` | its account, or staff | read one thread / reply |
| GET/POST | `support/thread/?token=` | a valid signed link | read / reply by link alone (F5) |
| POST | `support/find/` | anyone | order number + email → the link back |
| GET | `support/orders/<oid>/queries/` | the order's customer | threads about one order |
| GET | `owner/support/` | staff | the inbox and the counts |
| GET/POST | `owner/support/<ref>/` | staff | read (clears unread) / reply |
| POST | `owner/support/<ref>/close/` | staff | close or reopen |

Audited actions: `support.query_opened`, `support.customer_replied`, `support.owner_replied`,
`support.closed`, `support.reopened`, and `settings.updated` for the grievance fields — each
with actor, before and after (rule 9).

### 4. MIGRATIONS ADDED

| Migration | What | Reverse |
|---|---|---|
| `addon.0008_grievance_officer` | six grievance fields on the settings row, all blank / 0 | drops the six columns |
| `support.0001_initial` | `Query`, `QueryMessage`, `QueryPhoto` and the status index | drops the three tables |

Back up first, then `python manage.py migrate`. Roll back Phase F only, **in this order**
(`support.0001` references `store.CartOrder`, which is untouched):

    python manage.py migrate support zero
    python manage.py migrate addon 0007

Verified on a copy of the database: apply, roll back both, re-apply, all clean;
`makemigrations --check` reports no changes. Note that rolling back drops the conversations;
photo **files** already uploaded stay on disk (or in Cloudinary) and would have to be removed
by hand.

### 5. ENV VARS ADDED

All optional, all with working defaults; documented in `backend/.env.example`:

| Variable | Default | What |
|---|---|---|
| `THROTTLE_SUPPORT` | `20/min` | opening and replying to a thread, including uploads |
| `SUPPORT_LINK_HOURS` | `720` | how long a guest's signed link keeps working (F6) |
| `SUPPORT_MAX_PHOTOS_PER_MESSAGE` | `3` | photos per message |
| `SUPPORT_PHOTO_MAX_MB` | `5` | size of each photo |
| `SUPPORT_NOTIFY_EMAILS` | *(blank)* | who is emailed when a query comes in; blank sends nothing (F16) |

Nothing existing changed. No secret is involved.

### 6. TESTS ADDED

`backend/support/tests/test_support.py`, 54 tests:

- **Opening a thread.** A guest gets a thread and their own signed link; a signed-in customer
  gets one on their account with the account's email and no link; a thread can be about an
  order and takes the phone off it; a thread cannot be attached to someone else's order (403)
  or to an order that does not exist, and neither attempt creates anything; an empty subject,
  body or email is refused with a usable message and creates nothing; opening is audited.
- **Photos.** Real pictures are stored with the message; a PDF wearing an image name and
  content type is refused and **nothing** is stored; one bad photo refuses the whole message,
  including the good one next to it; more than three is refused; over the size limit is
  refused; an empty file is refused; the shipped limits (3, 5 MB, 720 h, no notify address) are
  read in a clean interpreter so no local `.env` can hide a change to them.
- **Who may read a thread.** A customer cannot read or write on another customer's thread
  (403); the reference alone opens nothing; a missing thread and someone else's answer
  identically; staff may read any; a guest thread opened with an account's email belongs to
  that account; "my threads" lists only my own and needs an account.
- **The guest link.** It opens its own thread; it opens **no other** thread; it expires; a
  tampered token is refused; a guest can reply on it; order number + email returns the link,
  with the right email required and the same answer whichever half is wrong.
- **The owner answers.** A reply marks the thread ANSWERED, the customer sees it and reading it
  clears their badge; the reply records which staff user wrote it and is audited; she can close
  as she replies; a customer writing back **reopens** a closed thread and it returns to the
  inbox; close and reopen without replying, with closing twice writing no second audit row; an
  empty reply is refused.
- **The inbox.** The counts separate open / answered / closed / unread; the default view hides
  closed threads and puts unread first; opening a thread clears its unread flag; the row shows
  who is asking and about which order; every owner endpoint is staff-only and a customer's
  attempts write nothing.
- **Messages are a record.** Append-only: editing or deleting raises.
- **Email is a courtesy.** One acknowledgement per thread and exactly one notice per reply,
  each with its own dedupe key; the owner is told only when an address is configured; with
  every send failing the thread still exists and is still answerable; the email carries the
  reference and a signed link that resolves to that thread, and **no message text**.
- **The throttle.** Every customer-facing view names the `support` scope and the configured
  rate is `20/min`; the limit really bites (3 allowed, then 429) and the refused requests
  create nothing.
- **Grievance officer (L4).** Every field ships blank and `grievance_response_days` is 0; the
  owner sets them and the change is audited with before and after; they are public once set;
  a customer cannot set them (403).

Shown failing first against `31e5d5d`: collection error
(`ImportError: cannot import name 'links' from 'support' (unknown location)`), and at that
commit the suite collects **275 tests** and never looks in `support/` at all (F19). The access
checks (F8, F5) were additionally proven load-bearing by removing them — 3 tests then fail,
including both "another customer" tests and "a guest link opens no other thread" — and
restoring them.

    python -m pytest support/tests/test_support.py -q  ->  54 passed
    python -m pytest -q                               ->  325 passed, 4 skipped (SQLite)
    $env:DATABASE_URL = "postgres://ecom:ecom@127.0.0.1:5432/ecom"
    python -m pytest -q                               ->  329 passed (PostgreSQL 16)

Playwright, `frontend/e2e/support.spec.js`, 3 tests: a signed-in customer orders, reports the
order damaged from the order page, has an honestly-named PDF refused in the browser and a PDF
renamed `.png` refused by the server (nothing stored either time), sends a real photo, and sees
the order page switch to "Report something else"; the owner sees the unread badge count 1, opens
the thread with the photo, cannot send an empty reply, answers, and the badge clears; the
customer sees "New reply", reads it, writes back and the thread returns to "Waiting for us". A
guest reports a problem from the Contact page with no account, gets a link, opens it, adds to
the thread, and finds that the bare reference and a tampered token open nothing; the owner sees
it marked "(guest)" and closes it with a reply; the guest writes back and it reopens. The
grievance block is absent from the Contact page, the owner fills in four of the six fields, and
it appears with her own words and no empty row for the address she left blank.

    npm run build          ->  built
    npx playwright test    ->  34 passed

### 7. MANUAL VERIFICATION STEPS

Back up, migrate (section 4), `python -m pytest -q`, `npm run build`, run both servers and the
worker (`python manage.py run_worker`), then:

1. **As a shopper**: Contact → **Get help**. Report something, attach a photo, send. You get a
   reference. Signed out, you also get a link on screen — open it in a private window and the
   conversation is there.
2. Paste that link with the last few characters changed: it opens nothing. Visit
   `/support/thread/<the reference>` with no token: it opens nothing either.
3. **As the owner**: Admin area → **Support** (sidebar, with a count). Open the thread: the
   photo is there, full size on click. Reply. The status becomes Answered and the count clears.
4. **As the shopper** again: "My conversations" (or the guest link) shows the reply. Write back:
   the thread goes back to "Waiting for us" and reappears in the owner's inbox.
5. Close a thread as the owner, then write back as the customer: it reopens.
6. Try to attach a renamed file (copy a PDF to `photo.png`): refused, with the reason, and the
   message is not sent.
7. Open someone else's conversation: sign in as a different customer and visit
   `/support/thread/<their reference>` — "We cannot open that conversation."
8. **Grievance officer**: Admin area → Store settings → Grievance officer. The Contact page has
   no such block until you fill in a name. Fill one in and only the fields you typed appear.
9. Django admin → Support → Queries: the conversation is there and its messages cannot be edited.

### 8. ASSUMPTIONS MADE (exhaustive)

1. Decisions F1-F20.
2. A customer picks a reason from a fixed list, and the subject defaults to that reason when
   they type none. The list is storefront copy, not stored data.
3. A message body is capped at 4,000 characters and a subject at 200.
4. Photos go on a customer's message. The owner may attach them too (the service accepts them);
   her screen has no picker yet.
5. Photos are stored under `support/<ref>/` in whatever storage the store already uses
   (Cloudinary when configured, the local media folder otherwise).
6. A thread is attached to at most one order. A problem spanning two orders is two threads.
7. A guest thread is matched to an account by email only when the thread has no user and the
   addresses match exactly (lower-cased), the same rule as the G3 account link.
8. "My conversations" and the inbox are unpaged; at this size that is a handful of queries.
9. The sidebar's unread count is read when the admin area navigates, not pushed live.
10. The owner's reply is plain text. No formatting, no templates, no canned replies.
11. Reading a thread is not audited: it changes no state. Who answered is recorded on the
    message and in the audit row.
12. `support.0001_initial` references `store.CartOrder` with `SET_NULL`, so a deleted order
    (which the store does not do) would leave the conversation intact.
13. Email failures retry on the job runner's own backoff; after `JOB_MAX_ATTEMPTS` the job is
    DEAD and the thread is unaffected.

### 9. KNOWN GAPS

- **No canned replies or templates** for the owner; every answer is typed.
- No search in the owner's inbox, and no filter by customer or order — only by status.
- The owner cannot attach a photo from her screen (the service supports it; the UI does not).
- No "assigned to" or internal notes: one owner, one inbox.
- A customer cannot close their own thread; they can stop replying, and the owner closes it.
- No WhatsApp route into a thread. Phase F is email and the web only; the Cloud API is still
  deferred.
- The customer's email is not verified when a guest opens a thread, so a mistyped address means
  the acknowledgement bounces. The on-screen link is the mitigation (F4).
- No attachment virus scanning beyond "is it really an image".
- Photos are never deleted, including when a thread is rolled back out of the database.
- The unread count is per store, not per staff user; a second staff member sees the same badge.
- `SUPPORT_LINK_HOURS` cannot be changed from the Store settings screen, only in the environment.
- The Contact page's grievance block is the only place those details appear; they are not in the
  policy pages or in emails.

### 10. NOT DONE AND WHY

- **The grievance-officer wording itself**: a legal interpretation, and a stop condition
  (CLAUDE.md §7). The fields are the owner's to fill; L4 is still open in the roadmap.
- Returns and refunds as a *process* (approve a return, issue a refund): not in Phase F, which
  is the conversation only. The owner refunds through Razorpay's dashboard as before.
- WhatsApp Cloud API inbound messages: deferred with the rest of that integration.
- Automatic expiry emails to the owner: still waiting on the email-provider decision from
  G5 part B, as in Phase D.
- Phase F is the last phase in the roadmap. What is ranked for later is listed under
  "Ranked for later (not scheduled)" in `docs/ROADMAP.md`.

---

## Phase E decisions (13 Oct 2026)

| # | Question | Decision | Why | Cost to reverse |
|---|---|---|---|---|
| E1 | Where a kit's stock lives | Nowhere. A kit variant has **no ledger rows of its own**: `available_qty` for a kit is `min(component available // qty)`, and booking a batch against a kit is refused by `owner/variants/<id>/stock/` | Two numbers for one thing always drift. The ledger stays the single source | One branch in `available_qty` |
| E2 | What a kit's reservation looks like | The **components** are reserved, each hold tagged with `StockReservation.kit_variant`. The kit itself is never reserved (`reserve` raises `InvalidMovement` for a kit) | Dispatch, cancellation and expiry then need no kit-specific code: they already follow reservations | A column |
| E3 | Order of component locks | `reserve_kit` takes its parts **ordered by `component_variant_id`**, always | Two shoppers buying overlapping kits would otherwise take the same two row locks in opposite orders and deadlock | One `order_by` |
| E4 | What the shopper is told when a kit is short | `InsufficientStock` is re-raised naming the **kit** and how many kits are possible, never the component | "Only 2 left" about a serum the shopper never asked for is confusing, and it leaks which parts are scarce | Low |
| E5 | Partial kits | Never. `reserve_kit` is one transaction: if any component is short, **nothing** is held | Half a kit is not a product. A stray hold on the cleanser would quietly block someone else's order | n/a |
| E6 | Releasing one cart line | `release_cart_line(cart_id, variant)` is kit-aware in both directions: dropping the kit releases only holds tagged with that kit; dropping a plain line of the same size releases only holds **not** tagged with a kit (`kit_variant__isnull=True`) | The same size is often in the bag twice — alone and inside a kit. Proven load-bearing by removing the filter (a test then sees 8 where 7 is right) | One filter |
| E7 | Which order line a component hold belongs to | The **kit's** line. `attach_reservations_to_order` maps `reservation.kit_variant_id or reservation.variant_id` to the order item | The order has one line (the kit) at one price; the packing screen then shows the batches under that line | One expression |
| E8 | Re-reserving after a late payment | `hold_for_order` measures a kit line in **kits** (`_held_for_item`: the scarcest component's held quantity divided by its per-kit quantity) and re-reserves the missing kits with `reserve_kit` | Counting raw units would see 3 holds for a 1-kit line and think nothing was missing | Low |
| E9 | A kit's price | The owner's, on the kit size itself. **Never** summed from the components (ROADMAP Z7). The Kits screen shows what the parts come to separately, labelled as such, for the owner only | A kit is usually cheaper than its parts; that is the offer. A computed price would also move whenever a component's price moved | n/a |
| E10 | Can a kit be the product's main size? | Only when it is the product's **only** size (a gift-set product). It never takes over the "Default" placeholder, which may be holding the opening stock typed when the product was made | Adopting a stocked placeholder would strand those units behind a variant that cannot hold stock | Low |
| E11 | Kit inside a kit, sample inside a kit | Both refused, at three levels: a database `CheckConstraint` for a kit containing **itself**, a `UniqueConstraint` for the same part twice, and `store/owner_kits.py` for a kit or a sample as a part (ROADMAP Z7) | Nested kits make availability recursive and the owner's arithmetic unguessable; a sample is a gift, not stock sold in a box | n/a |
| E12 | Kit and sample on one size | Mutually exclusive, server-side (`_apply_variant_fields`) and in the form (each tick disables the other) | A zero-priced giveaway made of real stock is neither one thing nor the other | One check |
| E13 | What the shopper sees inside a kit | Product, size name and net quantity, in the owner's order. **No component prices** (`kit_contents` has no price field at all) | A bill of materials invites arithmetic the kit's price does not follow. "What's inside" is shown **before** the Add to bag button (section 8: no drip pricing) | Low |
| E14 | `available_qty_map` and kits | Still a fixed number of queries: kit ids and their components are fetched in two extra queries, then the kits are derived from the component figures already read | A listing page with kits would otherwise fall back to per-component queries | Low |
| E15 | Expired component stock | A kit whose parts are all expired **counts** as on hand but cannot be reserved, exactly as an ordinary size does (ROADMAP Z1) | One rule for allocation, not two | n/a |

---

## PHASE E — Kits from component stock (COMPLETED)

### 1. PHASE COMPLETED

**Phase E**, branch `phase/E-kits`, built on Phase D `d348ce5`.

- **A kit is a size made of other sizes.** Tick **Kit** on a size on the product's
  "Sizes & stock" screen, give it the price you want to charge, then say what goes inside it on
  the new **Kits** screen. A kit keeps **no stock of its own**: how many you can sell is
  decided by the scarcest thing inside it, and the Kits screen says which part that is.
- **Buying one holds every part, all or nothing.** Adding a kit to the bag reserves each
  component through the stock ledger in FEFO order, in one transaction. If any part is short,
  nothing is held and the shopper is told how many **kits** are available — never which
  component ran out.
- **Everything downstream already works.** The order has one line (the kit, at the kit's
  price); the packing screen shows the batches under it; dispatch turns each component's hold
  into exactly one `SALE_OUT`; cancelling returns every component; the expiry job and the
  recall lookup need no kit-specific code, because the holds are component holds.
- **The shopper sees what is in the box before committing**: a "What's inside" panel above the
  Add to bag button, listing each part by name and net quantity, with no component prices.
- **Nothing is deleted or renamed.** Two new nullable columns, one new table, one new screen,
  three new endpoints. Customers who never see a kit see no change at all.

### 2. FILES CREATED

- `backend/catalog/migrations/0009_kits.py` — `ProductVariant.is_kit` and the `KitComponent` table.
- `backend/inventory/migrations/0005_reservation_kit.py` — `StockReservation.kit_variant`.
- `backend/store/owner_kits.py` — the three owner endpoints and the kit rules (E11).
- `backend/inventory/tests/test_kits.py` — 34 tests (section 6).
- `frontend/src/views/owner/OwnerKits.jsx` — the kit builder.
- `frontend/e2e/kits.spec.js` — 3 Playwright tests.

### 3. FILES MODIFIED

- `backend/catalog/models.py` — `ProductVariant.is_kit`, `ProductVariant.kit_parts()`, and the
  `KitComponent` model with its unique-pair and not-itself constraints.
- `backend/catalog/admin.py` — a `KitComponent` inline on the variant page; `is_kit` and
  `is_sample` in the list and the filters.
- `backend/inventory/models.py` — `StockReservation.kit_variant` (nullable, `SET_NULL`).
- `backend/inventory/services.py` — `kit_available_qty`; `available_qty` dispatches on
  `is_kit`; `available_qty_map` derives kit figures from the component figures it already read
  (E14); `reserve` gained `kit_variant=` and refuses a kit outright (E2); new `reserve_kit`
  (E3, E4, E5); `release_cart_line` is kit-aware both ways (E6);
  `attach_reservations_to_order` resolves the kit's line (E7); new `_held_for_item` and a
  kit-aware `hold_for_order` (E8).
- `backend/store/views.py` — `put_in_cart` branches to `reserve_kit`; `_release_cart_line`
  delegates to the kit-aware service.
- `backend/store/serializers.py` — `ProductVariantSerializer` gained `is_kit` and
  `kit_contents` (never a price, E13).
- `backend/store/owner_catalogue.py` — `is_kit` on the variant payload, in the audited field
  list and in `_apply_variant_fields` (with E12's mutual exclusion); a kit never takes over the
  placeholder size (E10); `owner/variants/<id>/stock/` refuses a kit (E1).
- `backend/api/urls.py` — the three kit routes.
- `frontend/src/views/owner/OwnerProduct.jsx` — a **Kit** tick on the sizes form (it and
  **Sample** disable each other), a Kit badge on the size row, and a kit's stock panel offers
  no batches, only a note saying where its stock comes from.
- `frontend/src/views/shop/ProductDetail.jsx` — the "What's inside" panel.
- `frontend/src/views/vendor/Sidebar.jsx` — **Kits** in the daily group.
- `frontend/src/App.jsx` — the lazy route `admin-area/owner/kits/`.
- `frontend/playwright.config.js` — `kits.spec.js` added to `testMatch`.
- `docs/BUILD_LOG.md` — this section.

New endpoints, all `IsStaffOwner`:

| Method | Path | What |
|---|---|---|
| GET | `owner/kits/` | every kit, what is in it, what each part allows, and the sizes that may be added |
| POST | `owner/kits/<variant_id>/components/` | `{component_variant_id, qty}` put a part in |
| PATCH | `owner/kit-components/<id>/` | `{qty}` change how many go in |
| DELETE | `owner/kit-components/<id>/` | take the part out |

Each one audits `kit.component_added` / `kit.component_updated` / `kit.component_removed` with
actor, before and after (rule 9).

### 4. MIGRATIONS ADDED

| Migration | What | Reverse |
|---|---|---|
| `catalog.0009_kits` | `ProductVariant.is_kit` (False everywhere) and the `KitComponent` table | drops both |
| `inventory.0005_reservation_kit` | `StockReservation.kit_variant` (null everywhere) | drops the column |

Back up first, then `python manage.py migrate`. Roll back Phase E only, **in this order**
(`inventory.0005` depends on `catalog.0009`):

    python manage.py migrate inventory 0004
    python manage.py migrate catalog 0008

Verified on a copy of the database: apply, roll back both, re-apply, all clean;
`makemigrations --check` reports no changes.

### 5. ENV VARS ADDED

None. No setting changed.

### 6. TESTS ADDED

`backend/inventory/tests/test_kits.py`, 34 tests (2 of them PostgreSQL-only):

- **Availability.** A kit tracks its scarcest component, and follows it down when someone else
  holds stock; a kit needing 3 of a part divides by 3; a kit has no ledger rows of its own; a
  kit with nothing in it yet is sold out; a kit with a sold-out component reports
  `{"state": "sold_out", "label": "Sold out"}` while that component's own size stays in stock;
  an expired component batch counts as on hand but leaves the kit unbuildable (E15);
  `available_qty_map` and `available_qty` agree about kits.
- **Reserving.** Reserving a kit holds every component, tagged with the kit, and never the kit
  itself; one short component holds nothing at all and the error names the kit with the kit's
  own number (E4, E5); the kit variant can never be reserved directly; releasing a kit cart
  line returns every component and leaves a plain line of the same size alone, and the reverse
  (E6); changing the quantity of a kit line replaces the holds instead of stacking them; asking
  for more kits than the scarcest part allows is refused with "Only 3 left" and holds nothing.
- **Order lifecycle.** Checking out puts the component holds on the **kit's** order line (E7);
  cancelling returns every component with nothing physically moved; dispatch writes exactly one
  `SALE_OUT` per component and a second dispatch writes none; paying after the holds lapsed
  re-reserves the whole kit and running it twice does not stack (E8); a paid kit order whose
  component has since gone reports a shortfall of **2 kits** instead of raising.
- **Kit rules.** A kit cannot contain itself (database constraint); the same part cannot be
  listed twice (database constraint); the owner cannot put a kit, a sample or the kit itself
  inside a kit, each with its own message; a size cannot be a kit and a sample at once; stock
  cannot be booked against a kit; adding a kit size never takes over the stocked placeholder
  (E10); the kit's price does not move when a component's price does (E9).
- **What the shopper sees.** The product payload carries `is_kit`, the kit's real availability,
  the honest stock label and `kit_contents` in the owner's order — and **no key containing
  "price"** anywhere in it (E13).
- **Owner kit builder.** Building a kit and seeing `kits_possible` per part and the bottleneck;
  changing a quantity and removing a part, each audited; the same part twice is refused with a
  reason; a part can only be added to a size that is a kit; every endpoint is staff only
  (anonymous 401/403, a customer 403).
- **Concurrency (PostgreSQL only, skipped on SQLite).** Two shoppers racing for the last serum,
  one of them buying it inside a kit: exactly one wins, and the loser leaves no stray cleanser
  hold behind. Two shoppers racing for the last **kit**: exactly one wins and only the winner's
  two holds exist.

Shown failing first against `d348ce5`: collection error
(`ImportError: cannot import name 'KitComponent' from 'catalog.models'`). E6's filter was
additionally proven load-bearing by removing it — the plain-line release test then sees 8 where
7 is right — and restoring it.

    python -m pytest inventory/tests/test_kits.py -q  ->  32 passed, 2 skipped
    python -m pytest -q                              ->  271 passed, 4 skipped (SQLite)
    $env:DATABASE_URL = "postgres://ecom:ecom@127.0.0.1:5432/ecom"
    python -m pytest -q                              ->  275 passed (PostgreSQL 16)

Playwright, `frontend/e2e/kits.spec.js`, 3 tests: the owner adds a "Face routine kit" size with
the **Kit** tick (which disables **Sample**), sees that it has no stock panel of its own, puts
Face Serum 30 ml x1 and Face Scrub 50 g x2 inside it, and watches what the kit can sell follow
the scarcest part as the quantities change; a customer sees "What's inside" with no prices in
it, buys one for Rs 699 by COD, and one serum and two scrubs leave the shelf while the kit's own
stock stays nil — then the owner cancels and every component comes back; a third part that has
never been made is added, the kit goes to 0 and the shop says **Sold out** with the button
disabled, and taking that part out makes it sellable again. Stock figures are read before and
after each step rather than hard-coded, because the earlier specs have already bought and
cancelled things in the same database.

    npm run build          ->  built
    npx playwright test    ->  31 passed

### 7. MANUAL VERIFICATION STEPS

Back up, migrate (section 4), `python -m pytest -q`, `npm run build`, run both servers, then:

1. Admin → Products → **Sizes & stock** on any product. Add a size, tick **Kit**, set the price
   you want to charge, save. It gets a blue **Kit** badge, shows 0 available, and its stock
   panel offers no batches — only a note saying where its stock comes from.
2. Admin → **Kits** (sidebar, "Every day"). The new kit is listed, empty. Add two or three
   sizes to it, with quantities. "Kits it allows" appears per part, and the kit's own figure is
   the smallest of them; the line underneath names the part holding it back.
3. Change a part's quantity to something large and Save: the kit's figure drops immediately and
   no stock anywhere has moved. Put it back.
4. Try to add the kit to itself or a sample to it: refused, with the reason. Adding the same
   part twice: refused.
5. Open the shop → that product → choose the kit size. **What's inside** lists the parts with
   their net quantities and **no prices**, above the Add to bag button. The price shown is the
   one you set.
6. Buy one by COD. Admin → Products → the component products: each part's Available has dropped
   by the kit's quantity. The kit size itself still has no stock of its own.
7. Admin → Orders → open that order. **Packing** shows the batches under the kit's line.
   Cancel the order: every component's Available goes back up.
8. Django admin → Inventory → Stock reservations: the holds are on the components, each with a
   **kit variant** set. Dispatch an order instead of cancelling and the movements are one
   `SALE_OUT` per component, none for the kit.

### 8. ASSUMPTIONS MADE (exhaustive)

1. Decisions E1-E15.
2. A kit's components may come from **other products**, not only the kit's own product; the
   candidate list on the Kits screen is every active, non-kit, non-sample size in the store.
3. A kit's shipping weight is the one typed on the kit size, not the sum of its parts' weights:
   the box is packed differently from the parts.
4. A kit's net quantity is the one typed on the kit size. Nothing adds up its parts, which may
   be in different units (30 ml of serum and 50 g of scrub do not add).
5. A component may be in any number of kits at once; each kit's holds are tagged separately.
6. A component can still be sold on its own; the two compete for the same stock, first come
   first served, which is what the lock is for.
7. A kit may contain a size that is switched off (`active=False`): the Kits screen marks it
   "Not on sale" and it still limits the kit. Removing it is the owner's call.
8. Switching a component off does not switch its kits off; the kit's availability simply
   follows whatever stock that component has.
9. Changing what is in a kit does not touch orders already placed: those hold component
   reservations of their own, taken at the time.
10. A coupon applies to a kit as it does to any line, on the kit's own price.
11. Taking a part out of a kit does not release holds already taken for carts or orders.
12. The parts-bought-separately figure on the Kits screen is read off today's component prices
    and is for the owner's information only; nothing computes with it.

### 9. KNOWN GAPS

- **No "make this kit" helper**: the Kits screen tells you which part is holding a kit back, but
  there is no button to go straight to adding stock to that part.
- No kit builder on the product page itself; kits are edited on the one Kits screen (plus the
  Django admin inline).
- A kit's own line on the packing screen shows its components' batches, with no heading saying
  which batch belongs to which part — it reads as a list.
- `kit_contents` is not shown in the cart, at checkout, on the order page or in the order email;
  only on the product page. A shopper who wants to re-read what is in the box opens the product.
- No kit-level low-stock alert; "Only N left" on a kit is the ordinary threshold applied to the
  derived figure.
- The Kits screen lists every kit at once with no paging or search. At this size that is fine.
- A kit cannot contain a kit (E11), so a "double gift set" has to list all the parts again.
- Nothing stops a kit priced **above** its parts' total; the screen shows both numbers and
  leaves it to the owner.

### 10. NOT DONE AND WHY

- Customer support queries: phase F.
- Nested kits: refused by design (E11), not deferred.
- A printed packing slip listing a kit's parts: not in the roadmap for this phase (it is the
  same gap Phase D left).
- Component-level pricing or automatic kit discounts: ROADMAP Z7 settles the price as the
  owner's own.

---

## Phase D decisions (12 Oct 2026)

| # | Question | Decision | Why | Cost to reverse |
|---|---|---|---|---|
| D1 | A partly-built Phase D was found uncommitted in the build repo | **Reviewed and kept** as the foundation (models, migrations, the SAMPLE_OUT kind, `consume_samples_for_order`, `write_off_batch`, `order_batches`, `orders_from_batch`). It matched the house conventions. It was parked on `wip/phase-D-uncommitted` first, then cherry-picked, reviewed line by line and fixed. It had **no tests**, so every line is covered by the new ones | Redoing correct work wastes a phase; shipping unreviewed work breaks rule 11 | n/a |
| D2 | A gift sample was being booked as a SALE | **Fixed.** `consume_for_order` now excludes sample holds (`sample__isnull=True`). Found while reviewing D1: sample holds carry `order`, so dispatch consumed them first as `SALE_OUT` and `consume_samples_for_order` then found nothing. Proven by removing the fix and watching the test fail | A gift counted as revenue would corrupt every sales figure and the recall lookup | One filter |
| D3 | `sample_decision` would have reached the customer | `CartOrderSerializer` now **excludes** it; `OwnerCartOrderSerializer` adds it back for the owner's screens | ROADMAP Y19: samples are a surprise. The field sat on `CartOrder`, which the customer's own order API serialises with `__all__` | Low |
| D4 | A sample's hold could be handed back by the expiry job | Sample holds are pinned for the same long window as a paid order's (`SAMPLE_HOLD_MINUTES`) | The owner adds a sample to a parcel that may be packed hours later; a 30-minute TTL would silently free the stock | One constant |
| D5 | Can a sample be the main size, or the only size? | No to both: a sample is never `is_default`, never takes over the "Default" placeholder, and cannot be added until the product has a size people can buy | Otherwise a product's price would mirror a zero-priced giveaway | Low |
| D6 | Does batch lookup list only dispatched orders? | It lists **both**: orders that physically received stock (`SALE_OUT` / `SAMPLE_OUT`) and orders still holding it, each marked `dispatched` true or false | In a recall you also need the parcels that have not gone out yet | Low |
| D7 | Writing off stock that is held for an order | Refused, with the number that can be written off. Cancel that order first | Writing off stock that is promised to a customer would oversell | Low |
| D8 | How a customer is recognised for the samples report | Account first, then the email on the order, then the phone. Only orders placed **after** the sample order count, and only a full-size variant of that same product | Y7: measure whether the sample led to a sale. Guests come back without an account | Low |
| D9 | Where the new endpoints live | New `backend/store/owner_dispatch.py`; the dispatch extras are a **separate** endpoint (`owner/orders/<oid>/dispatch/`) rather than new fields on the order payload | The existing order payload and its tests stay untouched | Move the classes |
| D10 | Shelf life | `MIN_SHELF_LIFE_ON_DISPATCH_DAYS` default is now **0** (ROADMAP Z1), proven by a test that reads the setting in a fresh interpreter with the variable unset, so nobody's own `.env` can hide a change to the shipped default | Only an already-expired batch is held back; everything else is a flag, not a block (Y12) | One default |

---

## PHASE D — Dispatch checks, free samples, batch lookup (COMPLETED)

### 1. PHASE COMPLETED

**Phase D**, branch `phase/D-dispatch-samples`, built on Phase C `5a68534`.

- **Packing check on every order.** "Handle orders" now shows which batch each line is going
  out from, with **Expired** and **No use-by date** flags, and the missing date can be typed
  in right there (audited). Nothing is ever blocked (Y12): the flags inform, the owner decides.
- **Gift samples.** A sample is a hidden size of a real product (`is_sample`), created on the
  product's "Sizes & stock" screen with a **Sample** tick. On an order the owner adds samples
  or records "No samples". Adding one holds its stock; dispatch turns that hold into a
  `SAMPLE_OUT` movement **exactly once**, so a gift is never counted as a sale. Cancelling the
  order gives the stock back.
- **The customer is never told** (Y19): no order page, no email and no answer a customer can
  reach mentions a sample, and the order total never changes.
- **Samples report**: per sample, how many orders carried it, how many of those customers came
  back for that product, the conversion percentage, and which orders.
- **Stock & expiry screen**: expired stock still on the shelf, stock due within the alert
  window, and stock with no use-by date. Writing stock off is a `DAMAGE_OUT` movement in the
  ledger, never an edit, and never touches stock held for an order.
- **Batch lookup (recall)**: type a batch code and see every order that received stock from it,
  including parcels not yet sent.
- **Shelf life default is 0** (Z1): only an already-expired batch is held back from allocation.

### 2. FILES CREATED

- `backend/catalog/migrations/0008_productvariant_is_sample.py`
- `backend/inventory/migrations/0003_alter_stockmovement_kind.py`
- `backend/inventory/migrations/0004_reservation_sample.py`
- `backend/store/migrations/0043_order_samples.py`
- `backend/store/samples.py`
- `backend/store/owner_dispatch.py`
- `backend/tests/test_dispatch_samples.py`
- `frontend/src/views/owner/OwnerExpiry.jsx`
- `frontend/src/views/owner/OwnerSamples.jsx`
- `frontend/e2e/owner.spec.js`

### 3. FILES MODIFIED

- Backend: `backend/settings.py` and `.env.example` (shelf-life default 0), `catalog/models.py`
  (`is_sample`, `sellable`), `inventory/models.py` (`SAMPLE_OUT`, `StockReservation.sample`),
  `inventory/services.py` (sample holds, the sale/sample fix, `consume_samples_for_order`,
  `write_off_batch`, `order_batches`, `orders_from_batch`, `undated_batches_with_stock`),
  `store/models.py` (`OrderSample`, `CartOrder.sample_decision`), `store/order_state.py`
  (dispatch also consumes samples), `store/serializers.py` (the customer/owner split),
  `store/views.py` (samples never sellable), `store/owner_views.py` (owner serializer),
  `store/owner_catalogue.py` (create and edit a sample size), `api/urls.py`
- Frontend: `src/App.jsx`, `src/views/vendor/Sidebar.jsx`, `src/views/owner/OwnerOrderDetail.jsx`
  (packing and gift samples), `src/views/owner/OwnerProduct.jsx` (the Sample tick),
  `playwright.config.js`
- Docs: `docs/BUILD_LOG.md`

New owner endpoints (staff only):

    GET  /api/v1/owner/orders/<oid>/dispatch/     POST /api/v1/owner/orders/<oid>/samples/
    GET  /api/v1/owner/expiry/                    POST /api/v1/owner/batches/<id>/write-off/
    GET  /api/v1/owner/batch-lookup/?code=        GET  /api/v1/owner/samples-report/

Nothing was removed or renamed. One field moved out of a customer-facing payload (D3); it was
added in this phase and no customer screen ever read it.

### 4. MIGRATIONS ADDED

| Migration | What | Reverse |
|---|---|---|
| `catalog.0008_productvariant_is_sample` | `is_sample` on a variant (False everywhere) | drops the column |
| `store.0043_order_samples` | the `OrderSample` table and `CartOrder.sample_decision` (UNDECIDED) | drops both; ledger rows stay |
| `inventory.0003_alter_stockmovement_kind` | adds `SAMPLE_OUT` to the choice list (no data change) | restores the old list |
| `inventory.0004_reservation_sample` | `StockReservation.sample` (null everywhere) | drops the column |

Back up first, then `python manage.py migrate`. Roll back Phase D only, **in this order**
(`inventory.0004` depends on `store.0043`, which depends on `catalog.0008`):

    python manage.py migrate inventory 0002
    python manage.py migrate store 0042
    python manage.py migrate catalog 0007

Verified on a copy of the database: apply, roll back all four, re-apply, all clean;
`makemigrations --check` reports no changes.

### 5. ENV VARS ADDED

None. One default changed: `MIN_SHELF_LIFE_ON_DISPATCH_DAYS` is now `0` (was `30`). If your
`backend/.env` sets it to 30, change it to 0 or delete the line (D10).

### 6. TESTS ADDED

`backend/tests/test_dispatch_samples.py`, 13 tests: the shipped shelf-life default is 0 (read
in a fresh interpreter); only an expired batch is held back from allocation; Handle orders
flags expired and undated batches, the date can be recorded from there, and an undated batch
never stops the parcel; a batch that expires after allocation shows as Expired; samples are
held, dispatched once as `SAMPLE_OUT`, never as a sale, and never change the total; a sample
can be removed and its stock comes back, the same sample twice is refused, more than there are
is refused, and a cancelled order takes none; cancelling releases sample holds; a sample is
invisible in the shop, in the size picker, in the cart and in every customer-facing payload,
while the owner's own view shows it; the report counts only customers who came back for that
product; the expiry screen lists expired, due-soon and undated stock; writing off goes through
the ledger, refuses held stock and a fractional quantity; batch lookup lists exactly the orders
that got that batch, marking sample-only and not-yet-sent ones; every endpoint is staff only.

Shown failing first against `5a68534`: collection error
(`ImportError: cannot import name 'SAMPLE_ADDED' from 'store.models'`). The sale/sample fix
(D2) was additionally proven load-bearing by removing it: 2 tests fail with `SALE_OUT` where
`SAMPLE_OUT` is expected, and pass again when it is restored.

    python -m pytest tests/test_dispatch_samples.py -q  ->  13 passed
    python -m pytest -q                                 ->  239 passed, 2 skipped (SQLite)
    $env:DATABASE_URL = "postgres://ecom:ecom@127.0.0.1:5432/ecom"
    python -m pytest -q                                 ->  241 passed (PostgreSQL 16)

Playwright, `frontend/e2e/owner.spec.js`, 3 tests: the owner adds a "5 g sample" size with the
Sample tick (the price fills itself with 0), gives it stock, confirms it is absent from the
shop and the size picker; a customer orders the Face Scrub; the owner sees the packing batch,
adds 2 samples, is refused a duplicate, records a use-by date, ships it, and the customer's own
pages never contain the word "sample"; undated stock is listed on Stock & expiry, two units are
written off, and the recall lookup finds the batch and reports an unknown code; the samples
report shows 1 given and 0 converted. Shown failing first against `5a68534`: 1 failed (no
Sample tick on the sizes form), the rest of the serial block not run.

    npm run build          ->  built
    npx playwright test    ->  28 passed

### 7. MANUAL VERIFICATION STEPS

Back up, migrate (section 4), `python -m pytest -q`, `npm run build`, run both servers, then:

1. Admin → Products → **Sizes & stock** on any product. Add a small size, tick **Sample**, save. It appears with a blue **Sample** badge. Give it stock.
2. Open the shop: that size is not in the picker and not in the listing.
3. Admin → Orders → open a live order. **Packing** shows the batch each line comes from; type a use-by date if one is missing.
4. **Gift samples**: choose the sample, Add to parcel. The order total does not move.
5. Open that order as the customer (My orders): no mention of a sample anywhere.
6. Ship the order. Django admin → Inventory → Stock movements: one `SAMPLE_OUT` row, no `SALE_OUT` for the sample.
7. Admin → **Stock & expiry**: write off a couple of units with a reason; the on-hand figure drops. Paste a batch code into **Find a batch**: the orders that got it are listed.
8. Admin → **Samples**: the sample shows 1 order given. Buy that product again with the same email, and it shows as converted.

### 8. ASSUMPTIONS MADE (exhaustive)

1. Decisions D1-D10.
2. A sample is one row per (order, variant); to change the quantity, remove it and add it again.
3. Samples cannot be changed once the order has been shipped, arrived or delivered.
4. A sample's price is stored as 0; nothing reads it, because `quote()` never sees a sample.
5. "Later" in the report means a strictly later order date; two orders placed the same second do not count as a conversion.
6. The report is computed on request, not stored. At this size that is a handful of queries.
7. Writing off uses the `MANUAL` channel and the `DAMAGE_OUT` kind, as the existing ledger defines them.
8. Batch lookup matches the code exactly first, then as "contains" when exactly one batch matches.
9. A batch whose use-by date is **today** is not allocated (the rule is "date in the future"), although the screens call it expired only once the date has passed. Shipping a cosmetic on its last day should not happen silently.
10. The expiry screen reads the whole batch table; with a home-scale catalogue that is cheap.

### 9. KNOWN GAPS

- **No packing slip.** The samples in a parcel are on screen only; there is nothing to print yet. The owner reads them off the order while packing.
- The legacy dashboard screens (old Orders, Earnings) know nothing about samples; the Handle orders screen is the one to use.
- No low-stock alert for samples: the owner sees "N left" in the picker when adding one.
- The samples report has no date range; it covers everything since the first sample went out.
- A sample whose stock has run out is shown in the picker but cannot be chosen.
- `EXPIRY_ALERT_DAYS` (45) is still only settable in the environment, not on the Store settings screen.
- The admin area's sidebar is getting long; it has not been reorganised.

### 10. NOT DONE AND WHY

- Kits from component stock: phase E.
- Customer support queries: phase F.
- Automatic expiry emails to the owner: the alert data exists (`batches_nearing_expiry`), but delivering it needs the email provider decision from G5 part B.
- Printing a packing slip: not in the roadmap for this phase.

---

## Phase C decisions (11 Oct 2026)

What customers are charged changes in this phase: approved in writing by the owner (Q9, ROADMAP C).

| # | Question | Decision | Why | Cost to reverse |
|---|---|---|---|---|
| C1 | When a draft picks up new shipping settings | When the checkout page opens, the server re-prices the unpaid draft (`POST payments/quote/<oid>/`) and stores the online price. What the page shows, what the order stores and what Razorpay is asked for are then the same number | "A threshold edited in the admin area applies on the next quote" without ever charging a number that was not shown | Low |
| C2 | How the COD fee gets onto an order | Only when the order is placed as COD, in the same transaction (`PlaceCodOrderView`): re-price with `payment_method="COD"`, store, place. The browser sends the total it showed (`expected_total_paise`); if the server's figure differs, nothing is placed and the new figures come back (409) | CLAUDE.md section 8: no fee the customer did not see. The client total is only compared, never used as money | Low |
| C3 | Razorpay and the fee | A draft never carries the fee, and starting a Razorpay payment is refused for any order that does | "A Razorpay order is always created from the non-COD quote" | One check |
| C4 | A coupon that stopped being valid between cart and checkout | Re-pricing re-checks it like any quote: it is dropped and the page shows the new total | Same rule as the cart; nothing is charged that was not shown | Low |
| C5 | `initial_total` on an order | subtotal + shipping + COD fee, so `initial_total - saved = total` still holds | Keeps the G1 column meaning consistent | One line |
| C6 | Settings that contradict themselves | Refused with a message: shipping on at ₹0, free shipping on with no amount, the COD fee on at ₹0. Switching a feature off needs no amount | The owner should never save a setting that quietly does nothing | Low |
| C7 | Copy that states shipping or COD terms | Built from the live settings in one helper (`frontend/src/utils/shippingText.js`): announcement bar, home page tiles, product page line, cart, shipping policy (now with a Cash on Delivery section). The cart also says what COD adds, before checkout | One true sentence everywhere; drip pricing ruled out | Low |
| C8 | Where the label details (Phase B) are edited | The new Store settings screen, alongside shipping and COD (closes a Phase B known gap) | No Django admin needed for day-to-day settings | n/a |
| C9 | Where the owner endpoint lives | New `backend/store/owner_settings.py` | Same reason as B2 | Move the class |

---

## PHASE C — Owner-set shipping and COD fee (COMPLETED)

### 1. PHASE COMPLETED

**Phase C**, branch `phase/C-shipping-cod`, built on Phase B `3b4a18c`.

- **Admin → Store settings** (sidebar, under More): charge shipping or not, the shipping charge,
  free shipping on or off and its threshold, offer Cash on Delivery or not, a COD fee on or off
  and its amount, plus the product-information label details. Audited as `settings.updated`.
- **`quote()` knows the payment method.** `total = subtotal - discount + shipping + COD fee`.
  The fee only applies to COD with the fee on; coupons never discount it; it never counts
  towards free shipping. Shipping off means free; free shipping off means always charged.
- **Checkout** shows "Cash on delivery (+ ₹49 fee)". Choosing it switches the summary to the
  COD figures (fee row, new total) before "Place order"; "Pay ₹X" online never includes it.
- **Placing COD** stores the fee on the order (`CartOrder.cod_fee_paise`) and refuses if the
  total is not the one the customer saw.
- **Order pages and emails** show a "Cash on Delivery fee" row when one was charged
  (confirmation page, customer order page, owner order page, order emails).
- **Placed orders never change** when settings change.
- **COD switched off** by the owner: not offered at checkout and refused by the API.

### 2. FILES CREATED

- `backend/addon/migrations/0007_shipping_cod_settings.py`
- `backend/store/migrations/0042_cartorder_cod_fee_paise.py`
- `backend/store/owner_settings.py`
- `backend/tests/test_pricing_c.py`
- `frontend/src/views/owner/OwnerSettings.jsx`
- `frontend/src/utils/shippingText.js`

### 3. FILES MODIFIED

- Backend: `addon/models.py` (five settings), `store/models.py` (`CartOrder.cod_fee_paise`), `store/pricing.py` (`payment_method`, switches, `order_lines`, `quote_order`, fee stored by `apply_quote_to_order`), `store/payment_views.py` (`CheckoutQuoteView`, COD placement re-prices with the guard, Razorpay guard, `cod_fee_paise` in payment methods, COD respects the owner switch), `store/emails.py`, `templates/email/order_update.txt`, `order_update.html`, `api/urls.py` (`payments/quote/<oid>/`, `owner/settings/`), `tests/test_payments.py` (one expectation: the payment-methods answer gained `cod_fee_paise`)
- Frontend: `src/App.jsx`, `src/views/vendor/Sidebar.jsx`, `src/views/shop/Checkout.jsx`, `Cart.jsx`, `OrderConfirmation.jsx`, `ProductDetail.jsx`, `home.jsx`, `src/views/customer/OrderDetail.jsx`, `src/views/owner/OwnerOrderDetail.jsx`, `src/views/base/StoreHeader.jsx`, `src/views/policy/PolicyPage.jsx`, `policies.js`, `e2e/checkout.spec.js`, `playwright.config.js`
- Docs: `docs/BUILD_LOG.md`

New endpoints: `POST /api/v1/payments/quote/<order_oid>/` (public, order capability as for
checkout), `GET`/`PATCH /api/v1/owner/settings/` (staff only). Nothing removed or renamed.

### 4. MIGRATIONS ADDED

| Migration | What | Reverse |
|---|---|---|
| `addon.0007_shipping_cod_settings` | `shipping_enabled`, `free_shipping_enabled`, `cod_enabled` (all default on), `cod_fee_enabled` (off), `cod_fee_paise` (0): today's behaviour exactly | drops the five columns |
| `store.0042_cartorder_cod_fee_paise` | `CartOrder.cod_fee_paise` (default 0, paise only) | drops the column |

Back up first, then `python manage.py migrate`. Roll back Phase C only:

    python manage.py migrate store 0041
    python manage.py migrate addon 0006

Verified on a copy of the database: apply, roll back both, re-apply, all clean;
`makemigrations --check` reports no changes.

### 5. ENV VARS ADDED

None.

### 6. TESTS ADDED

`backend/tests/test_pricing_c.py`, 9 tests: fee off, COD costs the same; fee on, added only for
COD, never discounted (a 100% coupon leaves shipping and fee), never counted towards free
shipping, nothing on an empty quote; shipping off is free and free shipping off always charges,
with no nudge; checkout re-prices the draft with an edited threshold, shows both totals,
audits `order.repriced`, and drops COD when the owner switches it off; placing COD stores the
fee, mirrors pass, `initial_total - saved = total`, Razorpay refuses that order, the online
order's Razorpay amount has no fee, the email shows the fee row; a COD placement with a total
the customer did not see is refused with nothing changed, a float total is refused, a client
`total_paise` is ignored; a placed order keeps its figures when every setting changes; COD off
is neither offered nor accepted; the settings endpoint is staff only (401/403), refuses floats,
negative amounts and contradictory switches, saves paise, audits with the actor, and the public
`addon/` follows.

Shown failing first against `3b4a18c`: collection error
(`ImportError: cannot import name 'quote_order' from 'store.pricing'`).

    python -m pytest tests/test_pricing_c.py -q   ->  9 passed
    python -m pytest -q                           ->  226 passed, 2 skipped (SQLite)
    $env:DATABASE_URL = "postgres://ecom:ecom@127.0.0.1:5432/ecom"
    python -m pytest -q                           ->  228 passed (PostgreSQL 16)

Playwright, `frontend/e2e/checkout.spec.js` gains one test: the owner switches the ₹49 fee on in
Store settings; a guest's cart says COD adds ₹49; checkout shows "(+ ₹49 fee)", ₹528 online,
then ₹49 and ₹577 once COD is chosen; the confirmation page shows the fee and ₹577; with
shipping switched off the announcement, home page and shipping policy all say so. The test
restores the default settings through the API in a `finally`. Shown failing first against
`3b4a18c`: 1 failed (no Store settings screen), the 3 existing checkout tests passed.

    npm run build          ->  built
    npx playwright test    ->  25 passed

### 7. MANUAL VERIFICATION STEPS

Back up, migrate (section 4), `python -m pytest -q`, `npm run build`, run both servers, then:

1. Admin → **Store settings**: switch on "Charge a Cash on Delivery fee", type 49, save. The line under the form says "Cash on Delivery with a ₹49 fee".
2. As a shopper add Face Serum 30 ml: the cart says "Paying by Cash on Delivery adds a ₹49 fee".
3. Checkout: "Cash on delivery (+ ₹49 fee)"; online total ₹528; pick COD: fee row ₹49, total ₹577. Place the order: the confirmation and the order email show the fee.
4. Admin → Handle orders → that order: "Includes Cash on Delivery fee ₹49".
5. Store settings: switch shipping off. The top bar says "Free shipping on every order"; a new cart shows shipping Free.
6. Change the fee to 99: the order from step 3 still shows ₹577.
7. Switch everything back (shipping on ₹79, free from ₹999, fee off).

### 8. ASSUMPTIONS MADE (exhaustive)

1. Decisions C1-C9.
2. The fee is one flat amount per COD order, whatever the order size.
3. Tax (rate 0 today) is carved out of the whole total, COD fee included, as with shipping (E12).
4. Turning the fee off and COD off are independent: with COD off, the fee setting is kept but never charged.
5. "Placed" means payment status no longer `initiated`/`processing`; only drafts are re-priced.
6. The legacy Stripe path is switched off and was not taught about the fee (it would charge the stored online total).
7. Settings changes take effect for the next quote; a customer already on the checkout page is protected by C2 (COD) and by the stored total (online).

### 9. KNOWN GAPS

- The legacy dashboard screens (old Orders, Earnings) do not show the COD fee separately; it is inside the order total. The Handle orders screen shows it.
- Revenue reports do not split COD fees from goods.
- The tax rate is still set only in Django admin (it stays 0 until L2 is answered).
- The Playwright test changes store-wide settings and restores them in a `finally`; if the suite is killed mid-test, run it again (the database is recreated on every run).
- Admin help texts in `text-muted` remain low contrast in other admin screens (two on Store settings were switched to the theme's `text-subtle`).

### 10b. FOLLOW-UP (11 Oct 2026): a flaky guest account-link step

Reported by the owner: one browser test failed, "G3: a guest places a Cash on Delivery order
end to end and can ask for an account link".

Cause: the suite's Django server raises `THROTTLE_AUTH` and `THROTTLE_CHECKOUT` to 1000/min but
never `THROTTLE_OTP`, whose real limit is **5 a minute**. "Email me the link"
(`account/invite/`) is on that scope, along with password reset and the account-claim link. Any
run that reaches it more than five times a minute gets a 429, and the step fails for a reason
that has nothing to do with the store.

Reproduced here with `npx playwright test e2e/checkout.spec.js --grep "a guest places"
--repeat-each=6`: runs 1-5 passed, run 6 failed exactly as reported. With `THROTTLE_OTP` added
to `playwright.config.js`, the same command gives 6 passed, and the whole suite is 25 passed.

This is a test-harness limit only. The real store keeps its 5-a-minute limit on those
endpoints, which is what stops someone using them to send mail to an address repeatedly.

If a single full run still fails that test on your machine, it is a different cause and I need
the error block from the terminal (or `frontend/test-results/.../error-context.md`).

### 10. NOT DONE AND WHY

- Weight-based shipping (ranked for later, item 5).
- Showing the COD fee on the legacy dashboard screens: they are being retired, not extended.
- Dispatch checks, samples, batch lookup, `MIN_SHELF_LIFE_ON_DISPATCH_DAYS` to 0: phase D.

---

## Phase B decisions (11 Oct 2026)

| # | Question | Decision | Why | Cost to reverse |
|---|---|---|---|---|
| B1 | One screen or two for sizes and stock | **One screen per product**, `views/owner/OwnerProduct.jsx` at `/admin-area/owner/products/<pid>/`: details, sizes, stock. The roadmap named `OwnerSizes.jsx` and `OwnerStock.jsx` | Stock is added per size; one page avoids jumping between two screens for the same product | Split the file |
| B2 | Where the owner endpoints live | New `backend/store/owner_catalogue.py` (the roadmap said `owner_views.py`) | `owner_views.py` is the orders and reviews module; catalogue work is a separate concern | Move the classes |
| B3 | Net-quantity backfill from `weight_grams` | **Not done.** No data migration copies `weight_grams` into net quantity | `weight_grams` is the packed shipping weight, packaging included, and the seeded sizes are millilitres. Copying it would declare a false net quantity (same reason as K5). Sizes show no net quantity until the owner types one | One data migration |
| B4 | Where the claim-word warning appears | In the Details form of the new product screen, live while typing, and in the API response after saving (`warnings`). The legacy add/edit form has no benefit-line, how-to-use or cautions field, so it has no warning | The warning sits where the words are typed (Z4) | Low |
| B5 | Products made in the old Add Product form | Created with one placeholder size "Default"; the first size added takes its place (keeping any stock typed at creation and the product's SKU). After creating a product, the form now opens its sizes-and-stock screen | No orphan "Default" size beside the real ones | Low |
| B6 | Removing a category or a size | Neither can be deleted from the admin area: categories are hidden, sizes are switched off. The main size cannot be switched off until another is made main | Orders and products refer to them (rule 4) | n/a |
| B7 | MRP on the product page | Shown twice when there is a reduction: as the struck price (existing G2 rule) and as a plain "MRP ₹X (inclusive of all taxes)" row in Product information. The row shows whatever MRP the owner entered; nothing is shown when there is none | The roadmap's Product information block; the declaration is separate from the discount display | Remove one row |
| B8 | Uploads during the Playwright suite | New optional setting `DJANGO_MEDIA_ROOT`; the suite points it at `backend/e2e-media/` (deleted at the start of every run, git-ignored) | The new owner test uploads a product photo, and CLAUDE.md forbids tests writing into `backend/media/` | One line |
| B9 | How money is typed | Rupees as text in the form ("449" or "449.50"), sent as text, turned into paise on the server by `core.money.to_paise`. A JSON number is refused | Rule 6: no float ever touches a price | Low |

---

## PHASE B — Personal-care catalogue (COMPLETED; label details still needed from the owner)

### 1. PHASE COMPLETED

**Phase B**, branch `phase/B-catalogue`, built on Phase A `7db852c`.

- **Sub-categories.** A category can sit inside another (Skincare › Face). Loops are refused.
  New admin screen **Categories** (sidebar): add, rename, move, hide or show.
- **The shop filters by category** with chips: top-level categories, then one more row for
  each level below the chosen one (Skincare → Face → Serums). `/shop?category=skincare` includes everything inside Skincare at any depth; an
  unknown or hidden category shows nothing, never everything.
- **Sizes and stock from the admin area** (no Django admin needed): Products → "Sizes & stock",
  or straight after Add product. Per size: name, net quantity in g or ml, price, MRP, packed
  shipping weight, optional SKU; edit, make main, switch off. Price above MRP is refused.
  Price changes still write price history and an audit row.
- **Add stock** per size: quantity made, made-on date, optional use-by date, cost per unit,
  notes. It creates a batch and books it into the stock ledger. A batch's use-by date can be
  added or corrected later (audited); batches past it are marked **Expired**; batches with no
  date say so. Undated stock is never blocked (Y12).
- **Benefit line** (max 120 characters) on the product tile: over the photo on hover or keyboard
  focus on desktop, always under the name on phones.
- **Claim-word warning** (Z4): words such as cures, heals, acne, natural, 100% are listed while
  the owner types; saving still works. Word list: `backend/catalog/claims.py`.
- **Product page:** breadcrumb (Shop / Skincare / Face / product), "Net quantity 30 ml" under the
  price (follows the chosen size), the benefit line, How to use, Ingredients, Cautions, and a
  **Product information** block (MRP inclusive of all taxes, net quantity, maker, address,
  country of origin, consumer care) that shows only the fields that are filled in.
- **Store-wide label details** (`maker_name`, `maker_address`, `country_of_origin`,
  `consumer_care_contact`) exist and are public through `/api/v1/addon/`. They are **blank** and
  are entered in Django admin → Addon → Config settings (see Known gaps).
- `seed_ayura`: Face and Lips now sit inside Skincare; every placeholder product has a benefit
  line, how to use, cautions and a placeholder ingredients line; every size has its net quantity.

### 2. FILES CREATED

- `backend/catalog/claims.py`
- `backend/store/owner_catalogue.py`
- `backend/store/migrations/0040_category_parent.py`
- `backend/store/migrations/0041_product_care_fields.py`
- `backend/catalog/migrations/0007_variant_net_quantity.py`
- `backend/addon/migrations/0006_configsettings_label_fields.py`
- `backend/catalog/tests/test_catalogue_b.py`
- `backend/tests/test_media_root.py`
- `frontend/src/views/owner/OwnerProduct.jsx`
- `frontend/src/views/owner/OwnerCategories.jsx`
- `frontend/e2e/catalogue.spec.js`

### 3. FILES MODIFIED

- Backend: `store/models.py` (Category `parent`, `ancestors`, `would_create_cycle`, `descendant_ids`; Product `benefit_line`, `ingredients`, `how_to_use`, `cautions`), `catalog/models.py` (`net_quantity`, `net_quantity_unit`, `net_quantity_label`), `addon/models.py` (four label fields), `api/urls.py` (seven owner routes), `store/serializers.py` (new fields in the public product and variant payloads), `store/views.py` (`?category=` filter with sub-categories; category list ordered by name), `store/admin.py`, `catalog/admin.py` (net quantity and parent columns), `catalog/management/commands/seed_ayura.py`, `catalog/tests/test_seed_ayura.py`, `backend/settings.py` (`DJANGO_MEDIA_ROOT`), `.env.example`
- Frontend: `src/App.jsx` (two routes), `src/views/vendor/Sidebar.jsx` (Categories link), `src/views/vendor/AddProduct.jsx` (opens the new product's sizes-and-stock screen after creating it), `src/views/vendor/Products.jsx` ("Sizes & stock" button), `src/views/shop/Products.jsx` (category chips), `src/views/shop/ProductDetail.jsx`, `src/views/ui/kit.jsx` (benefit line on `ProductCard`), `playwright.config.js` (`catalogue.spec.js`, `e2e-media`)
- Root: `.gitignore` (`e2e-media/`), `docs/BUILD_LOG.md`

New owner endpoints (staff only):

    GET   /api/v1/owner/categories/                 POST  /api/v1/owner/categories/
    PATCH /api/v1/owner/categories/<id>/
    GET   /api/v1/owner/products/<pid>/             PATCH /api/v1/owner/products/<pid>/
    POST  /api/v1/owner/products/<pid>/variants/    PATCH /api/v1/owner/variants/<id>/
    POST  /api/v1/owner/variants/<id>/stock/        PATCH /api/v1/owner/batches/<id>/

No endpoint, model or field was removed or renamed.

### 4. MIGRATIONS ADDED

| Migration | What | Reverse |
|---|---|---|
| `store.0040_category_parent` | nullable `Category.parent` (PROTECT) | drops the column |
| `store.0041_product_care_fields` | `benefit_line`, `ingredients`, `how_to_use`, `cautions` on Product (blank default) | drops them |
| `catalog.0007_variant_net_quantity` | `net_quantity`, `net_quantity_unit` on ProductVariant (no backfill, B3) | drops them |
| `addon.0006_configsettings_label_fields` | four label fields on ConfigSettings (blank default) | drops them |

Back up first, then apply (from `backend\`):

    New-Item -ItemType Directory -Force -Path ..\backups | Out-Null
    Copy-Item db.sqlite3 "..\backups\db-$(Get-Date -Format 'yyyyMMdd-HHmmss').sqlite3"
    python manage.py migrate

Roll back Phase B only:

    python manage.py migrate store 0039
    python manage.py migrate catalog 0006
    python manage.py migrate addon 0005

Verified on a copy of the database: apply, roll back all four, re-apply, all clean;
`makemigrations --check` reports no changes.

### 5. ENV VARS ADDED

- `DJANGO_MEDIA_ROOT` (backend, optional): folder for uploads when Cloudinary is not used.
  Default `backend/media`. Only the Playwright suite sets it.

### 6. TESTS ADDED

`backend/catalog/tests/test_catalogue_b.py`, 13 tests: categories nest and the filter includes
sub-categories (and shows nothing for an unknown or hidden one); a category cannot go inside
itself; the first size replaces the placeholder, both sizes reach the shopper with their net
quantity, price history and audit rows written; bad values (JSON number, text, price above MRP,
unknown unit, blank label) refused with nothing written; SKUs made automatically or kept as
typed, a duplicate refused; the main size cannot be switched off until another is main, and the
legacy price follows the main size; a price change writes history and an audit row; receiving
stock creates a batch and a ledger movement with the staff actor, undated stock allowed, bad
values refused; a use-by date added later is audited and never moves stock; details save,
risky words come back as warnings without blocking, 121 characters refused; whole-word claim
matching; label details public through `addon/`; every endpoint 401 anonymous, 403 customer.

`backend/tests/test_media_root.py`, 2 tests (default `media/`; follows `DJANGO_MEDIA_ROOT`).
`backend/catalog/tests/test_seed_ayura.py` extended (parents, net quantities, care fields, and the
banned-word check now covers the new text).

Shown failing first: `test_catalogue_b.py` against `7db852c` fails at collection
(`ModuleNotFoundError: No module named 'catalog.claims'`); `test_media_root.py` with the old
`settings.py`: 1 failed, 1 passed (the default case passes either way).

    python -m pytest catalog/tests/test_catalogue_b.py -q   ->  13 passed
    python -m pytest -q                                      ->  217 passed, 2 skipped (SQLite)
    $env:DATABASE_URL = "postgres://ecom:ecom@127.0.0.1:5432/ecom"
    python -m pytest -q                                      ->  219 passed (PostgreSQL 16)

Playwright, `frontend/e2e/catalogue.spec.js`, 3 tests: the owner creates a product in Add
product (with a photo), lands on its sizes-and-stock screen, types a benefit line with "Cures"
and sees the warning, sets Skincare › Face, adds 30 ml and 100 ml (the first replaces
"Default"), is refused a 200 ml priced above its MRP, adds a dated and an undated batch, reaches
the screen again from the product list, and adds a third-level category (Mists inside Face); a shopper filters by
Skincare then Face, sees the third row of chips and an empty Mists, sees the benefit line on hover, opens the product and sees the breadcrumb,
"Net quantity 30 ml" then "100 ml", the care sections and the MRP row, and no Ingredients section
(none was typed); at 390 px the benefit line is under the name. Shown failing first against
`7db852c`: 2 failed (no Face category; no benefit line), 1 not run (serial).

    npm run build          ->  built
    npx playwright test    ->  24 passed

### 7. MANUAL VERIFICATION STEPS

Back up and migrate (section 4), then:

    python manage.py seed_ayura      (on a development database: it only adds what is missing)
    python -m pytest -q
    python manage.py runserver

Second terminal: `cd frontend`, `npm run build`, `npm run dev`. Then:

1. `/shop`: chips All, Bodycare, Haircare, Skincare. Click Skincare: a second row (All skincare, Face, Lips) and the Face and Lip products. Hover a card: the benefit line slides over the photo.
2. Open Face Serum: breadcrumb Shop / Skincare / Face / Face Serum; "Net quantity 30 ml"; pick 50 ml and it changes; How to use, Ingredients, Cautions; Product information with MRP and net quantity.
3. Sign in as the owner → Admin → Products → **Sizes & stock** on a product. Type "cures" in the benefit line: the warning appears. Add a size, add stock with and without a use-by date, set a use-by date later.
4. Admin → **Categories**: add "Serums" inside Face. In the shop, choose Skincare, then Face: a third row of chips shows Serums.
5. Add product: after "Product created" it opens the new product's sizes-and-stock screen.
6. Django admin → Addon → Config settings: fill maker name, address, country of origin and consumer care; they appear in Product information.

### 8. ASSUMPTIONS MADE (exhaustive)

1. Decisions B1-B9.
2. Net quantity is a whole number of g or ml (no decimals, no other units such as pieces).
3. One set of label details for the whole store (Y13); nothing per product.
4. "Expired" means the use-by date is before today (Asia/Kolkata); a batch expiring today is not yet expired.
5. A use-by date must be after the made-on date; made-on cannot be in the future; made-on defaults to today.
6. Batch codes are made from the size's SKU and the made-on date unless the owner types one (the API accepts it; the form does not show the field).
7. Hidden categories stay in the owner's category select, marked "(hidden)"; products can still be put in them.
8. Products of a hidden parent's visible sub-category still appear under "All"; the sub-category's chip appears only when its parent is shown.
9. The legacy `stock_qty` typed in Add product still becomes the "Default" size's opening stock (E15); the new screen is the place to add stock afterwards.
10. The warning list is a prompt, not a legal reading (L6).
11. `seed_ayura` ingredients are a placeholder line marked `[PLACEHOLDER]`; cautions are generic placeholder text.

### 9. KNOWN GAPS

- **Label details are blank (L3, stop-and-ask item).** Maker name and address, country of origin and consumer-care contact must come from you, and which of them the law requires is question L3. Until then Product information shows only MRP and net quantity.
- Label details are edited in Django admin, not the admin area; the shipping-settings screen in phase C is the natural home for them.
- The legacy Size and Color tabs remain in Add product and Edit product. They do not create sizes a shopper can choose; sizes are made on the new screen. Removing the tabs is a removal proposal (rule 4).
- The legacy edit form (`UpdateProduct.jsx`) is unchanged and has no benefit-line or care fields; it links nowhere to the new screen except through the product list.
- Undated batches are shown, not blocked, on the product screen; flagging them before dispatch is phase D.
- `MIN_SHELF_LIFE_ON_DISPATCH_DAYS` still defaults to 30 (Z1 says 0 for Ayura). A batch whose use-by date is under 30 days away is not sold. Changing the default is left to phase D, where dispatch rules are built.
- In the admin area the small help texts (`text-muted`) are low-contrast on the canvas colour, as in the other admin screens (`admin.css`).
- Category images are not managed from the new screen (none are shown in the shop).

### 10. NOT DONE AND WHY

- Net-quantity backfill: B3.
- Removing the legacy Size/Color tabs or `Product.stock_qty`: rule 4; proposals only.
- Shipping and COD fee settings: phase C. Dispatch checks, samples, batch lookup: phase D.
- Filling the label details or the real ingredients: the owner supplies them (L3).

---

## PHASE A — Fork and rebrand (COMPLETED)

### 1. PHASE COMPLETED

**Phase A**, branch `phase/A-rebrand`, built on Noore `c879153`.

Done:
- **The storefront reads as Ayura everywhere.** Store name, page titles, description, header
  and footer, About, contact, policies, empty and error states, search, the admin dashboard
  and Django admin. No "Noore", "candle" or "vendor" anywhere a shopper can reach (Playwright
  crawl).
- **Tagline as the home headline:** "If we wouldn’t use it at home, we don’t bottle it." It is
  also the footer line and opens the About page, from `VITE_TAGLINE`.
- **Brand-neutral theme (K1-K4).** The whole look, including the browser colour, comes from one
  BRAND block in `src/theme/brand.css` plus the font imports in `src/theme/brand-fonts.js`.
- **Three palette options built and screenshotted** (home, product, cart at 390 px and 1280 px).
  The owner chose option 2, Turmeric.
- **Policy pages** gain labelled placeholder sections for personal care: opened products;
  damaged, leaking or wrong items; using the products; shelf life. `PLACEHOLDER_COPY` stays
  `true` and every page says so.
- **`seed_ayura`** (K7).
- **Deployment:** `docs/DEPLOY-AYURA.md` (every environment variable, the fork steps, the free
  stack), `render.yaml` (K9), `keep-awake.yml` (K8), `deploy/` renamed for Ayura.
- **Docs:** this section, the reconstructed section below, `CLAUDE.md` updated (approved),
  `docs/ROADMAP.md` is Ayura's plan.

- **Palette: Turmeric** (K15), the owner's choice; the two unchosen palettes' font packages were
  removed again.
- **Logo** (K16, K17): header shows the wordmark, the footer the full logo; favicon and phone
  home-screen icon are the leaf-and-drop mark.

### 2. FILES CREATED

- `backend/catalog/management/commands/seed_ayura.py`
- `backend/catalog/tests/test_seed_ayura.py`
- `backend/static/.gitkeep`
- `frontend/src/theme/brand-fonts.js`
- `frontend/public/brand/logo-wordmark.png`, `logo-full.png`, `logo-mark.png`, `README.md`
- `frontend/public/favicon.png`, `frontend/public/apple-touch-icon.png`
- `docs/DEPLOY-AYURA.md`
- `docs/ROADMAP.md` (Ayura's; the previous one is archived, see section 3)

### 3. FILES MODIFIED

Renamed (and modified):
- `frontend/src/theme/noore.css` → `frontend/src/theme/brand.css`
- `frontend/src/views/ui/noore.jsx` → `frontend/src/views/ui/kit.jsx`
- `deploy/noore-web.service`, `noore-worker.service`, `noore-backup.service`, `noore-backup.timer` → `deploy/ayura-*`
- `docs/ROADMAP.md` → `docs/archive/ROADMAP-noore-v2.md` (unchanged)
- `docs/DEPLOY-FREE.md` → `docs/archive/DEPLOY-FREE-noore.md` (unchanged)

Modified:
- Frontend: `index.html`, `vite.config.js`, `.env.example`, `package.json`, `package-lock.json`, `playwright.config.js`, `public/favicon.svg`, `src/main.jsx`, `src/App.jsx`, `src/theme/admin.css`, `src/layouts/LegacyStyles.jsx`, `src/utils/constants.js`, `apiCache.js`, `image.js`, `usePageTitle.js`, `src/views/base/StoreHeader.jsx`, `StoreFooter.jsx`, `NotFound.jsx`, `src/views/shop/home.jsx`, `Products.jsx`, `ProductDetail.jsx`, `Cart.jsx`, `Checkout.jsx`, `OrderConfirmation.jsx`, `src/views/customer/Orders.jsx`, `OrderDetail.jsx`, `BuyAgainButton.jsx`, `src/views/auth/login.jsx`, `register.jsx`, `logout.jsx`, `ClaimAccount.jsx`, `src/views/policy/About.jsx`, `Contact.jsx`, `PolicyPage.jsx`, `policies.js`, `src/views/owner/ShopNotReady.jsx`, `src/views/vendor/Dashboard.jsx`, `Sidebar.jsx`, `e2e/brand.spec.js`, `storefront.spec.js`, `checkout.spec.js`, `coldstart.spec.js`
- Backend: `backend/settings.py`, `.env.example`, `core/management/commands/seed_e2e.py`
- Root: `CLAUDE.md`, `.gitignore`, `render.yaml`, `.github/workflows/keep-awake.yml`, `deploy/Caddyfile`, `backup.sh`, `restore.sh`, `backup.env.example`, `env.production.example`, `docs/DEPLOY.md`, `docs/BUILD_LOG.md`

### 4. MIGRATIONS ADDED

None. No model, field or endpoint was added, renamed or removed.

### 5. ENV VARS ADDED

Frontend (`frontend/.env.example`): `VITE_TAGLINE`, `VITE_STORE_DESCRIPTION` (both optional).
New npm dependency: `@fontsource-variable/bricolage-grotesque` (the typeface, bundled).
Changed defaults: `VITE_STORE_NAME` and backend `STORE_NAME` now default to `Ayura`;
`VITE_WHATSAPP_NUMBER` example is the owner's number `917888548215`.

### 6. TESTS ADDED

Backend, `backend/catalog/tests/test_seed_ayura.py`, 5 tests. Shown failing first: with the
command file absent, 4 failed and 1 passed (the "refuses outside DEBUG" test passes either way,
because an unknown command also raises `CommandError`).

    python -m pytest catalog/tests/test_seed_ayura.py -q   ->  5 passed
    python -m pytest -q                                     ->  202 passed, 2 skipped (SQLite, 204 collected)
    $env:DATABASE_URL = "postgres://ecom:ecom@127.0.0.1:5432/ecom"
    python -m pytest -q                                     ->  204 passed, 0 skipped (PostgreSQL 16)

`tests/test_launch.py::test_django_deployment_check_passes_with_production_settings` failed on
the fresh Ayura clone (`static/` missing) and passes with `backend/static/.gitkeep` (K10).

Playwright, `frontend/e2e/brand.spec.js` extended: the crawl now also forbids "noore" and
"candle"; every title contains the store name; the browser colour equals the theme's canvas;
the description has no unfilled placeholder; the header and footer logo images load and carry
the store name as their text alternative; the three icon files are served; a new static check
finds no leftover theme or brand names in `src/`. The logo check was shown failing with the
`public/brand/` folder taken away. Shown failing first: the new `brand.spec.js` run against the untouched
Noore code gives **6 failed, 4 passed** (the 4 are the unchanged access-control checks).

    npx playwright test   ->  21 passed

The other specs were moved to the Ayura seed (Face Serum 30 ml Rs 449 / 50 ml Rs 649, Hair Oil,
Shampoo) with every expected total recalculated: 50 ml cart Rs 649 + Rs 79 = Rs 728; WELCOME10
takes Rs 64.90 for Rs 663.10; two 50 ml (Rs 1,298) ship free; the reorder cart is Rs 748 + Rs 79.

### 7. MANUAL VERIFICATION STEPS

Make the repository (keeps Noore's history; Noore's folder is not touched):

    git clone "C:\path\to\noore\Completed Source Code" ayura
    cd ayura
    git remote remove origin
    git checkout -b phase/A-rebrand

Apply the Phase A files, delete the old paths listed under "Renamed" in section 3, then:

    cd backend
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements-dev.txt
    Copy-Item .env.example .env
    python -c "import secrets; print(secrets.token_urlsafe(64))"

Paste the printed value as `DJANGO_SECRET_KEY` in `backend\.env`, set `DJANGO_DEBUG=True` and
`DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`, then:

    python manage.py migrate
    python manage.py seed_ayura
    python -m pytest -q
    python manage.py runserver

Second terminal:

    cd frontend
    npm install
    npm run build
    npm run dev

1. http://localhost:5173 : the Ayura logo in the header and footer; the tagline is the headline; yellow collection band; six products in the row. The browser tab shows the leaf-and-drop icon.
2. Open Face Serum: 30 ml Rs 449 (struck Rs 499, 10% off); 50 ml Rs 649 (7% off). No "Net weight" row.
3. Footer: each policy page shows the placeholder notice and the new personal-care sections.
4. Change `--color-canvas` in `frontend/src/theme/brand.css`: every page and the browser colour follow.
5. `npx playwright test` with the venv active: 21 passed.

### 8. ASSUMPTIONS MADE

1. Decisions K1-K14 above, and Y1-Y20, Z1-Z9 in `docs/ROADMAP.md`.
2. Home copy uses only facts the owner stated: home-made, made fresh, small batches, skin/hair/body care. No ingredient, origin, "natural" or "Ayurvedic" claim (Z9).
3. The hero picture is the first featured product's photo, as before.
4. Placeholder pictures are drawn only by `seed_ayura` (DEBUG only) and never reach production.
5. Seed shipping weights (`weight_grams`) are rough packed weights, used only by phase-B shipping work.
6. Seed batches carry a best-before one year out; the real shelf life is the owner's to enter.
7. Test names and fixtures that say "candle" (and a few `STORE_NAME = "Noore Candles"` settings inside tests that test the setting itself) were left alone (Y18).
8. `docs/DEPLOY.md` (paid server) keeps Noore's proven steps with Ayura's names; it was not re-run.

### 9. KNOWN GAPS

- The logo is a raster image cut from a 1024 px PNG. It is sharp at the sizes used; a vector (SVG) original, if one exists, would be sharper on large screens and smaller to download.
- If the logo was made with an AI image tool, whether it can be registered as a trademark is a question for the professional alongside L5.
- Some inline styles still set uppercase letter-spacing (stock status, size buttons, a few admin labels). They are outside the `.ui-caption` pattern and change in the screens phase B rewrites.
- The admin area keeps square corners and uppercase labels from `admin.css`: it follows the palette and typefaces, not the storefront's button shape.
- Support email is the placeholder `support@example.com` until `VITE_SUPPORT_EMAIL` is set.
- Home "UPI, cards or cash. Pay online or on delivery, at the same price" stays true only until phase C turns a COD fee on; phase C changes that line.
- Email delivery, a custom domain and live payments are as in `docs/DEPLOY-AYURA.md`, "What this deployment does not have".
- Legal questions L1-L7 are open.

### 10. NOT DONE AND WHY

- Removing `seed_noore`, the tracked `backups/` file, or the legacy vendor code: rule 4; proposals only.
- Renaming test fixtures: Y18.
- Category hierarchy, net quantity, sizes screen: phase B.

---

## RECONSTRUCTED — Noore work not recorded in this log (4 Oct to 11 Oct 2026)

Written on 11 Oct 2026 **from the git history and the code**, not by whoever made the changes.
It records what the commits contain; the reasons are taken from comments in the code where they
exist. Commits: `435cbd8` (the first commit, 4 Oct), `97b9f1a`, `8eecc47`, `947ed05` (4 Oct),
`3faa32e` (7 Oct), `cfab735` (8 Oct), `c879153` (11 Oct).

### 1. PHASE COMPLETED

Six changes after G5 part A, plus features already present in the first commit:

- **In the first commit but not logged** (`435cbd8`): deleting a product from the dashboard
  (only when it has no stock history or orders, audited as `product.deleted`; otherwise refused
  with an explanation), hiding and showing a product (`vendor-product-visibility`), the
  `purge_product` command (erases demo products and their ledger rows, refuses anything that has
  been ordered), and an Add Product form that tolerates its blank repeatable rows. 10 tests
  (190 collected, against 180 at the end of G4.5).
- **Free hosting** (`97b9f1a`): `render.yaml`, `backend/build.sh`, `frontend/vercel.json`,
  `docs/DEPLOY-FREE.md`; product photos on Cloudinary when `CLOUDINARY_URL` is set; static files
  through WhiteNoise; Render's hostname allowed automatically; background jobs runnable over
  HTTP (`POST /api/v1/jobs/run/`, `core/jobs_api.py`, off unless `JOBS_RUN_TOKEN` is set) and
  a GitHub workflow calling it; `backend/db.sqlite3` and `backend/media/` removed from git.
- **`claim_shop` on an empty database** (`8eecc47`): creates the store's one shop instead of
  pointing to the old shop sign-up page.
- **Listing speed** (`947ed05`): a whole page's stock in two queries (`available_qty_map`),
  prefetched variants, ratings and order counts annotated in one query; a product with no MRP
  no longer divides by zero and breaks the listing; Cloudinary photos requested at the size
  shown (`frontend/src/utils/image.js`); the jobs workflow every 10 minutes.
- **Admin area out of the shopper's download** (`3faa32e`): admin pages and their heavy
  libraries load only when opened (lazy routes, `manualChunks`); the home collection became a
  scrollable row.
- **Admin area design** (`cfab735`): `frontend/src/theme/admin.css` gives the Bootstrap-era
  dashboard markup the store's look without loading Bootstrap; new dashboard home and sidebar.
- **First-visit speed and safe bylines** (`c879153`):
  - `frontend/src/utils/apiCache.js` starts the catalogue request before React renders, paints
    the last copy from `localStorage`, and says honestly when the server is waking.
  - `.github/workflows/keep-awake.yml` replaced the jobs workflow: it pings and runs jobs.
  - `backend/core/display_name.py`: review bylines never show an email address or a phone number.
  - `User.save()` now falls back to the email's local part, not the whole address.

### 2. FILES CREATED

`render.yaml`, `backend/build.sh`, `backend/core/jobs_api.py`, `backend/core/display_name.py`,
`backend/store/management/commands/purge_product.py`, `frontend/vercel.json`,
`frontend/src/utils/image.js`, `frontend/src/utils/apiCache.js`, `frontend/src/theme/admin.css`,
`frontend/e2e/coldstart.spec.js`, `.github/workflows/keep-awake.yml`, `docs/DEPLOY-FREE.md`.
(`.github/workflows/run-jobs.yml` was created in `97b9f1a` and deleted in `c879153`.)

### 3. FILES MODIFIED

Backend: `backend/settings.py`, `.env.example`, `api/urls.py`, `core/serializers.py`,
`core/management/commands/claim_shop.py`, `catalog/display.py`, `inventory/services.py`,
`store/models.py`, `store/serializers.py`, `store/views.py`, `vendor/views.py`,
`userauths/models.py`, `userauths/serializer.py`, `tests/test_launch.py`, `tests/test_security.py`,
`catalog/tests/test_storefront.py`. Frontend: `index.html`, `vite.config.js`,
`playwright.config.js`, `src/main.jsx`, `src/App.jsx`, `src/theme/noore.css`,
`src/views/ui/noore.jsx`, `src/views/plugin/Addon.jsx`, the shop, customer, owner and vendor
views listed in the commits, `e2e/brand.spec.js`.

### 4. MIGRATIONS ADDED

None (checked: no file under any `migrations/` folder changed between `435cbd8` and `c879153`).

### 5. ENV VARS ADDED

`CLOUDINARY_URL`, `JOBS_RUN_TOKEN`, `JOBS_RUN_BATCH` (backend); `RENDER_EXTERNAL_HOSTNAME` (set
by Render); GitHub repository variable `API_BASE_URL` and secret `JOBS_RUN_TOKEN`.

### 6. TESTS ADDED

Collected tests at each commit: `435cbd8` 190, `97b9f1a` 194, `8eecc47` 195, `947ed05` 197,
`c879153` 199. At `c879153`: SQLite 197 passed, 2 skipped; PostgreSQL 16 199 passed; Playwright
20 passed (measured on 11 Oct 2026 for the Ayura Step 0 audit). Whether each was shown failing
first is not recorded.

### 7. MANUAL VERIFICATION STEPS

As in `docs/archive/DEPLOY-FREE-noore.md` for Noore.

### 8. ASSUMPTIONS MADE

1. The commit contents are the record; anything not in a commit or a code comment is not claimed.

### 9. KNOWN GAPS (found while reconstructing)

- `render.yaml` runs `./build.sh`, but `build.sh` is committed without the executable bit (fixed for Ayura, K9; Noore still has it).
- A fresh clone has no `backend/static/` (fixed for Ayura, K10; Noore still has it).
- `DEPLOY-FREE.md` step 6 names a workflow ("Run store background jobs") that no longer exists, and says `API_BASE_URL` is a secret without `/api/v1/`; `keep-awake.yml` reads a repository *variable* that includes `/api/v1/`.
- `keep-awake.yml` defaulted to Noore's API address (fixed for Ayura, K8).
- `backend/runtime.txt` says `python-3.9.16` (a Heroku file; Render uses `PYTHON_VERSION` 3.11.9 from `render.yaml`).
- `backups/db-20261004-130927.sqlite3` is tracked although CLAUDE.md says backups are ignored (K14).
- `docs/archive/ROADMAP-v1.md`, referenced for Appendix C and E, was never in the repository.

### 10. NOT DONE AND WHY

Nothing was changed in Noore's repository by this reconstruction.

---

## Decisions taken on the owner's behalf (27 Sep 2026)

The owner delegated all Phase 0 questions ("do what you feel would be best, keep me informed").
These are the decisions. Each can be reversed; the cost of reversing is noted.

| # | Question | Decision | Why | Cost to reverse |
|---|---|---|---|---|
| D1 | Which repo | The uploaded Udemy "Completed Source Code" | Only codebase available | n/a |
| D2 | Foundation phase before Feature 1 | **Yes**, split into F-A (platform + security) and F-B (catalog, inventory, orders) | Live-verified security holes and no stock model | n/a |
| D3 | Database | SQLite stays the local default; **PostgreSQL required for production** and for the Feature 10 concurrency test (that test will be skipped on SQLite, never faked). Selected via `DATABASE_URL`. `psycopg2` replaced by `psycopg2-binary` | Zero-friction Windows dev; honest concurrency testing | Low |
| D4 | Job runner | **DB-backed outbox** (`core.Job`) + `python manage.py run_worker`. No Redis, no Celery | Celery is not supported on Windows; one less service to run and pay for; works on SQLite and Postgres | Medium: handlers are plain idempotent functions, so they can be moved onto Celery later without rewriting them |
| D5 | Ledger / batch ordering | Stock ledger core (Feature 10) and `Batch` (Feature 5) move into **F-B** | Features 1, 3, 5, 6 all move stock; building them on `stock_qty` would be thrown away | n/a |
| D6 | Variants | One `ProductVariant` per product backfilled in F-B. Existing `Size`/`Color` rows are **not** converted yet | The frontend never uses size price (it always sends `product.price`), so sizes are cosmetic today | Low |
| D7 | Money | New tables are **integer paise only**. Legacy Decimal columns are untouched until a dedicated, reversible money-migration phase | Rule 6: never silently change money storage | n/a |
| D8 | Stripe + PayPal | **Kept and hardened** until Razorpay is live, then proposed for removal | Removing them now leaves no way to pay | Low |
| D9 | Owner identity | The owner and their team are Django **staff users** (`is_staff=True`). All vendor-dashboard endpoints are staff-only | Single brand: "vendor dashboard" = owner dashboard | Low |
| D10 | Guest checkout | **Allowed** (carts and orders work without login) | Required for Feature 4 phone-captured carts; standard for Indian D2C | Low |
| D11 | Multi-vendor residue | **Nothing removed.** Removal proposals R1-R21 stand; scheduled after Phase 5 | Rule 4, and the vendor dashboard is the only product-management UI | n/a |
| D12 | Marketplace service fee (5% on every order) | **Not changed in code.** Owner should set `Settings > service fee percentage` to 0 in Django admin | It is pricing data, not code; changing it silently changes customer totals | n/a |
| D13 | GST / tax bug | Not fixed yet (documented). Fixed in the pricing work with the paise migration | Changing tax changes every total | n/a |

**Still blocked on the owner (cannot be decided for you, rule 12):** Razorpay integration docs/samples and account capabilities; WhatsApp Cloud API templates, rate card and webhook samples. These block Phase 1 features [1] and [2], not F-B.

---

## Decisions taken on the owner's behalf (3 Oct 2026, phases G1 and G2)

The owner's instruction for this session: "build it from what source code you have, just fix
it as you feel". The ZIP supplied was the **Phase F-B snapshot** (80 passed, 1 skipped); the
G0 work described in the roadmap was not in it. These are the calls made. Each is reversible.

| # | Question | Decision | Why | Cost to reverse |
|---|---|---|---|---|
| E1 | G0 is missing from the supplied code | Built G1 and G2 on the F-B snapshot and re-did only the G0 items they depend on: the `AddToCart` import casing, MEDIA_ROOT test isolation, a default variant for every new product, paid-order stock holds, the pincode input, and a Playwright smoke suite. **If a separate G0 branch exists elsewhere it will conflict with this code; keep one, not both** | Nothing else to build on | Medium (a merge) |
| E2 | G1 Step 0 | Ran on the supplied `db.sqlite3` after applying its pending F-A/F-B migrations: 4 products, 4 default variants, **0 mismatches**. The result is trivially clean because the variants were created by the backfill moments earlier; it says nothing about any other database | Only database available | n/a |
| E3 | If a price mismatch exists on another database | Not auto-resolved. From G1 on the two can no longer diverge (signals keep them in step), but an old mismatch stays until the owner picks a winner | Choosing silently would change what a customer is charged | n/a |
| E4 | Existing demo amounts (dollars) | Re-labelled as rupees with no conversion. The one legacy order keeps its old service fee and tax as history | Demo data | None |
| E5 | `ProductVariant.options` did not exist | Added as a JSON column (G2), backfilled from the `size` / `color` text columns, which stay | The roadmap builds the picker over it | Low |
| E6 | Existing coupons | Become PERCENT, one use per customer, no total cap, no minimum, no expiry (the roadmap defaults) | Keeps their meaning | Edit in admin |
| E7 | Support email and WhatsApp number | Placeholders, read from `VITE_SUPPORT_EMAIL` / `VITE_WHATSAPP_NUMBER` | Not supplied | Set two env vars |
| E8 | Money column naming | Every legacy Decimal column gets a twin named `<column>_paise`. The roadmap's "subtotal / discount / shipping / tax / unit price / line total" are therefore `sub_total_paise`, `saved_paise`, `shipping_amount_paise`, `tax_fee_paise`, `price_paise`, `total_paise`. No second set of differently-named columns was added | Two columns for one number is a drift risk; one naming rule makes the mirror check mechanical | Low |
| E9 | Mirror writes (A5) | Enforced in `save()` of Cart, CartOrder and CartOrderItem (`store/money_mirror.py`): whichever side is written, the other follows; paise wins if both change | Legacy code, Django admin and old fixtures still write Decimal only | Low |
| E10 | "Do not touch vendor-named code" vs the roadmap's dashboard requirements | `backend/vendor/` is **untouched**. The dashboard price edit reaches the variant through a signal on `Product`; `stock_qty` is made read-only in the serializer. In `frontend/src/views/vendor/` only the roadmap-mandated minimum was changed: "$" to rupees, ledger availability instead of `stock_qty`, and a JS bug that blocked editing any product whose stock was 0. Nothing renamed or removed | Both instructions satisfied | Low |
| E11 | Shipping on order lines | Shipping is one charge per order. `CartOrderItem.shipping_amount` is 0 from G1 on, so the dashboard's revenue figure (`sub_total + shipping_amount` per line) no longer includes shipping | The flat fee cannot be honestly split across lines | Low |
| E12 | Tax base for the carve-out | The whole payable total (goods after discount, plus shipping). Rate is 0 today, so nothing is affected | Needs a CA's confirmation before the rate is ever set (see Known gaps) | One line |
| E13 | Abandoned drafts and coupon caps | A redemption counts while its order is alive and still carries that coupon. Unpaid drafts are expired by a new hourly job after `ORDER_DRAFT_TTL_HOURS` (48), which frees stock, coupon and cart. Card payment is refused for a draft older than TTL minus 25 h | Otherwise an abandoned checkout holds a customer's one coupon use forever | Low |
| E14 | A cart is one cart id | `cart-list` and `cart-detail` now both return exactly the lines of the given cart id (which is what an order is created from). Previously the list merged every cart the user ever had and the totals covered a different subset | The cart, its totals and the order must agree | Low |
| E15 | Stock for dashboard-created products | The `stock_qty` typed when a product is **created** becomes its opening batch in the ledger (as the F-B backfill did). After that, stock is added by adding a Batch in Django admin, which now books the quantity into the ledger | F-B left no way to receive stock from a UI | Low |
| E16 | Seed coupon | `seed_noore` also creates `WELCOME10` (10% off, one per customer) for local testing | The smoke suite needs a coupon | Delete it |

---

## Decisions taken on the owner's behalf (4 Oct 2026, phase G4.5)

The owner supplied a v0 export (`noore-ecommerce-v0-storefront.zip`) and asked for it to be
joined to this backend.

| # | Question | Decision | Why | Cost to reverse |
|---|---|---|---|---|
| J1 | Use the v0 app itself, or its design? | **Its design, ported into the existing storefront.** The v0 export is a Next.js 16 / React 19 mock: every product, price, cart line, order and address in it is hard-coded, nothing calls an API, and it has no product page, no shop page, no search and no account-link page. Wiring it up would have meant rewriting all the store logic in a second framework and running a second server. Instead its colours, type, layout and components were rebuilt on the pages that already work | Keeps the cart, coupons, Razorpay, COD, reviews, reorder, the tests and the deploy setup | Medium |
| J2 | Styling technology | Tailwind CSS 4 (what v0 uses) added to the Vite app. One theme file, `frontend/src/theme/noore.css`, holds every colour and typeface as named tokens; no component contains a hex code | The roadmap asks for one theme file so the skin can change without touching components | Low |
| J3 | Bootstrap | No longer loaded on every page. It is loaded only while the admin area or one of the few un-redesigned account pages is open (`layouts/LegacyStyles.jsx`) | Otherwise Bootstrap restyles the new storefront | Low |
| J4 | v0's numbers and claims | Not used. v0 shows free shipping above Rs 2,500, Rs 180 shipping, a NOORE10 code, a newsletter, a journal, Instagram and Pinterest, and says the candles are "natural soy wax", "cotton wick" and "made in India". The storefront shows the real shipping figures from the server, has no newsletter or journal (nothing behind them), and makes no ingredient or origin claim | Shipping must match what checkout charges; product claims are the owner's to make and stand behind | Add copy when supplied |
| J5 | Logo and favicon | The v0 export's icon files are v0's own logo, so they were not used. The logo is the wordmark "NOORE" in the design's serif; the favicon is a simple "N" on the brand's dark colour (`frontend/public/favicon.svg`) | No Noore logo file was supplied | Replace one file |
| J6 | "Do not touch vendor-named code" | Lifted for this phase only as far as the roadmap's G4.5 requires, since the owner started G4.5 by sending the design. Dashboard files were **not** renamed or moved: the routes moved to `/admin-area/`, and old `/vendor/...` and `/owner/...` addresses redirect staff there. `backend/vendor/` is untouched | Smallest change that meets the acceptance | Low |
| J7 | Who is staff, in the browser | The sign-in token now carries `is_staff`. It only decides whether the "Admin" link is shown; every owner endpoint still checks the database | The header needs to know without an extra request | Low |
| J8 | The public "shop by seller" page (`/vendor/<slug>/`) | No longer routed. It is a marketplace page with no place in a single-brand store | Roadmap R21 | Re-add one route |
| J9 | Pages not redesigned | Wishlist, account settings, notifications, forgot/reset password, and the legacy Stripe success and invoice pages keep their old Bootstrap look inside the new header and footer. The whole admin area keeps its look | v0 gave no design for most of them; they work | Per page |

---

## PHASE G4.5 — Brand and storefront (COMPLETED, with placeholders listed)

### 1. PHASE COMPLETED

**G4.5**, branch `phase/G4.5-brand`.

- **The storefront now looks like Noore**: cream, ink and clay palette, serif headings, the v0
  layout for header, footer, home, cart, checkout, order pages and forms.
- **New pages**: home (hero, collection, story strip, shipping and payment facts), shop with
  search and sorting, About, a proper not-found page.
- **Redesigned pages**: product (photo gallery with thumbnails, size picker, price, stock,
  reviews), cart, checkout, order confirmation, sign in, register, create-account link, sign
  out, my orders, order detail (with progress steps), policies, contact.
- **Listing photos share one ratio** (4:5) and a missing photo shows a plain block, never a
  broken-image icon.
- **No marketplace wording**: the header "Vendor" menu, seller names, the seller tab and seller
  shop links are gone from everything a shopper can reach.
- **Admin area**: the dashboard lives at `/admin-area/`. Staff see one "Admin" link. Everyone
  else sees no dashboard link, and dashboard addresses show the not-found page.
- **Bug D17 fixed**: an ordinary customer is never sent to a shop sign-up page.
- **Title, favicon and description** are Noore's.

### 2. FILES CREATED

- `frontend/src/theme/noore.css` — the one theme file
- `frontend/postcss.config.js`, `frontend/public/favicon.svg`
- `frontend/src/layouts/LegacyStyles.jsx`
- `frontend/src/views/ui/noore.jsx` — `PageIntro`, `BackLink`, `Field`, `Loading`, `Photo`, `ProductCard`
- `frontend/src/views/base/NotFound.jsx`, `frontend/src/views/policy/About.jsx`
- `frontend/e2e/brand.spec.js`

### 3. FILES MODIFIED

- `frontend/index.html` — title, description, favicon; Bootstrap no longer loaded globally
- `frontend/src/main.jsx`, `frontend/src/App.jsx` (rewritten: storefront, legacy and admin-area layouts and routes)
- `frontend/src/views/base/StoreHeader.jsx`, `StoreFooter.jsx` (rewritten)
- `frontend/src/views/shop/home.jsx`, `Products.jsx` (rewritten as home and shop), `ProductDetail.jsx`, `Cart.jsx`, `Checkout.jsx`, `OrderConfirmation.jsx` (same logic, new markup)
- `frontend/src/views/auth/login.jsx`, `register.jsx`, `logout.jsx`, `ClaimAccount.jsx`
- `frontend/src/views/customer/Orders.jsx`, `OrderDetail.jsx`, `BuyAgainButton.jsx`
- `frontend/src/views/policy/PolicyPage.jsx`, `Contact.jsx`
- `frontend/src/store/auth.js` — `is_staff`, `full_name`
- `frontend/package.json`, `package-lock.json` — `tailwindcss`, `@tailwindcss/postcss`, `postcss` (dev), `lucide-react`
- `frontend/playwright.config.js`, `frontend/e2e/storefront.spec.js`, `frontend/e2e/checkout.spec.js` — new button and field names
- `backend/userauths/serializer.py` — `is_staff` claim in the sign-in token
- `backend/tests/test_launch.py` — test for that claim

No longer routed, left in place (removal proposals, rule 4): `views/shop/Search.jsx`,
`views/vendor/Shop.jsx`, `views/auth/private.jsx`, `views/auth/dashboard.jsx`.

### 4. MIGRATIONS ADDED

None.

### 5. ENV VARS ADDED

None. (`VITE_STORE_NAME`, `VITE_SUPPORT_EMAIL` and `VITE_WHATSAPP_NUMBER` from G2 are now used throughout the header, footer and titles.)

### 6. TESTS ADDED

Playwright `frontend/e2e/brand.spec.js`, 7 tests; the whole suite is **14 passed** in real Chromium:

    npx playwright test

- A logged-out crawl follows every internal link from the home page and fails if "vendor" appears in any page's text, title, link, image description or label. It visited the home page, shop, every product, every policy, About, Contact, cart and sign-in.
- Every page has the Noore title, favicon and logo; the announcement bar shows the real free-shipping threshold.
- A signed-in customer sees no admin link, and `/admin-area/...`, `/vendor/...` (including `/vendor/register/`) and `/owner/...` all show the not-found page without redirecting.
- A signed-out visitor gets the not-found page for the same addresses.
- Staff click "Admin", land on `/admin-area/dashboard/`, open all eleven dashboard screens without a script error, and old `/vendor/...` and `/owner/...` addresses redirect to the new ones.
- Home, About, shop and product page at phone width (390) and desktop width (1280): a heading is visible, nothing overflows sideways, and listing photos share the 4:5 ratio.

The existing 7 browser tests (pricing, COD, Razorpay hand-off, owner flow, reorder, review) pass unchanged in behaviour against the new pages.

Backend: 1 new test (the staff claim, and that the API does not trust it).

    python -m pytest -q   ->  178 passed, 2 skipped (180 collected)

Shown failing first: before this phase `brand.spec.js` fails on its first assertions (the page title was "Django React Ecommerce", the header had a "Vendor" menu, `/admin-area/` did not exist).

### 7. MANUAL VERIFICATION STEPS

    cd backend
    .\venv\Scripts\Activate.ps1
    python -m pytest -q
    python manage.py runserver

    cd frontend
    npm install
    npm run build
    npm run dev

`npm install` is required: Tailwind and the icon set are new.

1. http://localhost:5173 : the Noore home page. Open a candle, pick a size, add to bag, go through checkout.
2. Shrink the window to phone width: the menu collapses, nothing scrolls sideways.
3. Sign in as an ordinary customer: no "Admin" link. Type `/vendor/dashboard/` in the address bar: not-found page.
4. Sign in as the owner: "Admin" appears in the header and opens `/admin-area/dashboard/`.
5. To change the look: edit a colour in `frontend/src/theme/noore.css` (for example `--color-clay`) and every page follows.

### 8. ASSUMPTIONS MADE

1. Decisions J1 to J9.
2. Fonts are the design's system fonts (Georgia for headings, Arial for text); no web font is downloaded.
3. The home page hero uses the first featured product's photo; "the collection" shows up to eight featured products, or all products if none is featured.
4. Listing cards link to the product page ("Choose a size"); adding to the bag happens there, where the size is chosen.
5. The product page shows details and reviews stacked on one page instead of in tabs.
6. Search lives at `/shop?query=`; the old `/search?query=` address still works.
7. The wishlist button on the product page is shown only to signed-in customers.
8. "My orders" shows a plain-language status (Placed, Being packed, On its way, Delivered, Cancelled, Refunded).
9. API addresses still contain the word "vendor" (for example `/api/v1/vendor/...`). They are visible only in the browser's network tab; the roadmap makes renaming them a separate decision.

### 8b. FOLLOW-UP (4 Oct 2026): the shop sign-up redirect

Reported by the owner: opening `/admin-area/product/new/` as a freshly created superuser
landed on a "Register Vendor Account" form. Cause: fifteen dashboard pages still carried the
marketplace line `if (vendor_id === 0) window.location.href = '/vendor/register/'`, and a new
superuser does not own the shop until `claim_shop` is run. G4.5 had stopped ordinary customers
reaching that form, but not staff.

- The redirect is removed from all fifteen pages, and the shop sign-up route is gone
  (`views/vendor/VendorRegister.jsx` stays in the repo as a removal proposal, rule 4).
- A staff account with no shop now gets `views/owner/ShopNotReady.jsx`, which names the
  `claim_shop` command, instead of any form. The owner-order and review screens, which need no
  shop, still open.
- Every dashboard link now points at `/admin-area/...` directly, so clicking no longer bounces
  through a redirect. Old addresses typed by hand still redirect staff.
- New browser test: a staff account whose token says it owns no shop sees the explanation, stays
  on the address it asked for, and never sees a sign-up form. Suite: 15 passed.

### 9. KNOWN GAPS

- **About page and policy pages are placeholder copy** and say so on the page.
- **No real logo, favicon artwork or product photos.** The seeded products have no photo, so listings show plain blocks until photos are uploaded.
- **Home page marketing lines** ("Light the beautiful moment", "Made for the in-between") come from the v0 design; replace them if they are not the brand's voice.
- Wishlist, account settings, notifications, password reset and the whole admin area are not redesigned (J9). Inside the admin area, Bootstrap pages sit under the Noore header; their look differs slightly from before because Bootstrap is now loaded on demand.
- The admin area's own links still point at `/vendor/...` and redirect; there is a brief flash on each click.
- No newsletter, journal or social links (J4).
- The built CSS and JS are larger than before (one bundle for storefront and admin area).

### 10. NOT DONE AND WHY

- **Using the v0 Next.js project as the frontend**: J1.
- **Renaming or deleting dashboard files, or renaming API paths**: rule 4 and the roadmap's stop condition.
- **Redesigning the admin area**: not in the roadmap.
- **Real copy, logo and photos**: the owner supplies them.

---

## Decisions taken on the owner's behalf (3 Oct 2026, phase G5 part A)

The owner said to continue. G4.5 is still on hold (it needs the design decision and assets), so
this session built every part of G5 that needs nothing from the owner. The rest of G5 ("part B")
needs a domain, a server, live Razorpay keys and an email provider.

| # | Question | Decision | Why | Cost to reverse |
|---|---|---|---|---|
| H1 | Error reporting | Emails to `ERROR_REPORT_EMAILS` from a small handler in `core/error_email.py`: masked message and traceback only, one email per distinct error per five minutes. No third-party service, no new dependency | Django's built-in error email includes the request body and settings, which would leak customer data; a hosted service needs an account the owner has not chosen | Swap the handler |
| H2 | Shared cache | Django's database cache, on by default when `DEBUG` is off. Needs `createcachetable` once | The roadmap names it; no Redis to run | One env var |
| H3 | HSTS | On in production, starting at one hour. Raising it to a year is a runbook step | It cannot be undone quickly if HTTPS breaks | One env var |
| H4 | Link previews for product pages | In production the web server sends `/detail/<slug>` to Django, which returns the built storefront page with the product's title, description, price and image in the `<head>` | The storefront is a single-page app; without this every shared link previews as a blank generic page | Remove one route |
| H5 | Health check | `GET /api/v1/health/`; `?strict=1` also fails when the worker has not finished a job for five minutes | A dead worker silently stops emails and payment reconciliation | Low |
| H6 | `npm audit` | Applied every non-breaking fix and moved `react-router-dom` 6.10.0 to 6.30.6 (same major). 56 findings became 39. The remaining ones need major upgrades and are listed under Known gaps | The suite and build pass after the changes | `git revert` |
| H7 | Swagger / ReDoc pages | Left in place. In production the web server does not route to them, so they are not reachable | Rule 4: not removed without approval | n/a |
| H8 | Deployed-site smoke test | `E2E_BASE_URL=https://... npx playwright test` runs only `e2e/production.spec.js`, which needs no seed data and places one COD order named "SMOKE TEST - please cancel" | The roadmap's "Playwright against production with a COD order that is then cancelled" | Low |

---

## PHASE G5 (part A) — Launch preparation (COMPLETED; part B needs the owner)

### 1. PHASE COMPLETED

**G5 part A**, branch `phase/G5a-launch-prep`. Everything in G5 that does not need a domain,
server, live keys or the owner's accounts.

- **Production settings**: HTTPS redirect, secure cookies, HSTS, proxy-aware scheme, clickjacking
  protection. Django's own deployment check passes.
- **PostgreSQL proven**: the whole suite passes on PostgreSQL 16.2 with nothing skipped, including
  the two concurrency tests that had never been run (stock for the last unit; a capped coupon).
- **Rate limits shared between server processes** (bug D14).
- **Deployment files** in `deploy/`: Caddy configuration, systemd units for web, worker and the
  nightly backup, backup and restore scripts, a production env template.
- **Backups**: nightly database and media, 14 days kept, off-site copy when configured; a restore
  script that restores into a scratch database and prints row counts.
- **Health check** for uptime monitors, **error emails** with personal data masked.
- **Search engines and sharing**: `robots.txt`, `sitemap.xml`, per-page browser titles, and
  product links that preview with the product's own title, price and image.
- **`npm audit`** triaged (bug D16): 56 findings down to 39.
- **Runbook** `docs/DEPLOY.md`: install, deploy, roll back, back up, restore, rotate a secret,
  monitor, go-live checklist.
- A **deployed-site smoke test**.

### 2. FILES CREATED

- `backend/core/health.py`, `backend/core/seo.py`, `backend/core/error_email.py`
- `backend/tests/test_launch.py`
- `deploy/Caddyfile`, `deploy/noore-web.service`, `deploy/noore-worker.service`, `deploy/noore-backup.service`, `deploy/noore-backup.timer`
- `deploy/backup.sh`, `deploy/restore.sh`, `deploy/backup.env.example`, `deploy/env.production.example`
- `docs/DEPLOY.md`
- `frontend/src/utils/usePageTitle.js`, `frontend/e2e/production.spec.js`

### 3. FILES MODIFIED

- `backend/backend/settings.py` — production security block, `CACHES`, error-report logging handler, `WORKER_STALE_AFTER_SECONDS`, `FRONTEND_INDEX_PATH`
- `backend/backend/urls.py` — `/robots.txt`, `/sitemap.xml`, `/detail/<slug>`
- `backend/api/urls.py` — `/api/v1/health/`
- `backend/.env.example` — the new variables
- `frontend/playwright.config.js` — `E2E_BASE_URL` mode
- `frontend/package.json`, `frontend/package-lock.json` — security updates (H6)
- `frontend/src/views/shop/ProductDetail.jsx`, `Cart.jsx`, `Checkout.jsx`, `OrderConfirmation.jsx`, `frontend/src/views/policy/PolicyPage.jsx`, `Contact.jsx` — page titles

### 4. MIGRATIONS ADDED

None. One new setup command for production only, which creates the cache table (it is not a
Django migration and holds no business data):

    python manage.py createcachetable

Undo: `DROP TABLE django_cache;` and set `DJANGO_CACHE=locmem`.

### 5. ENV VARS ADDED

Backend, all optional except where marked: `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`,
`SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`, `DJANGO_CACHE`,
`ERROR_REPORT_EMAILS` (**needs the owner's address in production**),
`ERROR_REPORT_MIN_INTERVAL_SECONDS`, `WORKER_STALE_AFTER_SECONDS`, `FRONTEND_INDEX_PATH`
(set in production).

Deployment: `SITE_ADDRESS`, `APP_ROOT` (Caddy); `BACKUP_DIR`, `MEDIA_DIR`, `BACKUP_KEEP_DAYS`,
`BACKUP_REMOTE` (**needs the owner's value**), `ADMIN_DATABASE_URL` (restore script).

Smoke suite: `E2E_BASE_URL`.

### 6. TESTS ADDED

`backend/tests/test_launch.py`, 12 tests. Shown failing first: against the G3/G4 commit, 11 fail
and 1 passes (the one that only checks development keeps its cache).

    python -m pytest tests/test_launch.py -q   ->  12 passed
    python -m pytest -q                        ->  177 passed, 2 skipped   (SQLite; 179 collected)

On PostgreSQL 16.2 (local server in the build container):

    $env:DATABASE_URL = "postgres://ecom:ecom@127.0.0.1:5432/ecom"
    python -m pytest -q                        ->  179 passed, 0 skipped

Covers: production settings are secure by default and `manage.py check --deploy --fail-level
WARNING` passes; rate-limit counters are stored in the shared database cache and a sixth request
is refused; errors are emailed once, masked, and a broken mail server never raises; the health
check for database, cache and worker, and it is never rate-limited; `robots.txt` hides private
areas; the sitemap lists published products and public pages only; product pages get escaped
title, description, canonical link, price and image, the app still boots, and unknown or
unpublished products get the plain page.

Playwright: 7 passed (local suite). Deployed-site spec: 2 passed against the local
production-like stack through Caddy.

### 7. MANUAL VERIFICATION STEPS

Nothing changes in day-to-day development; the usual commands still work. To see the new pieces:

    cd backend
    .\venv\Scripts\Activate.ps1
    python -m pytest -q
    python manage.py runserver

Then open http://127.0.0.1:8000/api/v1/health/ , http://127.0.0.1:8000/robots.txt and
http://127.0.0.1:8000/sitemap.xml . With the worker running in a second terminal,
http://127.0.0.1:8000/api/v1/health/?strict=1 answers ok; stop the worker, wait five minutes, and
it answers 503.

Production is in `docs/DEPLOY.md`.

**Drills run in the build session** (local production-like stack, scratch data):

| Drill | Result |
|---|---|
| Caddy configuration | `caddy validate`: valid. Storefront, deep links, API, admin, static, `/detail/...`, `robots.txt`, `sitemap.xml` all 200; a missing asset 404 |
| Stop web and worker | health check 502; started again, `?strict=1` ok |
| Backup | 0.53 s; database dump 200 KB, media 3.4 MB |
| Restore into a scratch database | under 1 s; products 3, variants 9, orders 1, stock movements 9, audit rows 18, migrations 88, identical to the live counts |

These are on a tiny scratch database on the build machine. They prove the scripts work; they are
**not** the production restore drill the roadmap requires. That is done on the real server.

### 8. ASSUMPTIONS MADE

1. Decisions H1 to H8.
2. One server, Ubuntu 24.04, paths under `/srv/noore`, service user `noore`, PostgreSQL on the same machine, Caddy in front.
3. Media stays on the server's disk (roadmap A7) and is in the nightly backup.
4. The off-site copy uses `rclone`, so the owner can choose any storage provider.
5. The sitemap has no last-modified dates (products record only a creation date).
6. Link-preview pages are produced only for published products; anything else gets the unchanged app page.
7. `og:image` is the product's main image at its uploaded size.
8. The health check exposes only booleans and one number; nothing secret or personal.
9. Gunicorn runs 3 workers; a small VPS is assumed.
10. The systemd units were written from the standard unit format and not executed (no systemd in the build container).

### 9. KNOWN GAPS

- **Not deployed.** No domain, server, HTTPS certificate, live keys or real email were available. `docs/DEPLOY.md` ends with exactly what is and is not proven.
- **`npm audit`: 39 findings remain**, none in what a shopper's browser can be attacked through as far as the advisories describe:
  - 34 in the CKEditor 40 packages (and `lodash-es` beneath them). The editor is used only on the owner's add/edit product screens. The offered fix is a major downgrade to version 39; the real fix is an upgrade to a current CKEditor, which is its own piece of work.
  - `vite` 4 and `esbuild` (5 findings): development-server issues. They do not ship in the built site. The fix is a major upgrade to Vite 8.
  - `react-router` 6 (2 moderate): an open redirect through a backslash in a link target, and a server-rendering issue. This app does not server-render and never builds a link from user-typed text. The fix is a major upgrade to version 7.
- The Swagger and ReDoc pages still exist (H7).
- No CDN and no image resizing; product photos are served as uploaded.
- Throttle counters in the database cache are not cleaned up automatically beyond Django's own culling (300 entries by default).
- `CLAUDE.md` remains the owner's unchanged copy.

### 10. NOT DONE AND WHY (G5 part B, needs the owner)

- Buying the domain; pointing DNS at a server.
- The server itself, and running `docs/DEPLOY.md` on it.
- Razorpay live keys, the live webhook, and one real order paid, dispatched, delivered and refunded.
- Email provider, SPF and DKIM; confirming mail lands in an inbox.
- The off-site backup destination, and the restore drill on production data with timings.
- A reboot test on the real server.
- Final photos, prices, MRP, weights, policy copy; real unit cost on each batch (bug D15).
- The CA or lawyer's answers on product declarations, published contact details and privacy.
- G4.5 branding: still waiting for the design decision.

---

## Decisions taken on the owner's behalf (3 Oct 2026, phases G3 and G4)

The owner's instruction: "you just start building", and to combine phases. G3 and G4 were
built together in one session. G4.5 (branding) and G5 (launch) were not started: G4.5 was
explicitly put on hold by the owner and needs a design decision, G5 needs a domain and a server.

| # | Question | Decision | Why | Cost to reverse |
|---|---|---|---|---|
| F1 | Razorpay documentation (rule 12) | Read from Razorpay's own published pages on 3 Oct 2026, not from memory: `razorpay.com/docs/developer-tools/integrations/standard-checkout` (create order, checkout options, payment signature, payment states, webhook events) and `razorpay.com/docs/webhooks/validate-test` (webhook signature, `x-razorpay-event-id`, tunnel advice). The sources and every shape used are listed at the top of `backend/store/payments/razorpay.py` | The owner said to start; the roadmap allows "current official documentation pages" | n/a |
| F2 | Which event means "paid" | `payment.captured` only. The documentation calls `captured` the state in which it is "safe to deliver". `payment.authorized`, `order.paid` and every other event are acknowledged and ignored | Unambiguous in the documentation | One constant |
| F3 | Webhook handling | Verified and applied inside the request, in one database transaction, with no call out to Razorpay (so it answers well inside Razorpay's 5-second limit and does not depend on the worker). The documentation's "discard events older than 5 minutes" is **not** applied: it would also discard Razorpay's own retries after any downtime. Replay is prevented instead by claiming each Razorpay order id exactly once | A customer who has paid must not be stranded by a slow or restarted server | Low |
| F4 | Fields read from the webhook | `payload.payment.entity.{id, order_id, amount, currency}`. If any is missing the event is refused (400) rather than guessed; the reconcile job then confirms the order from the Fetch Order API, whose response shape is fully documented | Fail closed | Low |
| F5 | Capture | Orders are created with `"capture": "automatic"` (a documented Create Order parameter) so an authorised payment is captured without relying on a dashboard setting | An uncaptured payment is auto-refunded by Razorpay | One line |
| F6 | "UPI first inside the Razorpay window" | **Not done.** The pages read do not describe how to order payment methods, and nothing was invented. Razorpay's default order is used | Rule 12 | Add when the owner supplies that page |
| F7 | Owner screens | New pages under `frontend/src/views/owner/` and new endpoints under `/api/v1/owner/` (in `backend/store/owner_views.py`). `backend/vendor/` is untouched; `vendor/Sidebar.jsx` gained two links. The old "Orders" screen still lists paid orders only, so the new "Handle orders" screen is the one to use | COD orders awaiting cash never appeared on the old screen | Low |
| F8 | Late payment with no stock left | The order is marked paid (the money really was received) **and** flagged `needs_attention`; a flagged order cannot be shipped until the owner clears the flag. A payment for an order that had already expired or been cancelled is flagged and left expired/cancelled | "Never silently marked paid and unshippable" | Low |
| F9 | A finished order and the browser's cart id | Once an order is paid or placed as COD, the same browser cart starts a new order. Previously the cart id stayed tied to the paid order and the next checkout was refused | The storefront keeps one cart id per browser | Low |
| F10 | Customer order history | Shows paid, COD awaiting cash, refunded and cancelled orders. Unpaid checkout drafts are not shown | A COD order was invisible to its own customer | Low |
| F11 | Guest account link when the email already has an account | The verified guest orders are attached to that account, but its password is **not** changed by the link | The link proves the mailbox, but silently resetting a password is what "forgot password" is for | Low |
| F12 | Reorder | Signed-in owner of the order only. A guest order's id alone cannot be used to copy its contents; the guest creates an account first | The order id is a checkout capability, not an identity | Low |
| F13 | Rejected reviews | Stay in the database (status REJECTED) and still count as that customer's one review for the product | Stops a rejected spammer simply re-posting | Low |
| F14 | Review-request email | Sent once, `REVIEW_REQUEST_DELAY_DAYS` after **every line** of the order is delivered, to guests as well (who are pointed at their orders page and the account link) | "Once per order" | Low |
| F15 | Smoke-suite accounts | `python manage.py seed_e2e` creates an owner and a customer with a fixed throwaway password. It refuses to run unless DEBUG is on **and** the database file is `e2e.sqlite3` | The suite must sign in; a known password must never reach a real database | Delete the command |

---

## PHASE G4 — Reviews and one-tap reorder (COMPLETED)

### 1. PHASE COMPLETED

**G4**, built together with G3 on branch `phase/G3-G4-payments-reviews`.

- **Verified reviews.** Only a signed-in customer with a delivered line for the product can
  review it, once. The product page shows the form only to them and tells everyone else why not.
- **Moderation.** New reviews wait in the owner's "Review moderation" screen. Only approved
  reviews are public or count towards the star rating. The screen says rejecting is for abuse
  and spam, not low ratings. Each decision is audited.
- **Existing reviews** were marked approved by a migration, so nothing vanished.
- **One review-request email** per order, 7 days after delivery. No reminders.
- **Buy again** on the order list and order page: puts the order's items back in the cart at
  today's prices and stock, says what was reduced or unavailable, and opens the cart. It never
  places an order.

### 2. FILES CREATED

- `backend/store/migrations/0037_review_moderation_fields.py`, `0038_approve_existing_reviews.py`, `0039_review_one_per_user_per_product.py`
- `backend/tests/test_reviews_reorder.py`
- `frontend/src/views/owner/OwnerReviews.jsx`
- `frontend/src/views/customer/BuyAgainButton.jsx`

### 3. FILES MODIFIED

- `backend/store/models.py` — `Review.order_item`, `status`, `moderated_by`, `moderated_at`, unique rule; rating and count use approved reviews only; `active` follows `status`
- `backend/store/views.py` — `review_eligibility`, `ReviewEligibilityView`, review creation rules, public list of approved reviews only, `put_in_cart` (the shared cart path), `ReorderView`
- `backend/store/owner_views.py` — moderation queue and approve/reject
- `backend/store/jobs.py` — `store.queue_review_requests` (hourly)
- `backend/store/emails.py` — the review-request email
- `backend/store/admin.py` — review status column and filter
- `backend/api/urls.py`, `backend/backend/settings.py`, `backend/.env.example`
- `backend/conftest.py` — `delivered_order` fixture; `backend/tests/test_security.py` — the review test now gives the reviewer a delivered order
- `frontend/src/views/shop/ProductDetail.jsx`, `frontend/src/views/customer/Orders.jsx`, `OrderDetail.jsx` (also fixes a hard-coded order number in its heading), `frontend/src/App.jsx`, `frontend/src/views/vendor/Sidebar.jsx`

### 4. MIGRATIONS ADDED

| Migration | What | Reverse |
|---|---|---|
| `store.0037_review_moderation_fields` | four columns on Review | drops them |
| `store.0038_approve_existing_reviews` | existing reviews become APPROVED | back to PENDING |
| `store.0039_review_one_per_user_per_product` | checks for duplicates (stops with a clear message if any), then adds the unique rule | removes the rule |

Apply: `python manage.py migrate`. Roll back G4 only: `python manage.py migrate store 0036`.
Verified on a copy of the supplied database (2 reviews, both approved after apply, both kept after rollback).

### 5. ENV VARS ADDED

- `REVIEW_REQUEST_DELAY_DAYS` (optional, default `7`)

### 6. TESTS ADDED

`backend/tests/test_reviews_reorder.py`, 9 tests. Shown failing first against the G2 commit
(`ImportError: cannot import name 'queue_review_requests'`).

    python -m pytest tests/test_reviews_reorder.py -q   ->  9 passed

Covers: no delivered line gives 403 (never bought, not yet delivered, someone else's order);
pending and rejected reviews are never public and never move the average; a low rating that
is approved does move it; a second review is refused (API and database); moderation is staff
only and audited; the eligibility answer for each case; one review-request email, not before
the delay; reorder of a three-line order with one line sold out adds two and reports the
third, at today's prices, holding stock, placing no order, safe to press twice; short stock is
reduced and a discontinued variant is skipped; reorder is refused for other users and guests.

Playwright: the reorder-from-order-history scenario is the last part of
`frontend/e2e/checkout.spec.js` (see G3, section 6).

### 7. MANUAL VERIFICATION STEPS

After the G3 steps below: sign in as a customer whose order you delivered, open the product,
Review tab, submit. It does not appear. As the owner open Review moderation, approve it; it
appears and the stars update. On My Orders press Buy again; the cart opens with today's prices.

### 8. ASSUMPTIONS MADE

1. Decisions F12 to F14.
2. "Delivered line" means an order line with delivery status Delivered on an order that is not cancelled and belongs to the signed-in user.
3. Editing or deleting one's own review is not offered.
4. Reorder sets each line to the order's quantity (it does not add to what is already in the cart).
5. The legacy vendor review screens still work but are not the moderation queue.

### 9. KNOWN GAPS

- No reply-to-review and no photos.
- The review-request email needs the worker running.
- Django admin can still change a review's status directly (it is then not written to the audit log).

### 10. NOT DONE AND WHY

- Review reminders: the roadmap says none.
- Reorder placing the order itself: the roadmap forbids it.

---

## PHASE G3 — Razorpay test mode and COD (COMPLETED)

### 1. PHASE COMPLETED

**G3**, branch `phase/G3-G4-payments-reviews`.

- **Checkout has a payment choice**: "UPI / Card / Netbanking" (default, Razorpay) or "Cash on delivery". No COD fee.
- **Online payment.** The server creates the Razorpay order for the stored total, the browser
  opens Razorpay, and the customer lands on a "Confirming your payment" page. The order becomes
  paid **only** when Razorpay's signed server notification (webhook) arrives, with the right
  amount and currency. A forged, repeated or mismatched notification changes nothing.
- **Safety net.** A background job asks Razorpay about orders still unconfirmed after 3 minutes, so a missed webhook cannot strand a paid order.
- **Cash on Delivery.** The order is placed with nothing charged and its stock kept. The owner
  presses **Confirm COD** after speaking to the customer; only then can it be shipped. On
  delivery the owner presses **Mark cash collected**.
- **Owner "Handle orders" screen**: confirm COD, add courier and tracking, mark packing / shipped / arrived / delivered, cancel, record a refund. Stock leaves the ledger exactly once, on dispatch.
- **Order emails**, each sent once: order placed, payment received, shipped (with tracking), cancelled.
- **Guests can create an account** from the confirmation page; the link goes to the order's email and attaches that email's orders once used.
- **Stripe and PayPal** are switched off (code and tests remain).
- `CartOrder.oid` is now unique (bug D12).

### 2. FILES CREATED

- `backend/store/payments/__init__.py`, `base.py`, `razorpay.py`, `legacy.py`
- `backend/store/payment_views.py`, `backend/store/owner_views.py`
- `backend/store/emails.py`, `backend/store/account_claim.py`
- `backend/templates/email/order_update.txt`, `order_update.html`
- `backend/store/migrations/0035_cartorder_payment_fields.py`, `0036_cartorder_oid_unique.py`
- `backend/core/management/commands/seed_e2e.py`
- `backend/tests/test_payments.py`
- `frontend/src/utils/razorpay.js`
- `frontend/src/views/shop/OrderConfirmation.jsx`, `frontend/src/views/auth/ClaimAccount.jsx`
- `frontend/src/views/owner/OwnerOrders.jsx`, `OwnerOrderDetail.jsx`
- `frontend/e2e/checkout.spec.js`

### 3. FILES MODIFIED

- `backend/store/models.py` — `payment_provider`, `razorpay_order_id`, `razorpay_payment_id`, `cod_confirmed_at`, `cod_confirmed_by`, `needs_attention`, `delivered_at`; `oid` unique
- `backend/store/order_state.py` — `place_cod_order`, `confirm_cod`, `advance_order_delivery`; paid-with-no-stock sets `needs_attention`
- `backend/store/views.py` — Stripe and PayPal refuse unless enabled; a finished order frees the cart (F9)
- `backend/store/jobs.py` — `store.reconcile_pending_payments` (every 2 minutes)
- `backend/customer/views.py` — order history shows placed orders (F10)
- `backend/store/apps.py`, `backend/store/admin.py`, `backend/api/urls.py`, `backend/backend/settings.py`, `backend/.env.example`
- `backend/conftest.py` — `legacy_providers` fixture; `backend/tests/test_security.py`, `backend/tests/test_pricing.py` — the five Stripe/PayPal tests switch those providers on
- `frontend/src/views/shop/Checkout.jsx` — payment-method selector, Razorpay hand-off, COD
- `frontend/src/App.jsx`, `frontend/src/views/vendor/Sidebar.jsx`
- `frontend/playwright.config.js`, `frontend/e2e/storefront.spec.js`

### 4. MIGRATIONS ADDED

| Migration | What | Reverse |
|---|---|---|
| `store.0035_cartorder_payment_fields` | seven columns on CartOrder | drops them |
| `store.0036_cartorder_oid_unique` | checks for duplicate order ids (stops with a clear message if any), then makes `oid` unique | removes the constraint |

Apply: `python manage.py migrate`. Roll back G3 and G4: `python manage.py migrate store 0034`.
Verified on a copy of the supplied database: no duplicate order ids; apply, roll back, re-apply clean.

### 5. ENV VARS ADDED

Backend (`backend/.env.example`):

- `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` — **need the owner's test keys**
- `RAZORPAY_WEBHOOK_SECRET` — **needs the owner's value** (chosen when adding the webhook; not the key secret)
- `RAZORPAY_API_BASE` (default `https://api.razorpay.com`)
- `ENABLED_PAYMENT_PROVIDERS` (default `razorpay,cod`)
- `PAYMENT_RECONCILE_AFTER_MINUTES` (default `3`)
- `STORE_NAME` (default `Noore Candles`)
- `ACCOUNT_CLAIM_LINK_HOURS` (default `48`)

No frontend variable: the public key id reaches the browser from the server with each payment.

### 6. TESTS ADDED

`backend/tests/test_payments.py`, 20 tests. Shown failing first against the G2 commit
(`ImportError: cannot import name 'reconcile_pending_payments'`).

    python -m pytest tests/test_payments.py -q   ->  20 passed
    python -m pytest -q                          ->  165 passed, 2 skipped (167 collected)

No test contacts Razorpay. The HTTP call is stubbed with the documented order entity, and
webhooks are signed in the test exactly as documented.

Covers every acceptance line: a forged, unsigned or wrongly-keyed webhook is rejected and
changes nothing; the same webhook twice (and a second event for the same payment) marks paid
once and sends one email; wrong amount or currency is rejected; returning from checkout with a
valid signature leaves the order unpaid, and a signature for a spoofed order id fails; without
a webhook the order stays unpaid until the reconcile job confirms it (not when Razorpay says
unpaid or part-paid); a COD order cannot be dispatched before Confirm COD and can after; stock
leaves the ledger exactly once, prepaid and COD; Stripe and PayPal are off by default and
their own tests still pass; no secret appears in any response. Also: late payment re-reserves,
or flags the order; COD refused cleanly when stock has gone; owner endpoints are staff only;
guest account link end to end, tampered and expired links refused.

Playwright, **7 passed in real Chromium** (`npx playwright test`): the four G1/G2 tests, plus
COD checkout end to end with the guest account link; the online-payment hand-off (our server's
"start" answer and Razorpay's script are stubbed, and the options passed to Razorpay are
checked); and one long scenario: customer orders COD, owner is refused shipping, confirms COD,
ships, delivers, collects cash, customer buys again and writes a review that waits for moderation.

### 7. MANUAL VERIFICATION STEPS

    New-Item -ItemType Directory -Force -Path backups | Out-Null
    Copy-Item backend\db.sqlite3 "backups\db-$(Get-Date -Format 'yyyyMMdd-HHmmss').sqlite3"
    cd backend
    .\venv\Scripts\Activate.ps1
    python manage.py migrate
    python -m pytest -q
    python manage.py runserver

Second terminal (emails, payment reconcile, draft expiry all need this):

    cd backend
    .\venv\Scripts\Activate.ps1
    python manage.py run_worker

Third terminal: `cd frontend`, `npm install`, `npm run build`, `npm run dev`.

**Cash on Delivery (no keys needed).** Add a candle, check out, choose Cash on delivery, Place
order. Sign in as the owner, Handle orders, open it: Mark shipped is refused; Confirm COD;
Mark shipped; Mark delivered; Mark cash collected. The worker terminal prints each email.

**Razorpay test mode.**

1. Razorpay dashboard, Test Mode, Account & Settings, API Keys, Generate Key. Put the key id and secret in `backend/.env` as `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`. Restart the server.
2. Razorpay needs a public HTTPS address for the webhook. Its documentation says `localhost` cannot be used, that `ngrok.io` and several other tunnel domains are blocked, and suggests **zrok**. Install zrok, enable it once with your zrok account token, then run: `zrok share public http://127.0.0.1:8000`. Copy the https address it prints.
3. Add that host to `DJANGO_ALLOWED_HOSTS` in `backend/.env` and restart the server.
4. Razorpay dashboard, Test Mode, Account & Settings, Webhooks, Add New Webhook. URL: `https://<your zrok host>/api/v1/payments/razorpay/webhook/`. Secret: a long random string, also put in `backend/.env` as `RAZORPAY_WEBHOOK_SECRET`. Event: `payment.captured`. In test mode the dashboard asks for the OTP `754081`.
5. Check out with "UPI / Card / Netbanking". In the Razorpay window use UPI id `success@razorpay`, or card `4100 2800 0000 1007` with any future expiry and CVV.
6. The page says "Confirming your payment", then "Payment received". The order is paid in Handle orders.
7. Missed-webhook check: stop zrok, pay again, wait three minutes with the worker running. The order still becomes paid.

### 8. ASSUMPTIONS MADE

1. Decisions F1 to F11 and F15.
2. A Razorpay order is created per stored total; if the total changes (coupon) a new one is created and the old one is abandoned. Retries after a failed attempt reuse the same Razorpay order, as the documentation advises.
3. The Razorpay `receipt` is the order's `oid`; `notes.order_oid` carries it too.
4. Reconcile treats a fetched order as paid only when `status` is `paid` and `amount_paid` equals the stored total in INR.
5. Checkout options sent to the browser are limited to documented ones: `key`, `amount`, `currency`, `name`, `description`, `order_id`, `prefill`, `notes`, plus the `handler`.
6. COD moves the order to payment status `pending`; delivery does not mark it paid, the owner does.
7. Shipping actions apply to every line of the order at once.
8. "Order placed" for an online payment is emailed when the customer returns from Razorpay, not when the window opens.
9. Refunds are issued in the Razorpay dashboard and recorded here by the owner; no refund API is called.
10. The account link is a signed token valid 48 hours; nothing is stored for it.
11. Nothing sensitive is logged: no signatures, secrets, webhook bodies, emails or phone numbers.

### 9. KNOWN GAPS

- **Not tested against real Razorpay.** The build container cannot reach Razorpay and has no keys. Everything is tested against the documented shapes; the owner's first test-mode payment (section 7) is the real proof. If Razorpay's webhook lacks `currency` on the payment entity, webhooks will be refused and the reconcile job will confirm payments about three minutes late: tell me and it is a one-line change.
- **PostgreSQL concurrency tests still not run** (see G1).
- **The worker must be running** for emails, the reconcile job and draft expiry.
- UPI is not forced to appear first in the Razorpay window (F6).
- No refund API, no partial refunds, no returns flow.
- The legacy "Orders" and "Order detail" dashboard screens are unchanged and show paid orders only.
- Order status can still be edited directly in Django admin, bypassing the state machine.
- `CLAUDE.md` is still the owner's unchanged copy and now lags behind G1 to G4.

### 10. NOT DONE AND WHY

- **G4.5 branding**: on hold by the owner's instruction; needs the design decision first.
- **G5 launch readiness**: needs a domain, a server and live Razorpay keys.
- **Removing Stripe/PayPal**: rule 4; switched off, not removed.

---

## PHASE G2 — Storefront basics (COMPLETED)

### 1. PHASE COMPLETED

**G2 — Storefront basics**, built on top of G1 in the same session. Branch name used
locally: `phase/G2-storefront`.

What a shopper and the owner get:

- **Size picker.** The product page shows one row of buttons per option (today: Size). Picking
  200 g shows the 200 g price, MRP, stock and SKU, and adds the 200 g candle to the cart. It
  is built from `ProductVariant.options`, so a second option such as Colour needs data only.
- **Honest price.** A struck-through MRP and "N% off" appear only when MRP is really above
  the price; the percentage is rounded down. A settings flag can later require proof from the
  recorded price history instead.
- **Price history.** Every price or MRP change, from the dashboard, Django admin or the
  shell, writes one permanent row with who did it. Rows cannot be edited or deleted.
- **Honest stock.** "In stock", "Only N left" (only when N is real and 5 or fewer) or "Sold
  out" with add-to-cart disabled. A sold-out size does not block the other sizes.
- **Shipping line** on the product page and in the cart, including "Add Rs X more for free
  shipping", computed by the pricing function.
- **Policy pages**: Shipping, Returns and Refunds, Privacy, Terms, and Contact, linked from
  the footer and from checkout. The copy is clearly-marked placeholder text.
- **Stock can no longer be typed into drift.** `Product.stock_qty` is read-only in Django
  admin and in the dashboard edit screen; both show ledger availability instead. Adding a
  Batch in admin now receives its stock.
- **`python manage.py seed_noore`**: three placeholder scents in three sizes with stock.

### 2. FILES CREATED

- `backend/catalog/display.py` — `strikethrough_for`, `lowest_prior_price`, `stock_status`
- `backend/catalog/management/__init__.py`, `backend/catalog/management/commands/__init__.py`
- `backend/catalog/management/commands/seed_noore.py`
- `backend/catalog/migrations/0003_productvariant_options.py`
- `backend/catalog/migrations/0004_backfill_variant_options.py`
- `backend/catalog/migrations/0005_pricehistory.py`
- `backend/catalog/migrations/0006_opening_price_history.py`
- `backend/catalog/tests/test_storefront.py`
- `frontend/src/views/policy/policies.js` — the placeholder copy, one place to replace it
- `frontend/src/views/policy/PolicyPage.jsx`, `frontend/src/views/policy/Contact.jsx`
- `frontend/playwright.config.js`, `frontend/e2e/storefront.spec.js`
- `docs/ROADMAP.md`, `CLAUDE.md` — the owner's uploaded copies, added to the repo unchanged

### 3. FILES MODIFIED

- `backend/catalog/models.py` — `ProductVariant.options`; new `PriceHistory`
- `backend/catalog/signals.py` — price-history signal
- `backend/catalog/admin.py` — options and MRP columns; read-only `PriceHistory` admin
- `backend/inventory/admin.py` — adding a Batch books its stock; variant and quantity read-only afterwards
- `backend/store/admin.py` — `stock_qty` read-only, ledger availability column, variants inline on the product
- `backend/store/serializers.py` — variant `options`, `stock`, `strikethrough`, `weight_grams`; product `variants` (active only), `available_qty`, `price_from_paise`; `stock_qty` ignored on update
- `backend/store/views.py` — cart line's size/colour text taken from the variant's options
- `backend/backend/settings.py`, `backend/.env.example` — three storefront settings
- `backend/pytest.ini` — `catalog/tests` added to `testpaths`
- `backend/conftest.py` — every test gets a throwaway `MEDIA_ROOT`
- `backend/.gitignore`, `frontend/.gitignore` — smoke-suite database and Playwright output
- `frontend/package.json`, `frontend/package-lock.json` — `@playwright/test` 1.56.0 (dev), `test:e2e` script
- `frontend/src/App.jsx` — `/policy/:slug`, `/contact`
- `frontend/src/utils/constants.js`, `frontend/.env.example` — support email, WhatsApp number, store name
- `frontend/src/views/shop/ProductDetail.jsx` — rewritten: picker, price, stock, shipping line; legacy Size/Color rows no longer rendered; the swapped size/colour arguments are gone
- `frontend/src/views/shop/Checkout.jsx` — policy links
- `frontend/src/views/shop/Products.jsx`, `Search.jsx` — "From Rs X", "Sold out" badge, null-safe vendor/brand
- `frontend/src/views/customer/Wishlist.jsx`, `frontend/src/views/vendor/Shop.jsx` — null-safe brand
- `frontend/src/views/base/StoreFooter.jsx` — policy links, support email, wa.me link
- `frontend/src/views/vendor/Products.jsx`, `UpdateProduct.jsx`, `AddProduct.jsx` — ledger availability; stock field read-only on edit (E10)

### 4. MIGRATIONS ADDED

| Migration | What | Reverse |
|---|---|---|
| `catalog.0003_productvariant_options` | adds `options` JSON column | drops it |
| `catalog.0004_backfill_variant_options` | fills `options` from `size` / `color` where set | empties only values it could have written |
| `catalog.0005_pricehistory` | creates `PriceHistory` | drops the table |
| `catalog.0006_opening_price_history` | one opening row per existing variant | deletes only rows labelled `system:migration` |

Apply (from `backend\`, after the backup in section 7):

    python manage.py migrate

Roll back G2 only:

    python manage.py migrate catalog 0002

Verified on a copy of the supplied database: apply, roll back, re-apply all clean; 4 opening
rows written; rollback removed the table and the column and left the 4 variants in place.

### 5. ENV VARS ADDED

Backend (`backend/.env.example`), all optional:

- `STRIKETHROUGH_REQUIRES_PRICE_HISTORY` (default `False`)
- `PRICE_HISTORY_WINDOW_DAYS` (default `30`)
- `LOW_STOCK_THRESHOLD` (default `5`)

Frontend (`frontend/.env.example`):

- `VITE_SUPPORT_EMAIL` — **needs the owner's value**; default is the placeholder `support@example.com`
- `VITE_WHATSAPP_NUMBER` — **needs the owner's value**; digits only with country code; default placeholder `910000000000`
- `VITE_STORE_NAME` (default `Noore Candles`)

Smoke suite only: `E2E_PYTHON`, `E2E_API_PORT` (8011), `E2E_WEB_PORT` (5183).

### 6. TESTS ADDED

`backend/catalog/tests/test_storefront.py`, 16 tests:

    python -m pytest catalog/tests -q        ->  16 passed
    python -m pytest -q                      ->  136 passed, 2 skipped (138 collected)

The 2 skips are the PostgreSQL-only concurrency tests (see Known gaps).

Shown failing first: the file was run against the G1 commit, where it fails at import
(`ModuleNotFoundError: No module named 'catalog.display'`), and before this phase
`catalog/tests` was not in `testpaths` at all (122 collected then, 138 now).

Covers: an opening history row per variant; exactly one row per price change with the actor
from the dashboard, from a user context and from the shell; no row for unrelated saves; rows
cannot be updated or deleted; flag off and flag on (including a short price spike that must
not manufacture a discount, and an MRP-only edit); percent rounded down; stock indicator at,
below and above the threshold and sold out; the product API per variant; 200 g adds the 200 g
variant; a sold-out variant refused while siblings are accepted; `stock_qty` not editable
from the dashboard or admin; a Batch added in admin receives stock once; `seed_noore`
refuses outside DEBUG and is idempotent.

Playwright (`frontend/e2e/storefront.spec.js`), 4 tests, **run in a real Chromium in this
session: 4 passed**:

    npx playwright test

Pick a size and add it to the cart; add to cart, apply a coupon and check INR totals in the
cart and at checkout (no "$", "USD", PayPal, tax or service-fee row); Rs 999+ ships free;
all four policy pages and the contact page open from the footer.

### 7. MANUAL VERIFICATION STEPS

Windows PowerShell, from the repo root.

    New-Item -ItemType Directory -Force -Path backups | Out-Null
    Copy-Item backend\db.sqlite3 "backups\db-$(Get-Date -Format 'yyyyMMdd-HHmmss').sqlite3"
    cd backend
    .\venv\Scripts\Activate.ps1
    pip install -r requirements-dev.txt
    python manage.py migrate
    python manage.py seed_noore
    python -m pytest -q
    python manage.py runserver

Second terminal:

    cd frontend
    npm install
    npm run build
    npm run dev

Then at http://localhost:5173 :

1. Open a seeded candle. Click 200 g: price Rs 799, struck Rs 949, "15% off", "In stock".
2. Add it to the cart. The cart line says "200 g" and Rs 799; the summary says shipping Rs 79
   and "Add Rs 200 more for free shipping".
3. Footer: open each of the four policies and Contact. Each policy shows the placeholder notice.
4. Django admin, Catalog, Product variants: change a price. Catalog, Price history shows one
   new row with your user. Try to edit that row: you cannot.
5. Django admin, Inventory, Batches: add a batch of 5 for a variant. Its availability rises by 5.
6. Django admin, Products: `stock_qty` is greyed out.

Smoke suite (venv activated, from `frontend\`, first time only `npx playwright install chromium`):

    npx playwright test

### 8. ASSUMPTIONS MADE

1. Option names are free text; the picker shows them as stored ("Size"). The cart line's
   legacy `size` text is taken from the option named exactly `Size`, colour from `Colour` or `Color`.
2. Option values of one product form a consistent set (every variant has the same option
   names). If a combination does not exist, the picker jumps to a variant that has the chosen value.
3. A sold-out size stays selectable (so its price can be seen) but cannot be added.
4. "Only N left" counts what other shoppers can still buy, so it already excludes units held
   in carts, including the viewer's own.
5. The exact available quantity is still present in the public API (`available_qty`, as it
   was since F-B); only the page chooses not to display it above the threshold.
6. Flag on: the "current price period" starts at the first history row with the current
   selling price (an MRP-only edit does not restart it). The reference is the lowest price in
   force during the window before that moment, including a price already in force when the
   window opened. With no earlier price on record nothing is struck.
7. Opening history rows are dated at migration time, because that is when recording began.
8. `queryset.update()` and raw SQL bypass signals and are not recorded in the price history.
   Nothing in this codebase changes a variant price that way.
9. Listing pages show "From Rs X" (lowest active variant) and add the default variant from
   the card; choosing a size happens on the product page.
10. Policy pages read the shipping charge and threshold live from the server settings, so
    those two numbers are real even though the surrounding copy is placeholder.
11. `seed_noore` attaches products to the first shop (`Vendor`) if one exists, so they show
    in the owner dashboard; it creates no shop. Seed products have no image file.
12. The smoke suite uses its own database (`backend/e2e.sqlite3`) and ports, and needs
    `python` on PATH to be the project's interpreter.

### 9. KNOWN GAPS

- **Policy copy is placeholder** and says so on every page. `PLACEHOLDER_COPY` in
  `frontend/src/views/policy/policies.js` must be set to `false` when the real text goes in.
- **Support email and WhatsApp number are placeholders** until the two `VITE_` variables are set.
- Footer "About us" lorem ipsum, the MDBootstrap copyright line, the header and the
  "Vendor" tab/links are untouched: that is G4.5.
- No dashboard screen for managing sizes or receiving stock; both are done in Django admin.
- The product description is shown as plain text, as before; HTML typed in the dashboard
  editor would show its tags.
- `CLAUDE.md` section 3 still describes G1 as future work ("STILL LEGACY Decimal rupees
  until phase G1") and its trap list mentions the two things fixed here. It was added to the
  repo unchanged; the owner should approve an update.

### 10. NOT DONE AND WHY

- **G4.5 branding and vendor-reference removal**: explicitly excluded by the owner.
- **Razorpay, COD selector, reviews moderation, reorder**: G3 and G4.
- **Real policy text**: the owner supplies it.
- **PostgreSQL concurrency run**: PostgreSQL could not be installed in the build container
  (package download returned 404). The tests exist and skip on SQLite by design.

---

## PHASE G1 — Pricing (COMPLETED)

### 1. PHASE COMPLETED

**G1 — Pricing**: one server-side function decides what a customer pays, in INR, in integer
paise. Branch name used locally: `phase/G1-pricing`.

- **Rupees everywhere.** No "$" or "USD" in the storefront, the order emails or the
  dashboard. `ConfigSettings.currency_sign` is the rupee sign.
- **One pricing function**, `store/pricing.py` `quote()`, used by the cart, order creation
  and the coupon endpoint. Totals sent by the browser are ignored.
- **Shipping**: flat Rs 79 per order, free when the subtotal after discount is Rs 999 or more.
- **Coupons**: percentage or flat rupees; minimum order; start and expiry date; total cap;
  per-customer cap (by account, or by email / phone for guests). The discount is spread over
  every line. Each refusal has its own message. Uses are recorded in `CouponRedemption`.
- **No service fee, no added tax.** Prices are tax-inclusive; the checkout says "Inclusive
  of all taxes". A carve-out formula is in place for when a tax rate is set.
- **Paise columns** beside every Decimal money column on Cart, CartOrder and CartOrderItem,
  backfilled, with the Decimal columns kept in step as a mirror.
- **Payments**: Stripe charges in `inr` from the stored paise total. PayPal is hidden.
- Also (G0 items this phase needed, see E1): the `AddToCart` import casing (the frontend did
  not build on Linux before), a default variant and opening stock for every new product,
  paid orders keep their stock after the checkout hold lapses, a PIN code field in the cart.

Step 0 result: see decision E2.

### 2. FILES CREATED

- `backend/store/pricing.py` — `quote()`, coupon checks, `apply_quote_to_order`, `record_redemption`
- `backend/store/money_mirror.py` — `MoneyMirrorMixin`, `set_money`, `assert_mirrors`, `mirror_mismatches`
- `backend/store/jobs.py` — `store.expire_stale_order_drafts` (hourly)
- `backend/catalog/signals.py` — Product and default variant kept in step
- `backend/store/migrations/0029` to `0034`, `backend/addon/migrations/0003` to `0005` (section 4)
- `backend/tests/test_pricing.py`
- `frontend/src/utils/money.js` — `formatINR(paise)`, `formatRupees`, `rupeesToPaise`, `percentOff`

### 3. FILES MODIFIED

- `backend/store/models.py` — paise columns, `CartOrder.coupon_code`, coupon rule fields, `CouponRedemption`
- `backend/addon/models.py` — `shipping_flat_paise`, `free_shipping_threshold_paise`, `tax_rate_bps`; currency defaults
- `backend/store/views.py` — cart, cart totals, order creation, coupon endpoint and Stripe all go through `quote()`; every read of `service_fee_*` and `Tax.rate` removed; the `qty x rate` tax path deleted
- `backend/store/order_state.py` — a paid order's stock is secured (`hold_for_order`)
- `backend/inventory/services.py` — new `hold_for_order`
- `backend/core/signals.py` — `total_paise` tracked on `CartOrder`
- `backend/store/apps.py`, `backend/catalog/apps.py` — register the job and the signals
- `backend/store/admin.py` — coupon rule columns; read-only redemption admin
- `backend/backend/settings.py`, `backend/.env.example` — `ORDER_DRAFT_TTL_HOURS`
- `backend/templates/email/customer_order_confirmation.html`, `vendor_order_sale.html` — "$" to the rupee sign
- `backend/conftest.py` — `product` fixture uses the automatic default variant; suite-wide mirror check
- `backend/inventory/tests/test_inventory.py` — the PostgreSQL race test uses the automatic default variant
- `backend/tests/test_security.py`, `backend/core/tests/test_core.py` — **two expectations changed on purpose**: per-line shipping of Rs 6 is now Rs 0 with Rs 79 on the order; the audited total after a 10% coupon on Rs 100 is Rs 169 (100 - 10 + 79), and `total_paise` appears in the audit row
- `frontend/src/views/plugin/addToCart.jsx` — optional variant id; no price sent
- `frontend/src/views/shop/Cart.jsx`, `Checkout.jsx` — rewritten: server totals, discount row, shipping or "Free", coupon apply/remove, PIN code, no tax or service-fee row, PayPal removed from the page
- `frontend/src/views/shop/ProductDetail.jsx`, `Products.jsx`, `Search.jsx`, `Invoice.jsx`, `PaymentSuccess.jsx`
- `frontend/src/views/customer/Orders.jsx`, `OrderDetail.jsx`, `Notifications.jsx`
- `frontend/src/views/vendor/Dashboard.jsx`, `Earning.jsx`, `OrderDetail.jsx`, `Products.jsx`, `Shop.jsx`, `AddProduct.jsx`, `UpdateProduct.jsx` — currency display only (E10)

### 4. MIGRATIONS ADDED

| Migration | What | Reverse |
|---|---|---|
| `store.0029_cart_paise_columns` | 6 paise columns on Cart | drops them |
| `store.0030_cartorder_paise_columns` | 7 paise columns and `coupon_code` on CartOrder | drops them |
| `store.0031_cartorderitem_paise_columns` | 8 paise columns on CartOrderItem | drops them |
| `store.0032_backfill_paise_columns` | fills paise from each Decimal twin (exact, half-up) | no-op: Decimal columns were never changed |
| `store.0033_coupon_rules` | `kind`, `flat_off_paise`, `min_order_paise`, `max_total_uses`, `max_uses_per_customer`, `valid_from`, `valid_until` | drops them |
| `store.0034_couponredemption` | `CouponRedemption`, unique on (coupon, order) | drops the table |
| `addon.0003_configsettings_pricing_fields` | shipping and tax settings | drops them |
| `addon.0004_currency_inr` | existing rows to the rupee sign / INR | restores "$" / USD |
| `addon.0005_currency_defaults_inr` | model defaults to the rupee sign / INR | restores the old defaults |

Apply:

    python manage.py migrate

Roll back G1 only (roll G2 back first, see its section):

    python manage.py migrate store 0028
    python manage.py migrate addon 0002

Verified on a copy of the supplied database: apply, roll back, re-apply all clean. After
apply: 2 carts, 1 order, 2 order lines, 0 mirror mismatches; config is rupee / INR / 7900 /
99900 / 0. After rollback: no paise columns, "$" / USD restored, order totals untouched.

### 5. ENV VARS ADDED

- `ORDER_DRAFT_TTL_HOURS` (optional, default `48`, keep above 26)

### 6. TESTS ADDED

`backend/tests/test_pricing.py`, 41 tests (40 run, 1 PostgreSQL-only):

    python -m pytest tests/test_pricing.py -q   ->  40 passed, 1 skipped
    python -m pytest -q                         ->  120 passed, 2 skipped at the end of G1

Shown failing first: run against the pre-G1 code the file fails at import
(`ModuleNotFoundError: No module named 'store.jobs'`); none of `store.pricing`,
`store.money_mirror` or the paise columns existed.

Covers every G1 acceptance line: Rs 920 pays Rs 79, Rs 999 ships free, Rs 1,100 with 10% off
pays Rs 79; a tampered client total is ignored and the stored order equals `quote()`; a
percentage coupon discounts every line and the lines sum to the paisa; a flat coupon larger
than the subtotal stops at 0; refusal when unknown, inactive, not started, expired, under
minimum, over the total cap and over the per-customer cap (signed-in and guest by email or
phone), each with its own message; cancelling frees the redemption, as does removing or
replacing the coupon; no service fee even with a 5% fee and an 18% Tax row configured; tax
at 1800 bps is carved out and the total is unchanged; a later price change never alters an
order; Stripe is called with `inr` and the stored paise.

**Mirror check (owner amendment).** `conftest.py` connects a check to every save of Cart,
CartOrder and CartOrderItem for the whole suite: it walks every money pair and fails the
test if `to_paise(decimal) != paise`. A named test walks create, quantity change, coupon,
payment and cancel. A dedicated test writes a paise value without its mirror
(`queryset.update`) and shows the assertion fail.

Playwright: the G1 scenario is in `frontend/e2e/storefront.spec.js` (see G2, section 6).

### 7. MANUAL VERIFICATION STEPS

Same commands as G2 section 7. Then:

1. Cart with one 200 g candle: Subtotal Rs 799, Shipping Rs 79, Total Rs 878.
2. Coupon `WELCOME10`: Discount -Rs 79.90, Total Rs 798.10. Coupon `NOPE`: "This coupon code is not valid."
3. Add a 300 g candle: Shipping becomes "Free".
4. Fill the address and go to checkout: same figures, "Inclusive of all taxes", no tax or
   service-fee row, no PayPal button, card button reads "Pay Rs ... by card".
5. Django admin, Coupons: set "Max total uses" to 1 on a coupon, use it on one order, try it
   from another browser with another email: "This coupon has been fully redeemed."
6. Dashboard, edit a product's price: Django admin, Catalog, Product variants shows the new price.
7. Worker: `python manage.py run_worker --once` runs the draft-expiry job among the others.

### 8. ASSUMPTIONS MADE

1. Decisions E3 to E16 above.
2. Order column meanings from G1 on: `sub_total` item subtotal before discount; `saved` the
   discount; `shipping_amount` the order's shipping; `tax_fee` tax carved out (0 today);
   `service_fee` 0; `initial_total` subtotal plus shipping; `total` what the customer pays.
   On a line: `price` unit price; `sub_total` price x qty; `saved` its share of the discount;
   `total` sub_total minus saved; `shipping_amount` and `service_fee` 0.
3. Rows written before G1 keep their old meaning and old numbers.
4. PERCENT rounds down to a whole paisa; the split across lines is largest-remainder, ties
   to the earlier line.
5. A coupon is looked up by code, case-insensitively, among active coupons; the legacy
   per-vendor match is gone. If two active coupons share a code the newest wins.
6. A redemption counts unless its order is Cancelled, or its payment is cancelled or
   expired, or the order no longer carries that coupon. A failed or refunded payment still counts.
7. Signed-in customers are matched by account only; guests by lower-cased email or E.164 phone.
8. A guest's per-customer cap can only be checked once they give contact details, so the
   cart preview may accept a code that order creation then refuses; the customer is told
   before the checkout page opens and the order is created without the discount.
9. Re-posting a cart updates its unpaid draft from the cart as it is now. If the request
   has no `coupon_code` key the draft keeps its coupon; a blank value removes it.
10. Applying a coupon on the checkout page re-prices from the unit prices stored on the order.
11. `redemption.discount_paise` is the discount at the moment of first use; the order's
    `saved_paise` is the current figure.
12. The cart-totals response no longer has the float keys `shipping`, `tax`, `service_fee`,
    `sub_total`, `total`; it has integer `*_paise` keys. No endpoint, model or field was
    removed or renamed.
13. `ConfigSettings` defaults apply when no settings row exists.
14. Paying when the hold has lapsed re-reserves if stock is there; if not, the order is
    still marked paid and an `order.stock_shortfall` audit row is written for the owner.
15. Stripe's `currency` value `inr` and an integer `unit_amount` in the smallest unit are
    the only provider details changed; no payload was invented.
16. Built and tested on Python 3.12 and Node 22 (the container's); the project targets 3.11 and 20.

### 9. KNOWN GAPS

- **Guest coupon evasion (accepted by the owner).** A guest can get round the per-customer
  cap by checking out with a different email **and** a different phone number. The cap is
  reliable only for signed-in customers. `max_total_uses` still bounds the total cost of a
  coupon, so **set it on every coupon that matters**.
- **PostgreSQL concurrency tests not run.** `ConcurrentCouponTest` (new) and the F-B
  stock race test skip on SQLite. PostgreSQL could not be installed in the build container.
  Run them once locally with the commands in `CLAUDE.md` section 2 (`-k concurrent`, and
  `python -m pytest tests/test_pricing.py -k capped -q`).
- **Draft expiry needs the worker.** Without `run_worker`, an abandoned checkout keeps its
  coupon use until the job runs.
- **A total of Rs 0 cannot be paid by card** (the endpoint says so). Only reachable if
  shipping is set to 0 and a flat coupon covers the subtotal.
- **Tax base needs a CA** before `tax_rate_bps` is ever set above 0 (E12). This is a
  compliance interpretation; nothing is charged differently today.
- **Order emails** now show rupees but still list "Tax" and "Service fee" rows (both 0.00)
  and no discount row.
- **Django admin can still edit order statuses directly** (`list_editable`), bypassing the
  state machine. Pre-existing; not changed here.
- **Nothing in the dashboard moves an order's delivery status**, so stock does not leave
  the ledger on dispatch yet (a G0 item not rebuilt here).
- **PayPal backend path** still exists and still compares in USD; it is unreachable from
  the storefront and returns 503 without credentials.
- Legacy `CouponUsers`, `Coupon.used_by`, `CartOrder.coupons` and `CartOrderItem.coupon`
  are no longer written; `CouponRedemption` and `coupon_code` replace them.
- Dashboard revenue excludes shipping (E11).

### 10. NOT DONE AND WHY

- **Razorpay, COD selector**: G3.
- **Variant picker, price history**: G2 (done above).
- **Removing** `service_fee_*`, `Tax`, the Decimal columns, Stripe or PayPal: rule 4;
  they stay as removal proposals.
- **Resolving a real price mismatch**: none found in the supplied database (E2, E3).

---

## PHASE F-A.1 — Owner dashboard access (COMPLETED)

Follow-up to F-A after the owner reported that a newly created superuser could only see the
customer account pages.

**Cause.** The storefront's owner dashboard is driven by the `vendor_id` claim inside the login
token. A freshly created superuser owns no `Vendor` row, so the claim is `0` and
`Dashboard.jsx` redirects to `/vendor/register/`. Separately, the seeded shop (id 10) — which
owns all four demo products — was still attached to the seed account `desphixs@gmail.com`, so
even registering a new shop would have produced an empty dashboard. This is seed-data
ownership, not a defect introduced by F-A.

**FILES CREATED**

| Path | Purpose |
|---|---|
| `backend/core/management/commands/claim_shop.py` | `python manage.py claim_shop` — lists shops and attaches the brand's shop (with its products, orders, coupons and reviews) to a staff account. Refuses non-staff accounts, refuses to run before `migrate`, releases any shop the user already held, runs in one transaction, and writes a `shop.claimed` audit row |

**FILES MODIFIED** — none.

**MIGRATIONS ADDED** — none.

**ENV VARS ADDED** — none.

**TESTS** — no new automated test; verified manually end to end (see below). `python -m pytest -q` still reports 39 passed.

**MANUAL VERIFICATION PERFORMED**

On a copy of the seeded database: created a fresh `admin@gmail.com` superuser, confirmed its
token carried `vendor_id: 0`, ran `claim_shop --list` (six shops, only id 10 holding products),
ran `claim_shop --email admin@gmail.com`, confirmed the token then carried `vendor_id: 10`, and
called all nine owner dashboard endpoints with that account's JWT — every one returned HTTP 200
with real data (4 products, 1 order, revenue 1329.00) and no credential fields. Also confirmed
the command aborts with a readable message when run before `migrate`, and that the failure
rolls back cleanly, leaving ownership unchanged.

**ASSUMPTIONS MADE**

1. The brand's shop is the one holding the most products when `--shop-id` is not given.
2. Claiming a shop does not move products from other shops unless `--move-products` is passed.
3. The five empty seed shops are left in place (rule 4); they are covered by removal proposal R1.
4. The `vendor_id` token claim remains the mechanism for showing the dashboard, so a fresh login is required after claiming.

**KNOWN GAPS**

- The dashboard is still reached through the nav item labelled "Vendor", and `/vendor/register/` is still linked. Both are renamed or removed when the multi-vendor residue goes.
- `Dashboard.jsx` redirects to `/vendor/register/` whenever `vendor_id` is 0, including for ordinary customers, who then hit a 403 on that page. Cosmetic; folded into the residue removal.

---

## PHASE F-A — Platform & security baseline (COMPLETED)

### 1. PHASE COMPLETED

Foundation work only; no customer-facing feature from the 12. Acceptance criteria met:

- Every credential leak found in Phase 0 is closed and covered by a regression test.
- Default-deny API: every view explicitly opts into public access.
- Every customer-data endpoint enforces ownership; every owner endpoint enforces staff.
- Prices, shipping and cart ownership are decided by the server.
- Payment confirmations cannot be replayed across orders.
- Secrets moved out of code; `.env.example` documents every variable.
- Append-only audit log for price, stock, order and delivery state changes (rule 9).
- Idempotency store for webhooks/external confirmations (rule 8).
- Job outbox + worker (prerequisite for Features 1, 4, 5, 8, 10, 11).
- Money (paise) and Asia/Kolkata time helpers (rules 6, 7).
- PII-masking logging (security section).
- Test harness with 39 passing tests; 19 security tests proven to fail on the baseline.

**Critical findings discovered and fixed during this phase (all LIVE-VERIFIED before fixing):**

| Severity | Finding |
|---|---|
| CRITICAL | `GET /api/v1/products/` (public) returned the superuser's **password hash, OTP and password-reset token** via `product.vendor.user` (DRF `depth=3` auto-expanded the User model with all fields) |
| CRITICAL | `GET /api/v1/user/profile/<id>/` (anonymous) returned any user's password hash, OTP and reset token |
| CRITICAL | `POST /api/v1/user/password-change/` accepted only `user id + OTP`; combined with the leaks above this was **anonymous takeover of any account including the admin** |
| HIGH | `GET /api/v1/checkout/<oid>/` returned the buyer's password hash |
| HIGH | Public review lists exposed every reviewer's email and phone |
| HIGH | Anonymous read of any customer's orders, wishlist, notifications; anonymous edit of any profile |
| HIGH | Anonymous product create/update/delete, coupon CRUD, shop edit, order tracking edit |
| HIGH | Cart price and shipping taken from the request body |
| HIGH | Reviews could be posted as any user |
| HIGH | PayPal: amount/currency never verified, PayPal order id reusable across orders; Stripe: any paid session id could mark any order paid |
| MEDIUM | PayPal OAuth access token printed to stdout; password, OTP and reset token printed by the password-change view and logged to the browser console |
| MEDIUM | Password-reset OTP generated with `random` (not cryptographic); reset link host hardcoded to localhost |
| LOW | Guest cart id generated with `Math.random`; first call returned `null` |

### 2. FILES CREATED

| Path | Purpose |
|---|---|
| `backend/core/__init__.py` | Package marker |
| `backend/core/apps.py` | App config; registers audit signals and built-in jobs on startup |
| `backend/core/models.py` | `AuditLog` (append-only), `ProcessedEvent` (idempotency, append-only), `Job` (outbox); `AppendOnlyModel` base that blocks save/update/delete of existing rows |
| `backend/core/audit.py` | Current-actor context (`set_actor`, `acting_as`) and `record()` helper |
| `backend/core/signals.py` | Writes one audit row per tracked-field change on `Product`, `CartOrder`, `CartOrderItem` (covers API, admin, shell) |
| `backend/core/authentication.py` | `AuditingJWTAuthentication`: JWT auth that sets the audit actor |
| `backend/core/middleware.py` | `RequestActorMiddleware`: resets actor per request; attributes admin (session) changes |
| `backend/core/permissions.py` | `IsStaffOwner`, `PublicReadStaffWrite`, `ensure_self_or_staff()`, `ensure_order_access()` |
| `backend/core/serializers.py` | `SafeDepthModelSerializer` (depth-expanded Users become `PublicUserSerializer`), `PublicUserSerializer` |
| `backend/core/idempotency.py` | `claim_event(provider, event_id)` exactly-once claim |
| `backend/core/jobs.py` | `@job`, `@periodic`, `enqueue()` with dedupe key, atomic claim, retry with backoff, DEAD after max attempts, stale-job reaper |
| `backend/core/builtin_jobs.py` | Periodic `core.reap_stale_jobs` (every 5 min) |
| `backend/core/management/commands/run_worker.py` | `python manage.py run_worker [--once]` |
| `backend/core/money.py` | `to_paise`, `from_paise`, `format_inr`; rejects float |
| `backend/core/timeutils.py` | Asia/Kolkata helpers; rejects naive datetimes |
| `backend/core/logmask.py` | `PIIMaskingFilter` masking emails, phones, JWT/Bearer tokens |
| `backend/core/admin.py` | Read-only admin for audit log, processed events and jobs |
| `backend/core/migrations/0001_audit_idempotency_jobs.py` | Creates the three core tables |
| `backend/core/tests/test_core.py` | 18 platform tests |
| `backend/tests/test_security.py` | 21 security regression tests |
| `backend/conftest.py` | pytest fixtures (users, JWT clients, product, orders) |
| `backend/pytest.ini` | pytest configuration |
| `backend/requirements-dev.txt` | Test dependencies |
| `backend/.env.example` | Every backend variable, documented |
| `frontend/.env.example` | Frontend overrides, documented |
| `docs/BUILD_LOG.md` | This file |

(`__init__.py` markers under `core/management`, `core/management/commands`, `core/migrations`, `core/tests`, `tests` also created.)

### 3. FILES MODIFIED

| Path | What changed and why |
|---|---|
| `backend/backend/settings.py` | `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` (now includes `localhost`), CSRF/CORS origins read from env; `CORS_ALLOW_ALL_ORIGINS` replaced with an allow-list; `core` app + `RequestActorMiddleware` added; DRF default permission is now `IsAuthenticated` with `AuditingJWTAuthentication`; throttling (anon, user, auth, otp, checkout, review, webhook); email backend and sender from env (course author's personal address removed); Stripe/PayPal keys optional; `PAYPAL_API_BASE`, `BUSINESS_TIME_ZONE`, `PASSWORD_RESET_TOKEN_MINUTES`, job settings; `LOGGING` with PII masking; secure cookies when not DEBUG. Jazzmin and SimpleJWT settings unchanged |
| `backend/requirements.txt` | Added `django-tinymce==4.1.0` (required by two existing migrations; missing before), `psycopg2` -> `psycopg2-binary==2.9.9` (installs on Windows), pinned `Pillow==10.4.0` and `django-import-export==4.4.1` (were unpinned), `setuptools<81` (drf-yasg needs `pkg_resources`) |
| `backend/.env` | Now holds local-dev values including a freshly generated `DJANGO_SECRET_KEY`, console email backend, and empty payment keys (the old `<add-your-key>` placeholders would have been treated as real keys) |
| `backend/.gitignore` | `.env` is now ignored |
| `backend/userauths/serializer.py` | `UserSerializer` limited to id, email, username, full_name, phone (was `__all__`: password hash, OTP, reset token, permissions). `ProfileSerializer.user` made read-only (a user could previously re-point a profile to another account). Added `PublicProfileSerializer` |
| `backend/userauths/views.py` | Profile: owner or staff only. Password-reset request: identical response for known/unknown emails, returns no account data, OTP from `secrets`, reset token is a signed 30-minute JWT with `purpose=password_reset`, link uses `SITE_URL`, email failure no longer 500s. Password change: requires user id + OTP + the matching unexpired single-use reset token, validates password strength, constant-time compares; all debug prints removed. Throttle scopes on login, register, reset |
| `backend/store/serializers.py` | All model serializers now extend `SafeDepthModelSerializer`; `VendorSerializer.user` and `ReviewSerializer.profile` use public serializers |
| `backend/store/views.py` | Every view declares its permission. Cart: price and shipping from DB, quantity validated against stock, owner from JWT, body `user` must match caller. Cart list/detail/delete: `user_id` in URL must be the caller. Create order: owner from JWT, required-field validation, empty cart rejected. Checkout/coupon/payment-success: a registered buyer's order is only accessible to that buyer or staff. PayPal: amount and currency must equal the order total, PayPal order id claimed once via `ProcessedEvent`, row-locked status transition, 15 s timeouts, token no longer printed. Stripe: session id must equal the one created for the order, claimed once, 503 when keys absent. Reviews: login required, written as caller, rating 1-5 validated. Cart totals summed as Decimal. Missing products return 404 instead of 500. Existing behaviours intentionally preserved and flagged: tax formula, first-item-only coupon, vendor emails |
| `backend/customer/views.py` | Orders, order detail, wishlist, notifications, settings: login required and `user_id` must be the caller (or staff). Settings now updates the caller's own profile (it previously looked up `Profile` by the user id as a profile primary key, i.e. edited the wrong profile) |
| `backend/vendor/views.py` | All owner-dashboard endpoints require staff (`IsStaffOwner`), including the three function-based chart views and five views that had no permission at all. Public shop page: read by anyone, write by staff only. Shop product listing stays public. Vendor register attaches the shop to the signed-in staff user (ignores `user_id` in the body). Owner profile settings look up the profile by user. All debug prints removed. No logic otherwise changed |
| `frontend/src/utils/axios.js` | Request interceptor attaches the JWT to every API call and refreshes it when expired, with a single in-flight refresh shared by concurrent requests. This is why 38 components did not need editing |
| `frontend/src/utils/useAxios.js` | Now returns the shared instance (the old version read `response.data.access` from an object that had no `data`, so every refreshed request sent `Bearer undefined`) |
| `frontend/src/utils/auth.js` | Page-load session restore uses the shared single-flight refresh (avoids two rotations of the same refresh token and a surprise logout); a failed restore continues as guest instead of leaving the app blank; cookies get `SameSite=Lax` |
| `frontend/src/utils/constants.js` | Values overridable via `VITE_API_BASE_URL`, `VITE_SERVER_URL`, `VITE_PAYPAL_CLIENT_ID`; defaults unchanged |
| `frontend/src/views/plugin/cartID.jsx` | Cart id from `crypto.getRandomValues`; returned on first call |
| `frontend/src/views/auth/forgotPassword.jsx` | Shows the server's generic message; handles errors/throttling; no longer logs the response |
| `frontend/src/views/auth/createPassword.jsx` | No longer logs OTP, reset token and new password to the console; shows server validation errors (previous `try/catch` around a promise never caught anything) |
| `frontend/.gitignore` | Ignores `.env` and `.env.local` |

### 4. MIGRATIONS ADDED

| Name | What it does | Apply | Roll back |
|---|---|---|---|
| `core.0001_audit_idempotency_jobs` | Creates `core_auditlog`, `core_processedevent` (unique provider+event_id), `core_job` (unique dedupe_key) with indexes | `python manage.py migrate core` | `python manage.py migrate core zero` |

Rollback and re-apply verified on a copy of the seeded database. No existing table was altered.

### 5. ENV VARS ADDED

All in `backend/.env.example` with comments.

| Name | Purpose | Example | Required |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Django signing key (was hardcoded) | 64 random chars | **Yes** |
| `DJANGO_DEBUG` | Debug mode | `False` | No (default False) |
| `DJANGO_ALLOWED_HOSTS` | Served hostnames | `127.0.0.1,localhost` | No |
| `CSRF_TRUSTED_ORIGINS` | Admin form origins | `http://127.0.0.1:8000` | No |
| `CORS_ALLOWED_ORIGINS` | Browser origins allowed to call the API | `http://localhost:5173` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `BUSINESS_TIME_ZONE` | Timezone for business rules | `Asia/Kolkata` | No |
| `DJANGO_EMAIL_BACKEND` | Email backend | `django.core.mail.backends.console.EmailBackend` | No (default Mailgun) |
| `DEFAULT_FROM_EMAIL` | Sender address | `noreply@yourbrand.in` | No |
| `PAYPAL_API_BASE` | PayPal API host | `https://api-m.sandbox.paypal.com` | No |
| `PASSWORD_RESET_TOKEN_MINUTES` | Reset link lifetime | `30` | No |
| `THROTTLE_ANON`, `THROTTLE_USER`, `THROTTLE_AUTH`, `THROTTLE_OTP`, `THROTTLE_CHECKOUT`, `THROTTLE_REVIEW`, `THROTTLE_WEBHOOK` | Rate limits | `10/min` | No |
| `JOB_MAX_ATTEMPTS` | Retries before DEAD | `5` | No |
| `JOB_WORKER_SLEEP_SECONDS` | Idle poll interval | `5` | No |
| `JOB_STALE_AFTER_SECONDS` | Orphaned-job timeout | `600` | No |
| `VITE_API_BASE_URL`, `VITE_SERVER_URL`, `VITE_PAYPAL_CLIENT_ID` | Frontend overrides | see `frontend/.env.example` | No |

Changed from required to optional: `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY`, `PAYPAL_CLIENT_ID`, `PAYPAL_SECRET_ID` (payment endpoints return 503 when blank). `MAILGUN_API_KEY`, `MAILGUN_SENDER_DOMAIN` now read through `environs` (were `os.environ.get`).

### 6. TESTS ADDED

Run from `backend/` with the venv active:

```
pip install -r requirements-dev.txt
python -m pytest -q
```

Result: **39 passed**.

`tests/test_security.py` (21 tests) was also run against the untouched baseline commit: **19 failed, 2 passed**. The two that pass on the baseline are regression guards, not bug reproductions: a guest order has no buyer to leak, and in a fresh test database profile ids happen to equal user ids.

| Test | Proves |
|---|---|
| `test_public_catalog_endpoints_never_expose_credentials` | No password/OTP/reset token/permission key anywhere in 7 public endpoints |
| `test_reviews_do_not_expose_reviewer_email_or_phone` | Review lists show name and avatar only |
| `test_checkout_of_guest_order_does_not_expose_credentials` | Guard for the checkout serializer |
| `test_profile_endpoint_is_owner_only` | 401 anonymous, 403 other user, 200 self without secrets |
| `test_password_reset_request_returns_no_account_data` | Same body for known and unknown emails; no account data |
| `test_password_change_rejects_otp_without_valid_reset_token` | The takeover path is closed |
| `test_password_reset_full_flow_is_single_use` | Legit flow works once; link cannot be reused |
| `test_customer_orders_are_owner_only` | Order list/detail IDOR closed |
| `test_wishlist_notifications_and_settings_are_owner_only` | IDOR closed on three more endpoints; profile hijack and wishlist-for-victim blocked |
| `test_settings_update_changes_the_callers_own_profile` | Settings edit hits the right profile |
| `test_registered_buyers_order_is_hidden_from_other_users` | A logged-in buyer's order is not readable by others via its oid |
| `test_cart_price_and_shipping_come_from_the_database` | Tampered `price: 1.00` is stored as 56.00 |
| `test_cart_cannot_be_created_for_another_user` | Body `user` must be the caller |
| `test_order_cannot_be_created_on_behalf_of_another_user` | Body `user_id` must be the caller |
| `test_review_requires_login_and_is_written_as_the_caller` | No anonymous or impersonated reviews |
| `test_owner_dashboard_endpoints_are_staff_only` | 401/403/200 matrix on 7 owner endpoints |
| `test_anonymous_users_cannot_create_products_or_coupons` | No anonymous catalog/coupon writes |
| `test_public_shop_page_is_readable_but_not_writable` | Public read, staff-only write |
| `test_stripe_session_from_another_order_cannot_mark_order_paid` | Stripe cross-order replay blocked |
| `test_paypal_order_id_cannot_be_replayed_against_a_second_order` | PayPal replay blocked (409) |
| `test_paypal_payment_for_a_smaller_amount_is_rejected` | Underpayment rejected |
| `core/tests/test_core.py` (18 tests) | Price change writes exactly one audit row with before/after and actor; unchanged save writes none; system changes have null actor; API change attributed to JWT user; audit rows cannot be updated or deleted (instance and queryset); event claimed once; job dedupe; not run early; naive datetime rejected; no double claim; retry with backoff then DEAD with PII-masked error; periodic scheduling idempotent; stale jobs reclaimed; `run_worker --once`; paise conversion exact and float rejected; IST offset; log masking |

### 7. MANUAL VERIFICATION STEPS

Backend terminal (PowerShell, from `backend\`):

1. `.\venv\Scripts\Activate.ps1`
2. `pip install -r requirements-dev.txt`
3. `python manage.py migrate` -> expect `Applying core.0001_audit_idempotency_jobs... OK`
4. `python -m pytest -q` -> expect `39 passed`
5. Make sure your admin account is staff (superusers already are).
6. `python manage.py runserver`
7. Open `http://127.0.0.1:8000/api/v1/products/` and press Ctrl+F for `password` -> no match.
8. Open `http://127.0.0.1:8000/api/v1/user/profile/11/` in a private window -> `401`.
9. `http://localhost:8000/api/v1/products/` now works (was `400`).

Frontend terminal (from `frontend\`): `npm run dev`, then in the browser:

10. Browse the home page and a product page while logged out -> works.
11. Add to cart as a guest -> works; cart shows the database price.
12. Register a new customer -> auto-login works; `Account > Orders`, `Wishlist`, `Notifications`, `Settings` load.
13. Log in as your superuser -> vendor dashboard loads (stats, products, orders, coupons).
14. Log in as the normal customer and open `http://localhost:5173/vendor/dashboard/` -> dashboard data does not load (403 in the Network tab).
15. Forgot password with your email -> the password-reset email (with the link) prints in the **backend terminal** (console email backend). Open the link, set a new password, log in with it. Open the same link again -> error.
16. Third terminal: `python manage.py run_worker` -> prints `worker started`; within 5 minutes `Django admin > Core platform > Jobs` shows a DONE `core.reap_stale_jobs` row.
17. In Django admin change a product's price -> `Core platform > Audit logs` shows one `product.updated` row with before/after and your user.

### 8. ASSUMPTIONS MADE

1. The uploaded ZIP is the repository to convert.
2. The owner and all brand staff are Django staff users; being staff grants full access to every owner endpoint (no finer roles yet).
3. A guest order is addressable by anyone holding its random 10-letter `oid` (about 9.5 x 10^13 possibilities) so guests can pay and view their invoice. Once an order has a registered buyer, only that buyer or staff can use its `oid`.
4. The Stripe checkout endpoint remains reachable without a JWT because the frontend reaches it with a plain HTML form POST; the amount always comes from the database.
5. The PayPal v2 order response contains `purchase_units[0].amount.currency_code` and `.value`. Verification **fails closed** if that shape is absent. This is the only external payload shape assumed in this phase; please confirm against a real sandbox capture before relying on PayPal.
6. Guest carts remain addressable by `cart_id` (now cryptographically random, 30 chars) without login.
7. Cart price = `product.price`. Size-specific prices in the `Size` table are ignored, which matches what the frontend always sent.
8. Adding more than `stock_qty` to a cart is rejected. `stock_qty` is still never decremented (fixed in F-B), so this only guards obviously impossible quantities today.
9. Password-reset links are valid for 30 minutes and single-use. The email address remains in the URL path of the reset-request endpoint (frontend contract unchanged); it will appear in web-server access logs.
10. Throttle counters use Django's default local-memory cache: per process, reset on restart. Production with multiple processes needs a shared cache (flagged in Known Gaps).
11. The audit actor for anonymous API calls is recorded as `anonymous`; for the worker as `system:worker`; with no request as `system`.
12. Audit tracks these fields only: Product `price, old_price, shipping_amount, stock_qty, status`; CartOrder `payment_status, order_status, total`; CartOrderItem `delivery_status, tracking_id, delivery_couriers, qty, total`. Deletes of these models are also audited.
13. Append-only is enforced in the ORM (model and queryset). A database-level guard (Postgres trigger or revoked UPDATE/DELETE grants) is not in place.
14. The `run_worker` process is expected to run continuously in production (systemd, Supervisor, Render worker) or be invoked with `--once` from cron / Windows Task Scheduler every minute.
15. The job outbox gives at-least-once delivery; every future job handler will be written to be idempotent.
16. JWT claims unchanged (still include `vendor_id`) so the frontend's owner-dashboard routing keeps working.
17. CORS is now an allow-list of `http://localhost:5173` and `http://127.0.0.1:5173`. The production storefront origin must be added via `CORS_ALLOWED_ORIGINS`.
18. Development email goes to the terminal (`console` backend) via `.env`; production defaults to Mailgun if `DJANGO_EMAIL_BACKEND` is unset.
19. The committed `backend/.env` was replaced with development values and is now git-ignored. If the repo is under git: `git rm --cached backend/.env`.
20. Python 3.11 is the target runtime; tests were run on Python 3.12 with `setuptools<81`.

### 9. KNOWN GAPS

- **Customers who are not staff can no longer open the vendor dashboard or register as a vendor.** Intended for single-brand; the frontend still shows those links (removed with the residue later).
- The `vendor/register` page 403s for non-staff users.
- Throttling uses a per-process cache; configure a shared cache (Redis or Django's database cache) before running multiple app processes.
- `select_for_update()` in the payment confirmation is a no-op on SQLite (SQLite serialises writes anyway). Real row locking needs PostgreSQL.
- `Meta.depth` is still mutated per request inside several existing serializers (existing pattern). Concurrent POST/GET requests in one process can briefly see the wrong depth. Safe from a security standpoint now (nested users are always public-safe); it is a correctness wart to remove when those serializers are rewritten.
- Frontend behaviour after these changes was verified by a successful production build and by reading every changed call path, **not** by an automated browser test. Steps 10-17 above are the end-to-end check.
- PayPal and Stripe verification were tested with mocked provider responses only.
- `ProductDetail.jsx` passes size and colour to `addToCart` in swapped order (existing bug; size is stored as colour). Not fixed in this phase.
- Five files import `../plugin/AddToCart` while the file is `addToCart.jsx`: works on Windows, breaks Linux/Netlify builds. Not fixed (would be a rename outside this phase's scope).
- Existing correctness bugs left as-is and documented in code: tax computed as `qty x rate` instead of `price x rate`; coupons discount only the first matching item and are infinitely reusable; `CartOrder.oid` is not unique; `/create-order/` creates a new order on every call (fixed in F-B).
- `npm audit` reports 56 vulnerabilities in frontend dependencies (existing); not addressed in this phase.

### 10. NOT DONE AND WHY

- **Phase F-B** (next): `ProductVariant`, `Batch`, stock ledger + reservations with expiry, FEFO allocator, order `payment_method` / `channel` / `pincode` / `phone_e164`, order state machine, one order draft per cart. Deliberately split out so the security fixes could ship and be verified on their own.
- **Money migration** (legacy Decimal -> paise): separate reversible phase per rule 6.
- **Features 1 and 2:** blocked on Razorpay docs/samples and WhatsApp Cloud API templates, rate card and webhook samples (rule 12).
- **Removal of multi-vendor residue:** proposals R1-R21 stand, not approved, not done.

---

## PATCH F-A.1 — Product edit from the owner dashboard (COMPLETED)

### 1. PHASE COMPLETED
Bug fix, no new feature. Editing a product from the owner dashboard returned
`400 {"image": ["The submitted data was not a file. Check the encoding type on the form."]}`.

**Pre-existing, not caused by Phase F-A.** The same request was replayed against the untouched
baseline commit and produced the identical 400.

Cause: the edit screen loads a product and posts every field back. `image` arrives as the URL
string the API served (`http://127.0.0.1:8000/media/user_11/11.jpg`), and `FileField` only
accepts uploads. Three further defects were found in the same path:

- The whole update was a **full** update, so any field the form omitted was reset.
- Specifications, colours, sizes and the gallery were deleted and recreated on every save. The
  screen posts `gallery[N][image]` as the literal string `"undefined"`, so a successful save
  would have **wiped the gallery**.
- `category` was posted as `"[object Object]"` and silently ignored, so the category dropdown
  never did anything.
- On success the screen called `response.json()` on an Axios response, which has no such
  method, so a successful save still logged `Error submitting form` to the console.

### 2. FILES CREATED
| Path | Purpose |
|---|---|
| `backend/tests/test_product_update.py` | 7 regression tests for the product edit path |

### 3. FILES MODIFIED
| Path | What changed and why |
|---|---|
| `backend/vendor/views.py` | `ProductUpdateAPIView` rewritten. Update is now partial. Read-only/computed keys the form echoes back are dropped. An `image` value that is not an upload is ignored, so the stored image is kept. `category` is accepted as an id and ignored when it is the echoed object. Nested image values that are existing media URLs are resolved to their storage path, validated to exist, and attached after the row is created (a path string cannot pass `FileField` validation). A nested section is replaced only when the request carried usable entries for it, so editing a price can no longer wipe the gallery. `get_object` uses `get_object_or_404` (was `.get()`, a 500 on a bad id) |
| `frontend/src/views/vendor/UpdateProduct.jsx` | Sends `image` only when the user picked a new file; sends `category` as an id; skips read-only keys; sends existing colour/gallery image URLs back instead of `undefined`; removes the per-field `console.log` of the whole product; removes the invalid `response.json()`; shows the server's validation message on failure instead of only logging it; navigates after the success dialog |

### 4. MIGRATIONS ADDED
None.

### 5. ENV VARS ADDED
None.

### 6. TESTS ADDED
`cd backend && python -m pytest -q` -> **46 passed** (39 from F-A plus 7 below).

| Test | Proves |
|---|---|
| `test_price_edit_succeeds_when_image_is_echoed_back_as_a_url` | The reported 400 is gone |
| `test_price_edit_keeps_the_existing_product_image` | Editing a price does not clear the image |
| `test_price_edit_does_not_wipe_gallery_colors_sizes_or_specifications` | Nested data survives, including the colour's existing image |
| `test_a_new_image_upload_still_replaces_the_product_image` | Uploading a new image still works |
| `test_category_can_be_changed_by_id_and_is_untouched_when_echoed_back` | Category is editable and not clobbered |
| `test_product_edit_is_still_staff_only` | 401 anonymous, 403 customer (F-A guarantee intact) |
| `test_a_traversal_path_in_an_image_field_is_rejected` | `media/../../etc/passwd` in an image field is refused |

### 7. MANUAL VERIFICATION STEPS
1. Restart the backend and reload the frontend (hard refresh, Ctrl+Shift+R).
2. Owner dashboard -> Products -> edit a product -> change only the price -> Update.
3. Expect "Product Updated Successfully" and a redirect to the product list; the new price shows.
4. Re-open the same product: the image, gallery, colours, sizes and specifications are unchanged.
5. Change the category, save, re-open: the new category is selected (this never worked before).
6. Upload a new main image, save: the new image shows on the product page.
7. Browser console during a successful save: no errors, and no product field dump.

### 8. ASSUMPTIONS MADE
1. An image value that is not an upload means "keep what is stored", never "clear the image".
   The edit screen has no delete-image control, so no intent to clear can be expressed.
2. An existing image URL is only honoured when the file exists in storage; anything else is
   dropped. This blocks pointing a product at an arbitrary path.
3. A nested section (specifications, colours, sizes, gallery) is replaced only when the request
   carries at least one usable entry. Clearing a section entirely is therefore not possible from
   this screen and is done in Django admin. This is deliberate: the screen's `"undefined"`
   placeholder is indistinguishable from a genuine "delete everything".
4. `category` is writable by id. It remains read-only inside `ProductSerializer` (`depth=3`),
   so the view assigns it explicitly after validation.
5. Nested rows are still deleted and recreated rather than matched and updated, so their ids
   change on every save. Preserved from the original design; a rewrite is out of scope here.

### 9. KNOWN GAPS
- `AddProduct.jsx` (create) was not changed; it posts real `File` objects and works.
- Nested row ids are not stable across saves (see assumption 5).
- Verified by automated API tests and a production frontend build, not by a browser test.

### 10. NOT DONE AND WHY
- No change to `ProductSerializer`'s per-request `Meta.depth` mutation (flagged in F-A Known Gaps);
  it will be removed when that serializer is rewritten for variants in F-B.
- Phase F-B not started; this patch was pulled forward because it blocks day-to-day use.

---

## PHASE F-B — Catalog, inventory and order state (COMPLETED)

### 1. PHASE COMPLETED

Foundation work, part two. Still no customer-facing feature from the 12; this builds the
data model those features need. Acceptance criteria met:

- **Variants exist.** Every product has a sellable unit carrying SKU, price (paise) and stock.
- **Stock is a ledger.** Available stock is derived from append-only `StockMovement` rows.
  No mutable integer is incremented anywhere.
- **Stock actually moves.** It is held when an item enters a cart, transferred to the order
  at checkout, consumed on dispatch, and released on cancel or expiry. Before this phase
  stock never changed at all.
- **Batches and FEFO.** Allocation takes the soonest-expiring batch first, splits across
  batches when needed, and refuses batches inside the minimum-shelf-life window.
- **Reservations expire**, so abandoned checkouts give stock back (periodic job, 60s).
- **Order state machine.** Illegal transitions are rejected; every change is audited.
- **COD cannot be dispatched unconfirmed** — enforced in the service layer, ready for Feature 1.
- **One order per checkout.** Re-submitting the same cart returns the existing draft.
- **Channel seam.** `ChannelAdapter` with `WEBSITE` as the only implementation; orders carry `channel`.
- 80 tests passing, 1 skipped (see Known Gaps).

Bugs found and fixed on the way: the cart was never cleared after payment (so a returning
customer saw old items and could re-reserve stock), and `CartOrderItem` had no link to what
was actually sold beyond free-text size/colour.

### 2. FILES CREATED

| Path | Purpose |
|---|---|
| `backend/catalog/models.py` | `ProductVariant`: SKU, price/MRP in paise, options, perishable flag, one-default-per-product constraint |
| `backend/catalog/admin.py` | Variant admin showing price, on-hand and available |
| `backend/catalog/apps.py`, `catalog/__init__.py` | App wiring |
| `backend/catalog/migrations/0001_initial.py` | Creates `catalog_productvariant` |
| `backend/catalog/migrations/0002_backfill_default_variants.py` | One default variant per existing product; price converted to paise |
| `backend/inventory/models.py` | `Batch`, `StockMovement` (append-only ledger), `StockReservation`, `Channel`, `MovementKind` |
| `backend/inventory/services.py` | Availability, FEFO/FIFO allocation, reserve/release/consume, expiry, alerts, batch reconciliation |
| `backend/inventory/adapters.py` | `ChannelAdapter` seam; `WebsiteChannelAdapter` only |
| `backend/inventory/jobs.py` | Periodic `inventory.expire_reservations` (every 60s) |
| `backend/inventory/admin.py` | Batch admin; read-only ledger and reservation admin |
| `backend/inventory/apps.py`, `inventory/__init__.py` | App wiring |
| `backend/inventory/migrations/0001_initial.py` | Creates batch, movement, reservation tables |
| `backend/inventory/migrations/0002_backfill_opening_stock.py` | Opening batch + ADJUSTMENT movement per variant from `Product.stock_qty` |
| `backend/store/order_state.py` | Order/payment/delivery state machine; COD dispatch guard; stock hooks |
| `backend/core/phone.py` | Indian phone normalisation to E.164 and log masking |
| `backend/inventory/tests/test_inventory.py` | 40 tests for F-B |
| `backend/store/migrations/0028_variant_channel_cod_fields.py` | Order and cart field additions |

### 3. FILES MODIFIED

| Path | What changed and why |
|---|---|
| `backend/store/models.py` | Added to `CartOrder`: `payment_method`, `channel`, `pincode`, `phone_e164`, `idempotency_key` (unique). Added to `CartOrderItem`: `variant`. Added to `Cart`: `variant`, `updated_at` (drives Feature 4 abandonment). Two new choice lists. **No existing field changed or removed** |
| `backend/store/views.py` | Cart: resolves the variant, reserves stock through the ledger, replaces its own hold when quantity changes, releases on line delete, and checks authorisation before touching stock. Checkout: one draft per cart, validates `payment_method`, stores pincode and normalised phone, links each line to its variant, and transfers cart holds to the order. Payment success: routes through the state machine and clears the paid cart |
| `backend/store/serializers.py` | Product responses now include `variants` with live availability and, for perishable goods, the earliest best-before a shopper could receive |
| `backend/backend/settings.py` | Registered `catalog` and `inventory`; added four inventory settings |
| `backend/.env`, `backend/.env.example` | Four inventory variables documented |
| `backend/conftest.py` | The `product` fixture now creates a default variant and opening stock, mirroring the backfill |
| `backend/pytest.ini` | Added `inventory/tests` to testpaths |
| `frontend/src/views/plugin/addToCart.jsx` | Stops sending price and shipping (the server ignores them), and shows the real reason when the server refuses, e.g. "Only 2 left in stock" instead of failing silently |

### 4. MIGRATIONS ADDED

| Name | What it does | Apply | Roll back |
|---|---|---|---|
| `catalog.0001_initial` | Creates `catalog_productvariant` | `python manage.py migrate catalog` | `python manage.py migrate catalog zero` |
| `store.0028_variant_channel_cod_fields` | Adds variant/channel/COD/idempotency fields | `python manage.py migrate store` | `python manage.py migrate store 0027` |
| `catalog.0002_backfill_default_variants` | One default variant per product (data) | `python manage.py migrate catalog` | `python manage.py migrate catalog 0001` |
| `inventory.0001_initial` | Creates batch, movement, reservation tables | `python manage.py migrate inventory` | `python manage.py migrate inventory zero` |
| `inventory.0002_backfill_opening_stock` | Opening batch + movement per variant (data) | `python manage.py migrate inventory` | `python manage.py migrate inventory 0001` |

`python manage.py migrate` applies all five in dependency order.

**Roll back in this order** (inventory first, then catalog, then store), because `Batch.variant`
is `PROTECT` and will refuse to let a variant be deleted while batches exist:

```
python manage.py migrate inventory zero
python manage.py migrate catalog zero
python manage.py migrate store 0027
```

The full rollback-and-reapply cycle was executed on a copy of the seeded database.
Both data migrations only delete rows they created.

### 5. ENV VARS ADDED

| Name | Purpose | Example | Required |
|---|---|---|---|
| `STOCK_ALLOCATION_STRATEGY` | `FEFO` (default) or `FIFO` | `FEFO` | No |
| `STOCK_RESERVATION_TTL_MINUTES` | How long a checkout holds stock | `30` | No |
| `MIN_SHELF_LIFE_ON_DISPATCH_DAYS` | Batches expiring sooner are never auto-allocated | `30` | No |
| `EXPIRY_ALERT_DAYS` | Owner alert horizon for approaching expiry | `45` | No |

### 6. TESTS ADDED

```
cd backend
python -m pytest -q
```

Result: **80 passed, 1 skipped** (39 from F-A, 41 new).

| Group | What the tests prove |
|---|---|
| Variants | One default per product enforced by a DB constraint; backfilled paise price equals the legacy Decimal exactly; several non-default variants allowed |
| Ledger | Available stock equals the sum of movements; wrong-sign and zero movements rejected; movements are append-only; every movement is audited with actor |
| FEFO | Soonest expiry taken first; splits across batches; FIFO mode takes the oldest; a batch inside the shelf-life window is never allocated though it still counts as on hand; an expired batch is never allocated; expiry alerts and expired-unsold reports |
| Reservations | A hold lowers available but not on hand; over-reserving fails and holds nothing; expired holds release stock; consuming an order decrements the right batches **exactly once** when run twice; releasing returns stock |
| Channel seam | Only `WEBSITE` is registered; an unknown channel raises; a new adapter can be added and routes through the same ledger |
| Order state | Illegal transitions rejected; cancelling releases stock; **an unconfirmed COD order cannot be dispatched and its stock does not leave**; a prepaid order's dispatch consumes stock once and not again as it moves to Delivered |
| Checkout | Adding to cart holds stock and refuses more than available; changing quantity replaces the hold instead of stacking; removing a line returns stock; **checking out twice with one cart creates one order**; pincode, payment method, channel, E.164 phone and variant all recorded; holds move from cart to order; invalid payment method rejected |
| Phone | Five Indian formats normalise to `+919876543210`; invalid numbers rejected rather than guessed; masking keeps four digits |

### 7. MANUAL VERIFICATION STEPS

From `backend\` with the venv active:

1. `python manage.py migrate` -> five migrations apply.
2. `python -m pytest -q` -> `80 passed, 1 skipped`.
3. `python manage.py runserver`, and in a second terminal `python manage.py run_worker`.
4. Open `http://127.0.0.1:8000/api/v1/products/`. Each product now has a `variants` array with `sku`, `price` and `available_qty`.
5. Note a product's `available_qty`, add that product to your cart in the storefront, and reload the API. `available_qty` has dropped by the quantity you added, while on-hand has not.
6. Remove the line from the cart. `available_qty` goes back up.
7. Django admin -> **Inventory -> Stock reservations**: your holds are listed with an expiry time.
8. Add something to the cart, then leave it. After `STOCK_RESERVATION_TTL_MINUTES` the worker flips the reservation to EXPIRED and availability returns. (Set the value to `1` in `.env` and restart to see it quickly.)
9. Try to add an absurd quantity (say 99999). The storefront shows "Only N left in stock" instead of failing silently.
10. Complete checkout twice from the same cart without paying. Django admin -> **Orders** shows one order, not two.
11. Open that order: `payment method`, `pincode`, `phone e164` and `channel` are filled, and each line has a `variant`.
12. Django admin -> **Inventory -> Batches**: an `OPENING-<SKU>` batch per product with your old `stock_qty`. **Their best-before is empty — set real dates or write them off before trusting expiry alerts.**
13. Add a real batch (Batches -> Add) with a near best-before date, then place an order: **Stock movements** shows the allocation came from the soonest-expiring batch.
14. Mark an order line as shipped in the admin. If the order is COD and unconfirmed, the service layer refuses (Feature 1 will add the confirm button); for a prepaid order a `SALE_OUT` movement appears and on-hand drops.

### 8. ASSUMPTIONS MADE

1. Every product gets exactly one default variant named "Default", with the product's SKU as the variant SKU (a numeric suffix is added if that SKU is already taken).
2. Existing `Size` and `Color` rows are **not** converted into variants. They stay decorative, exactly as the storefront already treats them. Converting them is a catalogue decision for the owner, not a migration I should make silently.
3. Variant prices are copied into paise, but **the legacy Decimal columns remain the source of truth for pricing**. Nothing reads `price_paise` for checkout yet; that switch happens in the money migration.
4. Opening stock becomes one batch per variant with **no best-before**, because the shelf life of pre-existing stock is unknown, and `cost_per_unit_paise = 0`, because historical cost is unknown. Both must be corrected by the owner before margin (Feature 12) and expiry alerts are meaningful.
5. `Batch.quantity_remaining` is a **derived property, not a stored column** as the brief listed it. A stored counter would be a second source of truth able to drift from the ledger, which contradicts Feature 10's acceptance criterion. Reported as a deliberate deviation.
6. Cart lines reserve stock immediately on add, not at checkout. This is stricter than most Indian D2C stores (which reserve at payment) and can make items look unavailable while others browse. `STOCK_RESERVATION_TTL_MINUTES` (default 30) bounds it; lower it if it feels aggressive.
7. `resolve_variant` matches on free-text size/colour and otherwise falls back to the default variant, because the storefront has no variant picker yet. Products keep one variant until the owner creates more.
8. Minimum shelf life (30 days) and the expiry alert horizon (45 days) are guesses. Set them to your real dispatch policy.
9. An expired or too-fresh batch still counts as **on hand** but is not **available**. Stock that physically exists is never hidden from the ledger; it is only excluded from allocation.
10. `ADJUSTMENT` movements may be positive or negative; all other kinds are sign-checked.
11. Order status values are unchanged. The state machine constrains how they may change; it does not rename them. The transition tables encode my reading of the existing flow and are one edit away if your operations differ.
12. `idempotency_key` is the `cart_id`. One cart yields one order; starting a fresh cart starts a fresh order.
13. Phone normalisation accepts Indian mobile numbers only (10 digits starting 6-9, with optional 0/+91/0091 prefixes). Anything else stores an empty `phone_e164` rather than a guess, so international customers will have no WhatsApp number until this is widened.
14. The paid cart is deleted once payment is confirmed. Reservations already belong to the order, so this does not release stock.
15. Dispatch consumes stock when a line first enters `Shipping Processing`, not at payment. If you pick and pack before marking the order, move the hook.
16. `can_dispatch()` reads `cod_confirmed_at` defensively so it works both before and after the Feature 1 migration; today no COD order can be dispatched at all, because nothing sets that field yet.
17. `Product.stock_qty` is left in place and still shown in the admin, but is now **stale** — it is no longer the source of truth. It will be removed or turned into a derived display in a later phase.

### 9. KNOWN GAPS

- **The concurrency test is skipped on SQLite and has not yet been run on PostgreSQL.** `select_for_update` is a no-op on SQLite, so the test refuses to pass for the wrong reason. PostgreSQL could not be installed in my build environment, so Feature 10's "two concurrent checkouts for the last unit" acceptance criterion is **written but not yet demonstrated**. Run it against Postgres before trusting concurrent checkout: set `DATABASE_URL` to a Postgres URL and run `python -m pytest inventory/tests -k concurrent -q`.
- `Product.stock_qty` and the ledger will drift the moment someone edits `stock_qty` in the admin. Nothing reconciles them yet.
- No owner UI for batches beyond Django admin, and no production-receipt screen.
- Expiry alerts are computed (`batches_nearing_expiry`, `expired_unsold_batches`) but not yet delivered anywhere — that is Feature 5's alerting, in Phase 2.
- The storefront has no variant picker, no stock indicator on the product page and no best-before display yet. The API exposes all three; the UI work belongs with Features 2, 3 and 5.
- Reservations are not yet taken for orders created outside our checkout; the seam exists but no other channel writes to it.
- `perishable` defaults to False on every backfilled variant, so no product shows a best-before until the owner ticks it.
- Frontend verified by production build and by reading each changed path, not by an automated browser test.
- All F-A known gaps still stand.

### 10. NOT DONE AND WHY

- **Money migration** (legacy Decimal -> paise everywhere): still its own phase. Variants carry paise, but checkout maths still uses the legacy Decimal columns, so nothing changed for customers.
- **Tax and coupon bugs** unchanged and still flagged in code; both belong with the pricing work.
- **Features 1 and 2** remain blocked on Razorpay and WhatsApp details from the owner.
- **Removal of multi-vendor residue:** proposals R1-R21 still not approved, still not done.
