#!/bin/bash

# Configuration and variables
PROJECT_DIR=$(pwd)
SOCK_FILE=$PROJECT_DIR/stockwise.sock
SERVICE_NAME="stockwise"

echo "======================================"
echo "Starting Stockwise EC2 Setup..."
echo "Project Directory: $PROJECT_DIR"
echo "======================================"

# 1. Update system packages
echo "Updating system..."
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install dependencies (Python, Nginx, venv)
echo "Installing Python 3, pip, venv, and Nginx..."
sudo apt-get install -y python3-pip python3-venv nginx

# 3. Create virtual environment
echo "Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 4. Install Python packages
echo "Installing application dependencies..."
pip install --upgrade pip
pip install wheel
pip install -r requirements.txt
# Gunicorn is required to serve Django applications on Unix systems
pip install gunicorn

# 5. Database migrations and static files
echo "Running migrations and collecting static files..."
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# 6. Configure Gunicorn systemd service
echo "Configuring Gunicorn daemon..."
cat <<EOF | sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null
[Unit]
Description=gunicorn daemon for stockwise
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:$SOCK_FILE config.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

# Start and enable Gunicorn service
sudo systemctl daemon-reload
sudo systemctl start ${SERVICE_NAME}
sudo systemctl enable ${SERVICE_NAME}

# 7. Configure Nginx
echo "Configuring Nginx reverse proxy..."
cat <<EOF | sudo tee /etc/nginx/sites-available/${SERVICE_NAME} > /dev/null
server {
    listen 80;
    server_name _;

    # Ignore favicon logs
    location = /favicon.ico { access_log off; log_not_found off; }

    # Serve static files directly
    location /static/ {
        root $PROJECT_DIR;
    }

    # Proxy all other requests to Gunicorn
    location / {
        include proxy_params;
        proxy_pass http://unix:$SOCK_FILE;
    }
}
EOF

# Enable Nginx site and disable default
sudo ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Restart Nginx
sudo systemctl restart nginx

# 8. Configure Firewall (allow Nginx HTTP)
echo "Configuring UFW Firewall..."
sudo ufw allow 'Nginx Full'

echo "======================================"
echo "Setup Complete!"
echo "Your app should now be running on port 80."
echo "Visit your EC2 instance's Public IP in a browser."
echo "======================================"
