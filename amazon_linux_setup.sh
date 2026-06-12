#!/bin/bash

# Configuration and variables
PROJECT_DIR=$(pwd)
SOCK_FILE=$PROJECT_DIR/stockwise.sock
SERVICE_NAME="stockwise"

echo "======================================"
echo "Starting Stockwise Amazon Linux Setup..."
echo "Project Directory: $PROJECT_DIR"
echo "======================================"

# 1. Update system packages
echo "Updating system..."
sudo dnf update -y

# 2. Install dependencies (Python, Nginx)
# Note: Amazon Linux 2023 uses dnf. If using Amazon Linux 2, use yum.
echo "Installing Python 3, pip, compilation tools, and Nginx..."
sudo dnf install -y python3 python3-pip python3-devel gcc nginx

# 3. Create virtual environment
echo "Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 4. Install Python packages
echo "Installing application dependencies..."
pip install --upgrade pip
pip install wheel
pip install -r requirements.txt
# Gunicorn is required to serve Django applications
pip install gunicorn

# 5. Database migrations and static files
echo "Running migrations and collecting static files..."
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# 6. Configure permissions for Nginx
echo "Configuring permissions so Nginx can read the socket and static files..."
# Add nginx user to the current user's group (ec2-user)
sudo usermod -a -G $USER nginx
# Make the home directory executable by the group
chmod 710 /home/$USER

# 7. Configure Gunicorn systemd service
echo "Configuring Gunicorn daemon..."
cat <<EOF | sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null
[Unit]
Description=gunicorn daemon for stockwise
After=network.target

[Service]
User=$USER
Group=nginx
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:$SOCK_FILE config.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

# Start and enable Gunicorn service
sudo systemctl daemon-reload
sudo systemctl start ${SERVICE_NAME}
sudo systemctl enable ${SERVICE_NAME}

# 8. Configure Nginx
echo "Configuring Nginx reverse proxy..."

cat <<EOF | sudo tee /etc/nginx/conf.d/${SERVICE_NAME}.conf > /dev/null
server {
    listen 80;
    server_name _;

    # Ignore favicon logs
    location = /favicon.ico { access_log off; log_not_found off; }

    # Serve static files directly
    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
    }

    # Proxy all other requests to Gunicorn
    location / {
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_pass http://unix:$SOCK_FILE;
    }
}
EOF

# Restart Nginx and enable it to start on boot
sudo systemctl start nginx
sudo systemctl enable nginx

echo "======================================"
echo "Setup Complete!"
echo "Your app should now be running on port 80."
echo "Visit your EC2 instance's Public IP in a browser."
echo "======================================"
