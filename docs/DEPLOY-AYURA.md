# Putting Ayura online for free

Covers the store as built through **phase F** (catalogue, shipping and COD fees, dispatch checks
and samples, kits, customer support). If you deployed at phase A, the parts that changed are
listed in [What changed since phase A](#what-changed-since-phase-a) — read that and you can skip
the rest.

Ayura runs as its own store, completely separate from Noore: its own GitHub repository, Neon
database, Render backend, Vercel storefront, Cloudinary account and Razorpay account. Nothing is
shared, so a problem (or a change) in one store can never reach the other.

The storefront goes on Vercel, the backend on Render, the database on Neon and photos on
Cloudinary. All free, no card, no domain. Allow about an hour the first time.

**What "free" means here.** These tiers are meant for demos and side projects, and most of them
do not allow running a real business on them. When Ayura takes real money, move to a small paid
server with `docs/DEPLOY.md`. Nothing you do here is wasted.

**The one rough edge.** A free Render service sleeps after 15 minutes without visitors, and the
next visitor waits while it wakes. The storefront shows real products from its cache and says
plainly that the server is starting (see `frontend/src/utils/apiCache.js`). The keep-awake
workflow in step 6 makes the sleep rare.

---

## What changed since phase A

If your store is already online, these are the only things to do:

| # | Change | What to do |
|---|---|---|
| 1 | **Migrations.** Phases B–F add 14 of them, including the new `support` app | Nothing. `build.sh` runs `migrate` on every deploy. Just push and watch the build log. |
| 2 | **`MIN_SHELF_LIFE_ON_DISPATCH_DAYS` is now `0`**, not 30 (ROADMAP Z1) | If you set it to `30` on Render, **delete the variable** or set it to `0`. At 30 the store refuses to dispatch any batch with under a month of shelf life left. |
| 3 | **Customers can now upload photos** (phase F support threads) | `CLOUDINARY_URL` goes from "or product photos vanish" to **mandatory**: without it you lose a customer's evidence of a damaged parcel. See step 2. |
| 4 | **Tighten the support rate limit** before you take real orders | Add `THROTTLE_SUPPORT=6/min` on Render. Step 2 explains why 20/min is too loose with file uploads. |
| 5 | **The grievance-officer fields are blank** and the Contact page shows nothing until you fill them | Admin area → Store settings → Grievance officer. See [Before your first real order](#before-your-first-real-order). |
| 6 | **`DJANGO_EMAIL_BACKEND` is now set in `render.yaml`** to the dummy backend | Nothing, unless you already set it by hand — in which case your dashboard value wins and still works. |
| 7 | New optional settings: `THROTTLE_SUPPORT`, `SUPPORT_LINK_HOURS`, `SUPPORT_MAX_PHOTOS_PER_MESSAGE`, `SUPPORT_PHOTO_MAX_MB`, `SUPPORT_NOTIFY_EMAILS`, `EXPIRY_ALERT_DAYS` | All have working defaults. Set `SUPPORT_NOTIFY_EMAILS` if you want an email when a customer writes in. |
| 8 | **Never set `DJANGO_ENV_FILE` on Render** | It exists only so the test suite can read the shipped defaults. Set to a real path it would load settings from that file instead. There is no `.env` on Render, so leave it unset. |

---

## Before you start

| You need | Where | Cost |
|---|---|---|
| A GitHub account, with Ayura in its own repository | github.com | Free |
| A Render account | render.com | Free, no card |
| A Neon account | neon.tech | Free, no card |
| A Cloudinary account (a new one for Ayura) | cloudinary.com | Free, no card |
| A Vercel account | vercel.com | Free, no card |
| A Razorpay account for Ayura (only for step 7) | razorpay.com | Free in test mode |

### Make the Ayura repository (keeps Noore's history)

From PowerShell, in the folder where you keep projects. The first line copies the Noore project
with its whole history into a new folder called `ayura`; Noore's own folder is not touched.

    git clone "C:\path\to\noore\Completed Source Code" ayura
    cd ayura
    git remote remove origin
    git checkout -b phase/A-rebrand

Apply the Phase A files into this folder, then:

    git add -A
    git commit -m "Phase A: fork Noore into Ayura"

On github.com: **New repository**, name it `ayura-store`, **Private**, **Create**. Then:

    git remote add origin https://github.com/YOURNAME/ayura-store.git
    git push -u origin phase/A-rebrand

Merge each approved phase branch into `main` on GitHub, and deploy from `main`.

**`backend/.env`, `backend/db.sqlite3` and `backend/media/` are not pushed** (`.gitignore`
excludes them). That is correct: secrets never go into a repository, and the online store starts
with its own empty database.

**Never copy Noore's `backend/.env` into Ayura.** Make a fresh one from `backend/.env.example`
with a new `DJANGO_SECRET_KEY`:

    python -c "import secrets; print(secrets.token_urlsafe(64))"

If the two stores shared one key, sign-in tokens and password-reset links signed by one would be
accepted by the other.

---

## Step 1: the database (Neon)

1. neon.tech, sign in with GitHub.
2. **Create project**. Name: `ayura`. Region: the one nearest India (Singapore if offered).
3. Copy the **Connection string**. It looks like:

       postgresql://ayura_owner:AbC123@ep-cool-name-123456.ap-southeast-1.aws.neon.tech/ayura?sslmode=require

4. Keep it somewhere private for step 3. **Treat it like a password.**

> Why not Render's own free database? It is deleted 30 days after it is created, data and all.

PostgreSQL is also what the concurrency tests need, so this is the same engine the stock
locking was tested against (two shoppers racing for the last unit, or the last kit).

---

## Step 2: photo storage (Cloudinary)

1. Sign up at cloudinary.com with a new account for Ayura.
2. On the dashboard, copy the **API Environment variable**: everything after `CLOUDINARY_URL=`,
   which looks like `cloudinary://419455555555555:aBcDeF-gHiJkLmNoPqRsTuVwXyZ@dxyz1234`.

**This is mandatory, not optional.** Free Render services have no disk of their own, so without
it everything uploaded disappears on the next restart or deploy. Since phase F that includes
**photos your customers send you** of a damaged or leaking parcel — the evidence for their
complaint, and for yours with the courier.

### Size and abuse, with real numbers

At the time of writing Cloudinary's free plan was **25 monthly credits**, 1 credit being 1 GB of
storage **or** 1 GB of CDN bandwidth — **check [the current plan](https://cloudinary.com/pricing)
yourself, because this is their pricing and it changes.** On those numbers, and the store's own
defaults of 3 photos per message at 5 MB each, 25 GB is roughly 1,700 full-size support
messages. Your real catalogue and its product photos are nowhere near that. Storage is not your
problem.

**The rate limit is.** `THROTTLE_SUPPORT` ships at `20/min`, and a guest needs no account to open
a thread. At 3 × 5 MB per message that is up to 900 MB a minute from one address, so a bored
attacker could burn the month's credits in under half an hour. A real customer never sends 20
support messages in a minute. Before you take real orders, on Render add:

    THROTTLE_SUPPORT=6/min

and if you want a smaller blast radius still, `SUPPORT_PHOTO_MAX_MB=3`. A phone photo is
comfortably under 3 MB. Cloudinary's dashboard shows credit use; check it after your first week.

---

## Step 3: the backend (Render)

1. render.com, sign in with GitHub.
2. **New** > **Blueprint**, choose `ayura-store`. Render reads `render.yaml` and offers a service
   called **ayura-api**. If that name is taken, Render adds a few characters to the address;
   use whatever address it shows you from here on. Click **Apply**.
3. The first build fails or comes up unhealthy. That is expected: the values only you can
   supply are still blank. Open **ayura-api** > **Environment** and fill in the ones marked
   "you" in the table below (leave the Vercel ones blank until step 5).
4. **Save, rebuild and deploy.** When it is up, open:

       https://<your-render-address>/api/v1/health/

   You want `"status": "ok"`, `"database": true`, `"cache": true`. `worker` is an object, not a
   flag — `{"ok": false, "seconds_since_last_job": null}` until step 6, and the plain
   `/health/` address stays `"ok"` whatever the worker is doing. Only `?strict=1` fails on it.

5. Create your admin login. Render's free plan has **no Shell tab**, so do it from your own
   computer, pointed at the Neon database for the length of three commands:

       cd backend
       .\venv\Scripts\Activate.ps1
       $env:DATABASE_URL = "<your Neon connection string>"
       python manage.py createsuperuser
       python manage.py claim_shop --email you@example.com
       Remove-Item Env:DATABASE_URL

   Use the same email in both. **Always run the last line**, or your next local command runs
   against the online database.

   Then sign out and back in on the storefront: the admin area is driven by the `vendor_id`
   claim in your sign-in token, so a token issued before `claim_shop` does not have it.

### Backend environment variables (Render)

`render.yaml` sets the first group; you type the rest in **Environment**. Every variable is also
documented in `backend/.env.example`.

| Key | Value | Who sets it |
|---|---|---|
| `PYTHON_VERSION` | `3.11.9` | render.yaml |
| `DJANGO_SECRET_KEY` | random, generated by Render | render.yaml |
| `JOBS_RUN_TOKEN` | random, generated by Render (step 6 copies it) | render.yaml |
| `DJANGO_DEBUG` | `False` | render.yaml |
| `DJANGO_CACHE` | `db` | render.yaml |
| `SECURE_SSL_REDIRECT` | `True` | render.yaml |
| `ENABLED_PAYMENT_PROVIDERS` | `razorpay,cod` | render.yaml |
| `STORE_NAME` | `Ayura` | render.yaml |
| `WEB_CONCURRENCY` | `2` | render.yaml |
| `DJANGO_EMAIL_BACKEND` | the dummy backend, until you have an email provider | render.yaml |
| `DATABASE_URL` | the Neon connection string (step 1) | you |
| `CLOUDINARY_URL` | the `cloudinary://...` value (step 2) | you |
| `SITE_URL` | your Vercel address, no trailing slash (step 5) | you |
| `CORS_ALLOWED_ORIGINS` | your Vercel address, no trailing slash (step 5) | you |
| `CSRF_TRUSTED_ORIGINS` | your Vercel address, no trailing slash (step 5) | you |
| `THROTTLE_SUPPORT` | `6/min` before real orders (step 2) | you |
| `SUPPORT_NOTIFY_EMAILS` | your email, to be told when a customer writes in; blank sends none | you, optional |
| `DEFAULT_FROM_EMAIL` | the sender address, once you have an email provider | you, later |
| `MAILGUN_API_KEY`, `MAILGUN_SENDER_DOMAIN` | from Mailgun, if you choose it | you, later |
| `ERROR_REPORT_EMAILS` | your email, once email works | you, later |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Ayura's Razorpay test keys (step 7) | you, optional |
| `RAZORPAY_WEBHOOK_SECRET` | the secret you type on the Razorpay webhook (step 7) | you, optional |

`RENDER_EXTERNAL_HOSTNAME` is set by Render itself; the backend adds it to the allowed hosts.

> **Why the dummy email backend:** the real default is Mailgun, and with no Mailgun keys every
> email fails and is retried until it gives up. The dummy backend quietly drops them instead.
> Do not use the console backend online: it would write customers' emails and addresses into the
> Render logs. **When you do configure Mailgun, remember to remove this variable** — otherwise
> everything keeps being silently dropped and you will think the provider is broken.

**Settings to leave alone**, listed because they are the ones people ask about:

- `MIN_SHELF_LIFE_ON_DISPATCH_DAYS` — default `0`, which is the rule the store is built around
  (ROADMAP Z1): an **expired** batch is never dispatched, and nothing else is held back. The
  dispatch screen flags stock that is close to its date and leaves the decision to you. Set it
  to a number only if you want a hard margin, and know that it will refuse to allocate stock you
  can see on the shelf.
- `EXPIRY_ALERT_DAYS` — default `45`, the horizon for "due soon" on the Stock & expiry screen.
- `SUPPORT_LINK_HOURS` — default `720` (30 days), how long a guest's link to their own support
  thread keeps working.
- `STOCK_RESERVATION_TTL_MINUTES` — default `30`, how long a cart holds stock before releasing it.
- `DJANGO_ENV_FILE` — **do not set this.** It exists so the test suite can read the defaults a
  fresh install has, by pointing it at a file that does not exist. On Render there is no `.env`
  to load anyway.

---

## Step 4: the storefront (Vercel)

1. vercel.com, **Add New** > **Project**, pick `ayura-store`.
2. **Root Directory**: **Edit**, choose `frontend`. The storefront is not at the top of the
   repository.
3. Framework says **Vite**. Leave the build settings alone (`frontend/vercel.json` sets them).
4. **Environment Variables**:

   | Key | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://<your-render-address>/api/v1/` |
   | `VITE_SERVER_URL` | `https://<your-render-address>/` |
   | `VITE_STORE_NAME` | `Ayura` |
   | `VITE_SUPPORT_EMAIL` | your support email (a placeholder is shown until you set it) |
   | `VITE_WHATSAPP_NUMBER` | `917888548215` |
   | `VITE_TAGLINE` | optional; default "If we wouldn’t use it at home, we don’t bottle it." |
   | `VITE_STORE_DESCRIPTION` | optional; the description search engines show |

   Keep the trailing slashes exactly as shown. `VITE_API_BASE_URL` also tells the page to open
   its connection to the backend early (see `frontend/vite.config.js`).

5. **Deploy.** You get an address like `https://ayura-store.vercel.app`. If the name you want is
   taken, change it under **Settings** > **Domains**.

> These values are baked in when the site is built. Change one later and you must redeploy on
> Vercel for it to take effect.

---

## Step 5: introduce them to each other

On Render, **ayura-api** > **Environment**, set these three to your Vercel address with **no
trailing slash**, for example `https://ayura-store.vercel.app`:

| Key | Value |
|---|---|
| `SITE_URL` | your Vercel address |
| `CORS_ALLOWED_ORIGINS` | your Vercel address |
| `CSRF_TRUSTED_ORIGINS` | your Vercel address |

Save; Render redeploys. Open your Vercel address: the storefront loads and talks to the backend.

`SITE_URL` is not only cosmetic. Every link the backend builds uses it: the payment return
address, a guest's "create your account" link, and a guest's link to their own support thread.
Wrong here means those links go nowhere.

---

## Step 6: keep it awake and run the background jobs

Order emails, **support emails**, payment reconciliation and abandoned-checkout expiry normally
run in a second process, which the free plan does not have. The workflow
`.github/workflows/keep-awake.yml` calls the backend every ten minutes instead: one request
keeps Render and Neon awake, a second runs the jobs that are due.

1. On Render, **ayura-api** > **Environment**, reveal `JOBS_RUN_TOKEN` and copy it.
2. On GitHub, `ayura-store` > **Settings** > **Secrets and variables** > **Actions**:
   - tab **Variables** > **New repository variable**: name `API_BASE_URL`, value
     `https://<your-render-address>/api/v1/` (with `/api/v1/` and the trailing slash);
   - tab **Secrets** > **New repository secret**: name `JOBS_RUN_TOKEN`, value the token you copied.
3. **Actions** tab > **keep-awake** > **Run workflow**. Two green ticks mean both jobs worked.
   After that it runs on its own.

Then `https://<your-render-address>/api/v1/health/?strict=1` answers 200 with
`"worker": {"ok": true, ...}`. Before the first job runs, that address answers 503 — which is
the point of `?strict=1`, and why your uptime monitor should use the plain `/health/` instead.

The workflow has **no built-in address**: without `API_BASE_URL` it says so and does nothing. A
copied workflow can therefore never ping another store's backend.

> GitHub pauses scheduled workflows in a repository with no activity for 60 days, and can run
> them late when it is busy. For a store that must never be slow, also add a free
> cron-job.org check of the health address every 5 minutes.

**Support threads do not depend on any of this.** The conversation is in the database the moment
the customer sends it, and your inbox shows it whether or not an email ever goes out. Jobs being
down delays the notification, not the report.

---

## Step 7: payments (optional)

Cash on Delivery works with nothing configured. For UPI and cards, in **Ayura's own** Razorpay
account, in **Test Mode**:

1. **Account & Settings** > **API Keys** > **Generate Test Key**.
2. On Render add `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`.
3. **Account & Settings** > **Webhooks** > **Add New Webhook**:
   - URL: `https://<your-render-address>/api/v1/payments/razorpay/webhook/`
   - Secret: a long random string; the same string goes on Render as `RAZORPAY_WEBHOOK_SECRET`
   - Event: `payment.captured`
4. Save both sides and let Render redeploy. Test UPI id `success@razorpay`; test card
   `4100 2800 0000 1007`, any future expiry, any CVV.

No real money moves in test mode. Live keys need Razorpay's KYC for the business that sells
under the Ayura name; which business that is (and whether it is the same one as Noore's) is
your decision and Razorpay's, not something set in code.

---

## Step 8: fill the shop

Sign in on your Vercel address with the superuser from step 3. Everything below is in the
**Admin area**, from the sidebar:

1. **Add product** — photo, title, description.
2. **Products** > **Sizes & stock** on a product:
   - **Sizes**: one row per size, each with its own price, MRP, net quantity (g or ml) and
     packed shipping weight. Tick **Sample** for something you give away, or **Kit** for a size
     made of other sizes.
   - **Stock**: add a batch (how many you made, when, and the use-by date if you know it). Stock
     is a ledger, so quantities are never edited — only corrected by another movement.
   - **Details**: category, the benefit line on the product tile, how to use, ingredients,
     cautions. Words that read as a medical claim are flagged while you type; saving is never
     blocked, it is a prompt to check your wording.
3. **Kits** — say what goes inside each kit size. The screen shows how many kits each part
   allows and names the one holding it back.
4. **Store settings** — shipping charge, free-shipping threshold, Cash on Delivery and its fee,
   the label details shown on every product page, and the grievance-officer block.
5. **Categories**, **Stock & expiry**, **Samples**, **Support**, **Review moderation** as you
   need them.

`python manage.py seed_ayura` (sample products) refuses to run with `DEBUG` off, so it can never
put sample products into the online store.

---

## Before your first real order

The store works without these. Taking money from a stranger without them is a different matter.

| # | What | Where |
|---|---|---|
| 1 | **Grievance-officer details.** The Contact page shows nothing until you fill in a name. The Consumer Protection (E-Commerce) Rules expect an e-commerce store to publish them; whether they are required of your business, and in what wording, is **ROADMAP L4 and a question for your professional** — this codebase deliberately writes none of it | Admin area → Store settings → Grievance officer |
| 2 | **Replace the placeholder policies.** Shipping, Returns and Refunds, Privacy, Terms are placeholder text and say so on the page. Edit `frontend/src/views/policy/policies.js`, then set `PLACEHOLDER_COPY = false` in the same file, commit and push | the repository, then Vercel redeploys |
| 3 | **Replace the About page** text | `frontend/src/views/policy/About.jsx` |
| 4 | **Tighten `THROTTLE_SUPPORT`** to `6/min` (step 2) | Render → Environment |
| 5 | **The label details** on every product page: maker name, address, country of origin, consumer care. Also L3, also your professional's call | Admin area → Store settings → Product information |
| 6 | **An email provider.** Until one is set, no order confirmation and no support acknowledgement is delivered. A guest's support link is shown **on screen** as well for exactly this reason — but tell them to keep it | Mailgun, then the Render variables in step 3 |
| 7 | **Real product photos**, and real use-by dates on your batches | Admin area |

---

## Everyday use

| Task | How |
|---|---|
| Deploy a change | `git push` to `main`. Render and Vercel both rebuild on their own; `build.sh` runs `migrate` for you. |
| See backend errors | Render > ayura-api > **Logs** |
| Answer a customer | Admin area > **Support**. The sidebar shows how many you have not looked at. |
| Pack an order | Admin area > **Orders** > open one. **Packing** shows the batch each line goes out from and flags expired or undated stock. |
| Back up the database | Neon > your project > **Backups**, or `pg_dump` as in `docs/DEPLOY.md` |
| Check the jobs are running | `/api/v1/health/?strict=1` answers 200 with `"worker": {"ok": true, ...}`; GitHub **Actions** shows green runs |
| Check Cloudinary use | Cloudinary dashboard > credits, after your first week (step 2) |

---

## When something is wrong

| What you see | What it means |
|---|---|
| Render build log says `./build.sh: Permission denied` | An old `render.yaml`. Ayura's runs `bash build.sh`, which does not need the file to be executable |
| Storefront loads but shows no products; the browser console says CORS | `CORS_ALLOWED_ORIGINS` does not exactly match the Vercel address, or ends in a slash |
| `DisallowedHost` in the Render log | You opened the backend on an address that is not its own; use the `.onrender.com` one |
| Photos vanish after a redeploy — product photos **or** a customer's support photos | `CLOUDINARY_URL` is missing or wrong (step 2) |
| Admin pages look unstyled | `collectstatic` did not run; redeploy with **Clear build cache** |
| Health says `"cache": false` | `createcachetable` did not run; redeploy with **Clear build cache** |
| keep-awake says `API_BASE_URL is not set` | Step 6, the repository **variable** (not secret) is missing |
| keep-awake jobs step fails with 404 | The `JOBS_RUN_TOKEN` secret on GitHub does not match the one on Render |
| Emails never arrive | Expected while `DJANGO_EMAIL_BACKEND` is the dummy backend. If you have configured Mailgun, **delete that variable** |
| A guest's support link opens nothing, or goes to the wrong place | `SITE_URL` is wrong or has a trailing slash (step 5). Links already emailed carry the old address |
| A guest says their support link stopped working | It expires after `SUPPORT_LINK_HOURS` (30 days). They can get it back with their order number and email, at `/support/find` |
| A customer's photo is refused | It is not really an image. The store opens the bytes rather than trusting the file name, so a renamed PDF is refused on purpose |
| Stock you can see on the shelf will not allocate | `MIN_SHELF_LIFE_ON_DISPATCH_DAYS` is set above 0 on Render, or the batch is past its use-by date |
| A kit shows as sold out with stock in the parts | One part is short, switched off, or out of date. Admin area > **Kits** names the one holding it back |
| Nothing in the admin area, or you cannot sign in | The database is new; run `createsuperuser` and `claim_shop` (step 3), then sign out and back in |
| `python manage.py check --deploy` warns about HSTS | Expected. `SECURE_HSTS_SECONDS` starts at an hour on purpose; subdomains and preload only matter once you have a custom domain |

---

## What this deployment does not have

- **A custom domain.** The `*.vercel.app` address is used for now.
- **Real emails.** Nothing is sent until an email provider is configured, and a provider will
  want a sending domain. Support threads work regardless; the acknowledgement does not arrive.
- **Live payments.** Test mode until Ayura's Razorpay KYC is done.
- **Backups you control.** Neon's free plan keeps its own; there is no off-site copy.
- **Always-on.** The keep-awake workflow narrows the sleep; it does not remove it.
- **Deleted photos.** Nothing removes a support photo from Cloudinary, including when the
  conversation is closed.

`docs/DEPLOY.md` covers the paid single-server setup that fixes the first five.
