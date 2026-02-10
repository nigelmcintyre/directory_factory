# Directory Factory

Foundational Django 5 codebase for configuration-driven niche directory sites using PostgreSQL JSONB.

## What’s included
- Universal `Listing` model with `attributes` and `structured_data` JSON fields
- Configuration-driven filters in `niche_config.py`
- HTMX-based filtering with server-rendered partials
- pSEO landing routes at `/<city>/<category>/`

## Quick start with Docker (Recommended)

1. Start the application with Docker Compose:
   ```bash
   docker-compose up --build
   ```

2. Visit http://127.0.0.1:8000/ to view the site.

That's it! PostgreSQL and Django are running in containers.

To stop: `docker-compose down`

To stop and remove data: `docker-compose down -v`

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

## Project structure
- `directory/models.py` - Universal Listing model with JSONField
- `directory/niche_config.py` - Site configuration and filter definitions
- `directory/utils.py` - Dynamic JSONB filtering logic
- `directory/views.py` - Home and pSEO landing views
- `directory/templates/` - Tailwind-styled templates with HTMX
