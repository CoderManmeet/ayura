# Putting Ayura online for free

Ayura runs as its own store, completely separate from Noore: its own GitHub repository, Neon
database, Render backend, Vercel storefront, Cloudinary account and Razorpay account. Nothing is
shared, so a problem (or a change) in one store can never reach the other.

The storefront goes on Vercel, the backend on Render, the database on Neon and product photos on
Cloudinary. All free, no card, no domain. Allow about an hour the first time.

**What "free" means here.** These tiers are meant for demos and side projects, and most of them
do not allow running a real business on them. When Ayura takes real money, move to a small paid
server with `docs/DEPLOY.md`. Nothing you do here is wasted.

**The one rough edge.** A free Render service sleeps after 15 minutes without visitors, and the
next visitor waits while it wakes. The storefront shows real products from its cache and says
plainly that the server is starting (see `frontend/src/utils/apiCache.js`). The keep-awake
workflow in step 6 makes the sleep rare.

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

Merge `phase/A-rebrand` into `main` on GitHub when you have approved the phase, and deploy from
`main`.

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

---

## Step 2: photo storage (Cloudinary)

1. Sign up at cloudinary.com with a new account for Ayura.
2. On the dashboard, copy the **API Environment variable**: everything after `CLOUDINARY_URL=`,
   which looks like `cloudinary://419455555555555:aBcDeF-gHiJkLmNoPqRsTuVwXyZ@dxyz1234`.

> Without it, every product photo disappears the first time the backend restarts: free Render
> services have no disk of their own.

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

   You want `"status": "ok"`, `"database": true`, `"cache": true`. `worker` stays `false` until
   step 6.

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
| `DATABASE_URL` | the Neon connection string (step 1) | you |
| `CLOUDINARY_URL` | the `cloudinary://...` value (step 2) | you |
| `SITE_URL` | your Vercel address, no trailing slash (step 5) | you |
| `CORS_ALLOWED_ORIGINS` | your Vercel address, no trailing slash (step 5) | you |
| `CSRF_TRUSTED_ORIGINS` | your Vercel address, no trailing slash (step 5) | you |
| `DJANGO_EMAIL_BACKEND` | `django.core.mail.backends.dummy.EmailBackend` until you have an email provider | you |
| `DEFAULT_FROM_EMAIL` | the sender address, once you have an email provider | you, later |
| `MAILGUN_API_KEY`, `MAILGUN_SENDER_DOMAIN` | from Mailgun, if you choose it | you, later |
| `ERROR_REPORT_EMAILS` | your email, once email works | you, later |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Ayura's Razorpay test keys (step 7) | you, optional |
| `RAZORPAY_WEBHOOK_SECRET` | the secret you type on the Razorpay webhook (step 7) | you, optional |

`RENDER_EXTERNAL_HOSTNAME` is set by Render itself; the backend adds it to the allowed hosts.

> **Why the dummy email backend:** the default is Mailgun, and with no Mailgun keys every order
> email fails and is retried until it gives up. The dummy backend quietly drops emails instead.
> Do not use the console backend online: it would write customers' emails and addresses into the
> Render logs.

Leave everything else at its default. Of note for Ayura: `MIN_SHELF_LIFE_ON_DISPATCH_DAYS` (30)
and `EXPIRY_ALERT_DAYS` (45) are revisited in phase D.

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

---

## Step 6: keep it awake and run the background jobs

Order emails, payment reconciliation and abandoned-checkout expiry normally run in a second
process, which the free plan does not have. The workflow `.github/workflows/keep-awake.yml`
calls the backend every ten minutes instead: one request keeps Render and Neon awake, a second
runs the jobs that are due.

1. On Render, **ayura-api** > **Environment**, reveal `JOBS_RUN_TOKEN` and copy it.
2. On GitHub, `ayura-store` > **Settings** > **Secrets and variables** > **Actions**:
   - tab **Variables** > **New repository variable**: name `API_BASE_URL`, value
     `https://<your-render-address>/api/v1/` (with `/api/v1/` and the trailing slash);
   - tab **Secrets** > **New repository secret**: name `JOBS_RUN_TOKEN`, value the token you copied.
3. **Actions** tab > **keep-awake** > **Run workflow**. Two green ticks mean both jobs worked.
   After that it runs on its own.

Then `https://<your-render-address>/api/v1/health/?strict=1` reports `worker: true`.

The workflow has **no built-in address**: without `API_BASE_URL` it says so and does nothing. A
copied workflow can therefore never ping another store's backend.

> GitHub pauses scheduled workflows in a repository with no activity for 60 days, and can run
> them late when it is busy. For a store that must never be slow, also add a free
> cron-job.org check of the health address every 5 minutes.

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

Sign in on your Vercel address with the superuser from step 3, then:

1. **Admin** (top right) > **Add product**: photo, title, description, price, MRP, stock.
2. Until phase B adds the sizes and stock screens, sizes and extra stock are added in Django
   admin at `https://<your-render-address>/admin/`:
   - **Catalog** > **Product variants**: one row per size (name `30 ml`, options
     `{"Size": "30 ml"}`, price and MRP in paise: ₹449 is `44900`).
   - **Inventory** > **Batches**: add a batch to put stock in.
3. The About page and the policy pages are still placeholder text, and say so on the page. They
   live in `frontend/src/views/policy/`. Replace the text, set `PLACEHOLDER_COPY` to `false` in
   `policies.js`, commit and push; Vercel redeploys on its own.

`python manage.py seed_ayura` (sample products) refuses to run with `DEBUG` off, so it can never
put sample products into the online store.

---

## Everyday use

| Task | How |
|---|---|
| Deploy a change | `git push` to `main`. Render and Vercel both rebuild on their own. |
| See backend errors | Render > ayura-api > **Logs** |
| Back up the database | Neon > your project > **Backups**, or `pg_dump` as in `docs/DEPLOY.md` |
| Check the jobs are running | `/api/v1/health/?strict=1` says `worker: true`; GitHub **Actions** shows green runs |

---

## When something is wrong

| What you see | What it means |
|---|---|
| Render build log says `./build.sh: Permission denied` | An old `render.yaml`. Ayura's runs `bash build.sh`, which does not need the file to be executable |
| Storefront loads but shows no products; the browser console says CORS | `CORS_ALLOWED_ORIGINS` does not exactly match the Vercel address, or ends in a slash |
| `DisallowedHost` in the Render log | You opened the backend on an address that is not its own; use the `.onrender.com` one |
| Product photos vanish after a redeploy | `CLOUDINARY_URL` is missing or wrong |
| Admin pages look unstyled | `collectstatic` did not run; redeploy with **Clear build cache** |
| Health says `"cache": false` | `createcachetable` did not run; redeploy with **Clear build cache** |
| keep-awake says `API_BASE_URL is not set` | Step 6, the repository **variable** (not secret) is missing |
| keep-awake jobs step fails with 404 | The `JOBS_RUN_TOKEN` secret on GitHub does not match the one on Render |
| Emails never arrive | Expected until an email provider is configured |
| Nothing in the admin area, or you cannot sign in | The database is new; run `createsuperuser` and `claim_shop` (step 3) |

---

## What this deployment does not have

- **A custom domain.** The `*.vercel.app` address is used for now.
- **Real emails.** Nothing is sent until an email provider is configured, and a provider will
  want a sending domain.
- **Live payments.** Test mode until Ayura's Razorpay KYC is done.
- **Backups you control.** Neon's free plan keeps its own; there is no off-site copy.
- **Always-on.** The keep-awake workflow narrows the sleep; it does not remove it.

`docs/DEPLOY.md` covers the paid single-server setup that fixes all five.
