#!/bin/bash

# Directory Factory Droplet Setup Script
# Run as root on Ubuntu 22.04

set -e

echo "=== Directory Factory Droplet Setup ==="

# Update system
echo "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Install Docker Compose standalone
echo "Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Nginx and Certbot
echo "Installing Nginx and SSL tools..."
apt-get install -y nginx certbot python3-certbot-nginx

# Clone repo
echo "Cloning repository..."
cd /opt
git clone https://github.com/nigelmcintyre/directory_factory.git
cd directory_factory

# Create .env file
echo "Creating environment file..."
cat > .env << 'EOF'
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com
POSTGRES_DB=directory_factory
POSTGRES_USER=directory_user
POSTGRES_PASSWORD=your-postgres-password-here
POSTGRES_HOST=your-managed-db-host
POSTGRES_PORT=25060
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
EOF

echo "⚠️  IMPORTANT: Edit /opt/directory_factory/.env with your values:"
echo "   - DJANGO_SECRET_KEY: Generate with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
echo "   - DJANGO_ALLOWED_HOSTS: Your domain"
echo "   - POSTGRES_*: Your managed database credentials"
echo "   - GOOGLE_MAPS_API_KEY: Your API key"

# Create docker-compose.prod.yml for production
echo "Creating production docker-compose file..."
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  web:
    build: .
    command: sh -c "python manage.py migrate && gunicorn directory_factory.wsgi:application --bind 0.0.0.0:8000"
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: always
    volumes:
      - ./static:/app/static
EOF

# Update requirements.txt to include gunicorn
echo "Adding gunicorn to requirements..."
grep -q "gunicorn" requirements.txt || echo "gunicorn==21.2.0" >> requirements.txt

# Create Nginx config
echo "Setting up Nginx..."
cat > /etc/nginx/sites-available/directory_factory << 'EOF'
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/directory_factory/static/;
    }
}
EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/directory_factory /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# Create systemd service for Docker containers
echo "Creating systemd service..."
cat > /etc/systemd/system/directory-factory.service << 'EOF'
[Unit]
Description=Directory Factory Application
Requires=docker.service
After=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/directory_factory
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable directory-factory

echo ""
echo "=== Setup Complete ==="
echo ""
echo "NEXT STEPS:"
echo "1. Edit /opt/directory_factory/.env with your configuration"
echo "2. Edit /etc/nginx/sites-available/directory_factory and set your domain"
echo "3. Run: systemctl start directory-factory"
echo "4. Set up SSL: certbot --nginx -d your-domain.com"
echo "5. Check logs: docker-compose -f docker-compose.prod.yml logs -f"
echo ""
