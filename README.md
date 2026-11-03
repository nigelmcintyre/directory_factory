# Sauna Guide (saunaguide.ie)

A directory of saunas in Ireland, built with Django on the Directory Factory codebase: listings with JSONB attributes, configuration-driven filters and county landing pages.

The roadmap and progress are in [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md).

## Stack and hosting

| Part | What | Notes |
|---|---|---|
| App | Django 5.2, Python 3.11, HTMX, Leaflet, Tailwind (prebuilt CSS) | Filters and infinite scroll are server-rendered HTMX partials |
| Hosting | Vercel project `saunaguide` (team `simple-site-solutions`, region `lhr1`) | Every push to `main` deploys to production. `vercel.json` must keep `"framework": "django"`. |
| Database | Neon Postgres project `saunaguide` (`little-leaf-76133932`, London), database `directory_factory` | The app connects with the pooled `DATABASE_URL` |
| CI | GitHub Actions (`.github/workflows/ci-cd.yml`) | Runs `manage.py check` and the test suite against Postgres on every push and PR |
| Analytics | GA4 property `531569261` (stream `G-M02JT3547M`), plus first-party listing stats in Postgres | See [Listing analytics](#listing-analytics-owner-reports) |

`setup-droplet.sh`, `docker-compose.prod.yml` and the Nginx setup belong to the old DigitalOcean deployment and are no longer used.

## Deploying

1. **Apply any new migrations to Neon first. Vercel does not run migrations.** Code that depends on a missing table will return 500 errors. Do one of the following:
   - Run `DATABASE_URL='<Neon connection string>' python manage.py migrate` locally. The connection string is in Neon console → Connect. It can't be pulled from Vercel because it's stored as a secret.
   - Run the migration's SQL in the Neon SQL editor, then record the migration with `INSERT INTO django_migrations (app, name, applied) VALUES ('directory', '<migration name>', now());`.
2. Push to `main`. Vercel builds and deploys in about a minute.
3. Environment variable changes only take effect on the next deploy. To apply them without a code change, redeploy the latest production deployment from the Vercel dashboard or run `vercel redeploy <deployment-url> --target production`.

## Local development

**With Docker** (Postgres plus the dev server, with `DJANGO_DEBUG=true` already set):
```bash
docker-compose up --build
```
Then open http://127.0.0.1:8000/.

**Without Docker:**
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_DEBUG=true POSTGRES_HOST=localhost   # plus POSTGRES_DB/USER/PASSWORD if not the defaults
python manage.py migrate
python manage.py runserver
```

`DJANGO_DEBUG` defaults to `false`. With debug off, the app refuses to start unless `DJANGO_SECRET_KEY` is set, so always set `DJANGO_DEBUG=true` locally.

**CSS:** after changing templates, run `npm install` once, then `npm run build:css`, or `npm run watch:css` while editing. The output, `static/css/tailwind.css`, is committed.

## Testing

```bash
python manage.py test
```

The tests need a Postgres database. Start one with `docker-compose up db`, or rely on CI.

## Environment variables

Production values live in Vercel (`vercel env ls production`). The ✓ column shows what was set in production as of 2026-11-03.

| Variable | Prod | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | ✓ | Required unless `DJANGO_DEBUG=true` |
| `DJANGO_DEBUG` | ✓ | `true` only for local development. Defaults to `false`. |
| `DJANGO_ALLOWED_HOSTS` | ✓ | Comma-separated. Defaults to `localhost,127.0.0.1`. |
| `CSRF_TRUSTED_ORIGINS` | ✓ | For example `https://saunaguide.ie,https://www.saunaguide.ie` |
| `DATABASE_URL` | ✓ | Neon pooled connection string. When it's set, the `POSTGRES_*` variables are ignored. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` | | Local and Docker database only |
| `GOOGLE_TAG_ID` | ✓ | GA4 measurement ID `G-M02JT3547M`. If it's missing, GA4 stops recording; this happened after the move to Vercel. |
| `GOOGLE_ADS_ID` | | Google Ads tag. Defaults to `AW-17961593385`. |
| `GOOGLE_ADSENSE_CLIENT` | ✓ | AdSense publisher ID |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | ✓ | Lead alerts by Telegram |
| `EMAIL_BACKEND`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | ✓ | Lead alerts by email through Google Workspace SMTP. The password is a Workspace app password, which needs 2-Step Verification. |
| `ADMIN_EMAIL`, `DEFAULT_FROM_EMAIL` | | Both default to `nigel@simplesitesolutions.ie` |
| `STRIPE_ENABLED`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | ✗ | Not set yet. The webhook returns 503 until they are. |
| `FEATURED_GRACE_DAYS` | | Days a listing stays featured after a failed payment. Default 7. |
| `ENABLE_GOOGLE_PLACES_SYNC` | ✓ | Safety switch for the old Google Places commands. Keep it `false`. |
| `MAP_PROVIDER`, `MAP_TILES_URL`, `MAP_DEFAULT_*` | | Optional map settings |

## Features

### Listings and county pages
- `Listing` (`directory/models.py`) stores amenities and opening hours in the `attributes` JSON field. Copied Google reviews are in `structured_data`.
- Filters are defined in `directory/niche_config.py`. Attribute values are lowercase: `yes`, `no`, `not listed`, `wood`, `electric`, `infrared`.
- County pages are served at `/<county-slug>/`. Featured listings sort first everywhere.

### Lead capture: `/submit/` and `/get-featured/`
- **Sauna submissions** are saved as `SaunaSubmission`. **Partner (get-featured) enquiries** are saved as `PartnerInquiry`, with a pipeline status of new, contacted, won or lost.
- Both are saved before any alert goes out. Alerts go to Telegram and by email to `ADMIN_EMAIL`, with Reply-To set to the person who submitted. A failed alert never loses a lead; it's only logged.
- Both forms have a hidden `fax` field as a spam trap. Submissions that fill it are thrown away silently.
- In admin, select submissions and run **"Approve and create listings"** to create the `Listing`, with a unique slug and the amenities filled in. Opening hours have to be entered by hand because the formats differ.

### Listing analytics (owner reports)
These are the numbers behind the free trial and the monthly reports to featured owners.

- **Markup:** every listing card (`data-placement="card"`) and listing page (`data-placement="detail"`) carries `data-listing-id` and `data-listing-name`. Each outbound link has a `data-click-type`: `website`, `booking`, `social`, `phone`, `directions` or `review`. The type for website and booking links is worked out from the URL by `directory/links.py`.
- **UTM tags:** website and booking links get `utm_source=saunaguide.ie&utm_medium=referral&utm_campaign=listing`, so owners see the traffic in their own analytics. Social links are left alone.
- **First-party counts:** a small script in `base.html` sends batched beacons to `POST /t/`. They're stored as daily totals per listing in `ListingDailyStat` (listing, date, metric, count). The metrics are:
  - `view`: the listing page was opened
  - `impression`: the card was at least 50% visible, counted once per page load
  - `click_<type>`: an outbound link was clicked.

  Bots are ignored, and no IPs or cookies are stored. The stats are browsable read-only in admin.
- **GA4:** the same script sends `listing_click` and `listing_view` events. Their parameters are registered as custom dimensions (`listing_id`, `listing_name`, `click_type`, `placement`), and `listing_click` is a key event.
- **Monthly report:** this prints a CSV of views, impressions and each click type per listing, sorted by total clicks.
  ```bash
  python manage.py listing_report --month 2026-11 [--listing <slug>]
  ```
  Run it with `DATABASE_URL` set to Neon to report on production.

### Managing GA4 from the command line
GA4 is managed through a service account, so the GA4 interface isn't needed after setup:
- service account: `ga-manager@saunaguide-analytics-1103.iam.gserviceaccount.com` (Google Cloud project `saunaguide-analytics-1103`)
- access: Editor on the GA4 property; `nigelmcintyre1995@gmail.com` is allowed to act as it.

```bash
TOKEN=$(gcloud auth print-access-token \
  --impersonate-service-account=ga-manager@saunaguide-analytics-1103.iam.gserviceaccount.com \
  --scopes=https://www.googleapis.com/auth/analytics.edit,https://www.googleapis.com/auth/analytics.readonly)
curl -H "Authorization: Bearer $TOKEN" -H "x-goog-user-project: saunaguide-analytics-1103" \
  https://analyticsadmin.googleapis.com/v1beta/properties/531569261/customDimensions
```

Use the Admin API (`analyticsadmin.googleapis.com`) for configuration and the Data API (`analyticsdata.googleapis.com`) for reports. Don't use `gcloud auth application-default login`: Google blocks its default client from the Analytics scopes.

### Featured listings (Stripe)
Featured listings are billed as Stripe subscriptions, and webhooks keep `listing.is_featured` in sync. Onboarding is currently manual. Self-serve checkout with Payment Links and a claim-your-listing flow is next on the roadmap (item 3).

1. Create the customer and subscription in the Stripe Dashboard.
2. In admin, open the listing and add a `Featured Listing Subscription` inline with the `stripe_subscription_id`.
3. With `STRIPE_ENABLED=true` and the webhook set up, status changes are applied to `listing.is_featured` automatically.

**Webhook endpoint:** `POST /billing/stripe/webhook/`

**Stripe events to subscribe to:** `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`

**Behaviour:**
- `active` or `trialing` sets `is_featured = True`.
- `invoice.payment_failed` starts a grace period of `FEATURED_GRACE_DAYS`, during which the listing stays featured.
- `invoice.paid` clears the grace period.
- `canceled` or `unpaid` after the grace period sets `is_featured = False`.
- Duplicate webhook deliveries are ignored using the `StripeWebhookEvent` table.
- Setting `auto_manage_featured = False` on a subscription lets you set the flag by hand.

## Data quality audit

This produces a read-only report of listings missing a website of their own, a phone number, a photo or opening hours:
```bash
psql "$DATABASE_URL" --csv -f scripts/listing_data_quality.sql > listing_data_quality.csv
python3 scripts/add_ga_columns.py listing_data_quality.csv analytics_data > listing_data_quality_ga.csv
```

`website_type` classifies each listing's link as `own_site`, `none`, `social`, `link_hub`, `booking_platform`, `google` or `dev_url`. The second command adds GA4 page views and outbound clicks from exported GA4 CSVs.

## Management commands

| Command | Status | Purpose |
|---|---|---|
| `listing_report` | Active | Monthly per-listing stats CSV (see above) |
| `import_listings <csv>` | Active | Import listings from CSV |
| `import_google_places <csv>` | Active | Import a Google Places CSV export |
| `geocode_listings_osm` | Active | Fill latitude and longitude from addresses using OpenStreetMap Nominatim |
| `generate_pages` | Active | Show which county pages have enough listings |
| `add_sauna`, `verify_listings`, `refresh_photo_refs`, `download_photos`, `fetch_google_reviews`, `geocode_place_ids` | Disabled | Old Google Places API commands, now stubs. Their `.sh` wrappers no longer do anything. |

## Project structure
- `directory/models.py`: `Listing`, `ListingDailyStat`, `SaunaSubmission`, `PartnerInquiry`, `FeaturedListingSubscription`, `StripeWebhookEvent`
- `directory/views.py`: home, county pages, listing page, submit, get-featured, the `/t/` beacon and the Stripe webhook
- `directory/links.py`: outbound link classification and UTM tagging, exposed to templates through `templatetags/listing_links.py`
- `directory/utils.py`: JSONB filtering and pagination
- `directory/schema.py`: structured data (JSON-LD) builders
- `directory/niche_config.py`: site name, domain and filter definitions
- `directory/templates/`: Tailwind and HTMX templates. The analytics script lives in `base.html`.
- `directory/tests/`: Django tests
- `blog/`: markdown blog posts
- `scripts/`: read-only data audit tools
