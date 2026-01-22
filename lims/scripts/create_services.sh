#!/bin/bash

application_name="gulf-coast-pathologists"
application_folder_name="lims-application"
application_path="/home/$USER/${application_name}"
PROJECT_DIR="${application_path}/${application_folder_name}"
GUNICORN_SOCK="/run/gunicorn.sock"
APP_ID="controllerapp"
GUNICORN_APP="$APP_ID.wsgi:application"
DAPHNE_APP="$APP_ID.asgi:application"
DAPHNE_PORT="8001"

# Function to create and configure gunicorn.socket
setup_gunicorn_socket() {
  cat <<EOL | sudo tee /etc/systemd/system/gunicorn.socket
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=$GUNICORN_SOCK

[Install]
WantedBy=sockets.target
EOL
}

# Function to create and configure gunicorn.service
setup_gunicorn_service() {
  cat <<EOL | sudo tee /etc/systemd/system/gunicorn.service
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$PROJECT_DIR/application
ExecStart=$PROJECT_DIR/env/bin/gunicorn \\
          --access-logfile - \\
          --workers 3 \\
          --bind unix:$GUNICORN_SOCK \\
          $GUNICORN_APP

[Install]
WantedBy=multi-user.target
EOL
}

# Function to setup daphne
setup_daphne_service() {
  cat <<EOL | sudo tee /etc/systemd/system/daphne.service
[Unit]
Description=Daphne Server
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$PROJECT_DIR/application
ExecStart=$PROJECT_DIR/env/bin/daphne -b 0.0.0.0 -p $DAPHNE_PORT $DAPHNE_APP
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOL
}

# Function to setup nginx site configuration
setup_nginx() {
  # Print a warning and ask for confirmation
  echo "Warning: This will delete all files in /etc/nginx/sites-enabled/"
  # shellcheck disable=SC2162
  read -p "Are you sure you want to continue? (yes/no): " confirm

  if [ "$confirm" == "yes" ]; then
    # Remove all files in /etc/nginx/sites-enabled/
    sudo rm -r /etc/nginx/sites-enabled/*
    echo "All files in /etc/nginx/sites-enabled/ have been removed."

    # Create the Nginx configuration file for the blog
    sudo tee /etc/nginx/sites-available/$application_name <<EOL
server {
    listen 80 default_server;
    server_name _;
    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root $PROJECT_DIR/application;
    }
    location / {
        include proxy_params;
        proxy_pass http://unix:$GUNICORN_SOCK;
    }
}
EOL

    # Create a symbolic link to enable the blog site
    sudo ln -s /etc/nginx/sites-available/$application_name /etc/nginx/sites-enabled/
    echo "Nginx site configuration for the blog has been created and enabled."

    # Add the user to the www-data group
    sudo gpasswd -a www-data "$USER"
    echo "User $USER has been added to the www-data group."
  else
    echo "Operation cancelled."
    exit 1
  fi
}

execute_python_services() {
  #Project migration and static files handling
  # shellcheck disable=SC1090
  source "${application_path}"/${application_folder_name}/env/bin/activate
  python "${application_path}"/${application_folder_name}/application/manage.py makemigrations
  python "${application_path}"/${application_folder_name}/application/manage.py migrate
  python "${application_path}"/${application_folder_name}/application/manage.py collectstatic

  # shellcheck disable=SC2162
  read -p "Do you want to create superuser? (yes/no): " confirm
  if [ "$confirm" == "yes" ]; then
    python "${application_path}"/${application_folder_name}/application/manage.py createsuperuser
  fi
  deactivate
}

configure_celery() {
  sudo apt install -y supervisor

  if [ ! -d "/var/log/celery/" ]; then
    # Create the directory
    sudo mkdir -p "/var/log/celery/"
  fi

  cat <<EOL | sudo tee /etc/supervisor/conf.d/celery_worker.conf
[program:celery_worker]
command=${application_path}/${application_folder_name}/env/bin/celery -A ${APP_ID} worker --loglevel=info -E
directory=${application_path}/${application_folder_name}/application
user=$USER
autostart=true
autorestart=true
stopasgroup=true
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker_error.log
EOL

  cat <<EOL | sudo tee /etc/supervisor/conf.d/celery_beat.conf
[program:celery_beat]
command=${application_path}/${application_folder_name}/env/bin/celery -A ${APP_ID} beat --loglevel=info
directory=${application_path}/${application_folder_name}/application
user=$USER
autostart=true
autorestart=true
stopasgroup=true
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat_error.log
EOL

  sudo supervisorctl reread
  sudo supervisorctl update

}

# Function to restart services
restart_services() {
  sudo systemctl start gunicorn.socket
  sudo systemctl enable gunicorn.socket
  sudo systemctl enable daphne
  sudo systemctl restart daphne
  sudo systemctl status daphne
  sudo systemctl restart redis-server
  sudo systemctl enable redis-server
  sudo systemctl status redis-server
  sudo systemctl restart nginx
  sudo service gunicorn restart
  sudo service nginx restart
  sudo supervisorctl restart celery_worker
  sudo supervisorctl restart celery_beat
  sudo supervisorctl status
  sudo systemctl status nginx
  echo "All the required services have been restarted."
}

# Run all setup functions
setup_gunicorn_socket
setup_gunicorn_service
setup_daphne_service
setup_nginx
execute_python_services
configure_celery
restart_services
