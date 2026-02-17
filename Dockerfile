# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install PostgreSQL client libraries
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Make manage.py executable
RUN chmod +x manage.py

# Create staticfiles directory
RUN mkdir -p /app/staticfiles

EXPOSE 8000

# Run migrations, collect static files, and start server
CMD sh -c "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn directory_factory.wsgi:application --bind 0.0.0.0:8000"
