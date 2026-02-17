# Directory Factory

Foundational Django 5 codebase for configuration-driven niche directory sites using PostgreSQL JSONB.

## What’s included
- Universal `Listing` model with `attributes` and `structured_data` JSON fields
- Configuration-driven filters in `niche_config.py`
- HTMX-based filtering with server-rendered partials
- pSEO landing routes at `/<county>/`

## Quick start with Docker (Recommended)

1. Start the application with Docker Compose:
   ```bash
   docker-compose up --build
   ```

2. Visit http://127.0.0.1:8000/ to view the site.

That's it! PostgreSQL and Django are running in containers.

To stop: `docker-compose down`

To stop and remove data: `docker-compose down -v`

## CSS Development

This project uses Tailwind CSS compiled locally for optimal performance.

**Initial setup:**
```bash
npm install
```

**Build CSS for production:**
```bash
npm run build:css
```

**Watch mode for development (auto-rebuild on changes):**
```bash
npm run watch:css
```

The compiled CSS is located at `static/css/tailwind.css` and is already built and ready to use.

## Production deployment notes

### Static files
- `STATICFILES_DIRS` points to the source assets in `static/` for local development.
- `collectstatic` copies all static assets into `staticfiles/` for production serving.

**Run during deploy:**
```bash
python manage.py collectstatic --noinput
```

**Serve in production (current setup: Nginx + Docker Compose):**
- Nginx should serve `/static/` directly from `staticfiles/`.
- Nginx should proxy requests to the app at `http://127.0.0.1:8000`.

Example Nginx location blocks:
```nginx
location /static/ {
   alias /opt/directory_factory/staticfiles/;
   expires 30d;
   add_header Cache-Control "public, max-age=2592000";
}

location / {
   proxy_pass http://127.0.0.1:8000;
   proxy_set_header Host $host;
   proxy_set_header X-Real-IP $remote_addr;
   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Environment variables
Set these before running the app:
- `DJANGO_SETTINGS_MODULE=directory_factory.settings`
- `DJANGO_SECRET_KEY` (required in production)
- `DJANGO_DEBUG=0`
- `ALLOWED_HOSTS` (comma-separated)
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- `GOOGLE_MAPS_API_KEY` (optional if you use Google Maps)
- `MAP_PROVIDER` (optional: `leaflet` or `google`)

### Database
Apply migrations on deploy:
```bash
python manage.py migrate
```

### Assets build
Build the Tailwind CSS before deploy:
```bash
npm install
npm run build:css
```

### Running with Docker
For production runs on the server:
```bash
cd /opt/directory_factory
docker compose -f docker-compose.prod.yml up --build -d
```

## Manual setup (without Docker)
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your PostgreSQL connection via environment variables:
   ```bash
   export POSTGRES_DB=directory_factory
   export POSTGRES_USER=postgres
   export POSTGRES_PASSWORD=postgres
   export POSTGRES_HOST=localhost
   export POSTGRES_PORT=5432
   ```

4. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. Start the development server:
   ```bash
   python manage.py runserver
   ```

6. Visit http://127.0.0.1:8000/ to view the site.

## Testing
Run the Django test suite:
```bash
python manage.py test
```

## Project structure
- `directory/models.py` - Universal Listing model with JSONField, SaunaSubmission model for user submissions
- `directory/niche_config.py` - Site configuration and filter definitions
- `directory/utils.py` - Dynamic JSONB filtering logic
- `directory/views.py` - Home, pSEO landing, and submission views
- `directory/forms.py` - User submission form for crowdsourcing missing listings
- `directory/tests/` - Django test modules
- `directory/templates/` - Tailwind-styled templates with HTMX
- `directory/management/commands/` - CLI tools for data maintenance

## Features

### User Submission System
Allow users to submit missing saunas via a web form at `/submit/`:
- Public submission form with all sauna fields (location, amenities, contact info)
- Status workflow: pending → approved/rejected
- Admin interface with bulk approve/reject actions
- Email notifications are not enabled by default

**Admin workflow:**
1. Users submit saunas at `/submit/`
2. Review submissions at `/admin/directory/saunasubmission/`
3. Approve or reject with bulk actions
4. Approved submissions become regular listings

### Management Commands

#### Add Individual Saunas
Add saunas from Google Maps using the `add_sauna` command:

```bash
# Using Docker
docker-compose exec web python manage.py add_sauna --search "Sauna name"
docker-compose exec web python manage.py add_sauna --url "https://maps.google.com/..."
docker-compose exec web python manage.py add_sauna --place-id "ChIJ..."

# Using bash wrapper (easier)
./add_sauna.sh --search "Sauna name"
./add_sauna.sh --url "https://maps.google.com/..."
```

Features:
- Fetches details from Google Maps Places API
- Extracts amenities from reviews (wood/electric heat, cold plunge, etc.)
- Gets opening hours, phone, website, ratings
- Automatically formats data for database

#### Verify Data Quality
Check and fix listing data using the `verify_listings` command:

```bash
# Check all listings (dry run)
docker-compose exec web python manage.py verify_listings

# Auto-fix errors
docker-compose exec web python manage.py verify_listings --fix

# Only verify counties
docker-compose exec web python manage.py verify_listings --county-only --fix

# Limit number of listings
docker-compose exec web python manage.py verify_listings --limit 50

# Using bash wrapper
./verify_listings.sh --fix
./verify_listings.sh --county-only --fix
```

Verifies:
- County names against Google Maps API
- City names (optional)
- Phone number formatting
- Website URLs

### Google Maps API Integration
Requires a Google Maps API key with Places API enabled:

1. Get API key from [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Places API (New) and Places API
3. Add to `.env` file:
   ```bash
   GOOGLE_MAPS_API_KEY=your_api_key_here
   ```

Used by:
- `add_sauna` command - fetch place details
- `verify_listings` command - verify location data
- Review analysis - extract amenities from user reviews

## Data Import

Import listings from CSV:
```bash
docker-compose exec web python manage.py import_listings sample_data/sauna_listings_final.csv
```

CSV format (17 columns):
- name, place_id, city, county, address
- website, phone, rating, reviews
- photo_ref, heat_source, cold_plunge, dog_friendly
- showers, changing_facilities, sea_view, opening_hours

**Note:** All attribute values should be lowercase: `yes`, `no`, `not listed`, `wood`, `electric`, `infrared`

## Configuration

### Environment Variables
Required:
- `POSTGRES_DB` - Database name
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password
- `POSTGRES_HOST` - Database host (localhost or db for Docker)
- `POSTGRES_PORT` - Database port (default: 5432)
- `GOOGLE_MAPS_API_KEY` - For Places API features

Optional:
- `DJANGO_DEBUG` - Debug mode (default: true)
- `DJANGO_SECRET_KEY` - Secret key for production

### Filter Configuration
Edit `directory/niche_config.py` to customize:
- Site metadata (name, tagline, description)
- Filter options and labels
- Attribute choices (must match data format)

**Important:** Use lowercase values: `"yes"`, `"no"`, `"not listed"`

## Production Deployment

See [setup-droplet.sh](setup-droplet.sh) for automated deployment script.

Manual steps:
1. Clone repository on server
2. Configure environment variables in `.env`
3. Run migrations: `docker-compose -f docker-compose.prod.yml run web python manage.py migrate`
4. Import data: `docker-compose -f docker-compose.prod.yml exec web python manage.py import_listings sample_data/sauna_listings_final.csv`
5. Start services: `docker-compose -f docker-compose.prod.yml up -d`

## Development Workflow

### Adding New Saunas
1. Use `add_sauna.sh` script for individual additions
2. Or accept user submissions via `/submit/` form
3. Verify data quality with `verify_listings.sh --fix`

### Maintaining Data Quality
Run periodic checks:
```bash
# Weekly: verify county data
./verify_listings.sh --county-only --fix

# Monthly: full verification
./verify_listings.sh --fix
```

### Updating Listings
1. Edit in Django admin at `/admin/directory/listing/`
2. Or update CSV and re-import
3. Run verification to ensure consistency
