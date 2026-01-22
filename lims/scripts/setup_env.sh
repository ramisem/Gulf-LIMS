#!/bin/bash

setup_application_name="gulf-coast-pathologists"
setup_application_folder_name="lims-application"
setup_application_path="/home/$USER/${setup_application_name}"
ZIP_APPLICATION_FILE="application.zip"

# Prompt for user input
# shellcheck disable=SC2162
read -p "Enter the Python version to install (e.g., 3.8): " PYTHON_VERSION

# shellcheck disable=SC2162
read -p "Do you want to install python${PYTHON_VERSION} and create the virtual environment? (yes/no): " confirm
if [ "$confirm" == "yes" ]; then
  # Add the dead-snakes PPA for Python
  sudo add-apt-repository ppa:deadsnakes/ppa

  # Install Python, its development files, virtual environment package, and nginx
  sudo apt install -y python"${PYTHON_VERSION}" python"${PYTHON_VERSION}"-dev python"${PYTHON_VERSION}"-venv nginx

  # Download and use version-specific get-pip.py if Python < 3.9
  if (( $(echo "${PYTHON_VERSION} < 3.9" | bc -l) )); then
    curl https://bootstrap.pypa.io/pip/"${PYTHON_VERSION}"/get-pip.py -o get-pip.py
  else
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
  fi

  # Install pip for the specified Python version
  sudo python"${PYTHON_VERSION}" get-pip.py

  # Install virtualenv using pip
  python"${PYTHON_VERSION}" -m pip install virtualenv

  sudo apt install net-tools

  python"${PYTHON_VERSION}" -m virtualenv "${setup_application_path}"/${setup_application_folder_name}/env

  sudo apt-get install redis-server -y
fi

# shellcheck disable=SC2162
read -p "Do you want to install the latest version of the application? (yes/no): " confirm
if [ "$confirm" == "yes" ]; then
  if [ ! -d "${setup_application_path}/${setup_application_folder_name}/application/" ]; then
    # Create the directory
    mkdir -p "${setup_application_path}/${setup_application_folder_name}/application/"
  fi
  unzip "$PWD"/$ZIP_APPLICATION_FILE -d "${setup_application_path}"/${setup_application_folder_name}/application/
  cp "$PWD"/requirements.txt "${setup_application_path}"/${setup_application_folder_name}/
fi

# shellcheck disable=SC2162
read -p "Do you want to install required Python Packages? (yes/no): " confirm
if [ "$confirm" == "yes" ]; then
  # shellcheck disable=SC1090
  source "${setup_application_path}"/${setup_application_folder_name}/env/bin/activate
  pip install -r "${setup_application_path}"/${setup_application_folder_name}/requirements.txt
  pip install django gunicorn
  pip install daphne==4.1.2
fi

# shellcheck disable=SC2162
read -p "Do you want to install 'PostgreSQL? (yes/no): " confirm
if [ "$confirm" == "yes" ]; then
  sudo sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
  wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
  sudo apt-get update
  sudo apt-get -y install postgresql-15
  sudo service postgresql status
fi

# shellcheck disable=SC2162
read -p "Do you want to update the password for 'postgres' user? (yes/no): " confirm
if [ "$confirm" == "yes" ]; then
  # shellcheck disable=SC2162
  read -sp "Enter the new password for the postgres user: " NEW_PASSWORD
  echo
  # Switch to the postgres user and execute the psql commands
  sudo -i -u postgres bash <<EOF
psql -c "ALTER USER postgres WITH PASSWORD '$NEW_PASSWORD';"
psql -c "\\du"
EOF
fi

# ---------------------------
# Java installation block
# ---------------------------
# shellcheck disable=SC2162
read -p "Do you want to install Java? (yes/no): " confirm
if [ "$confirm" == "yes" ]; then
  sudo apt update
  sudo apt install -y openjdk-17-jdk

  # Set JAVA_HOME and update PATH if not already present in ~/.bashrc
  # NOTE: JAVA_HOME should be the JVM directory (not the java binary)
  if ! grep -q 'export JAVA_HOME=' ~/.bashrc; then
    echo 'export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"' >> ~/.bashrc
    echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
    # Apply changes for current shell session
    # shellcheck disable=SC1090
    source ~/.bashrc
  else
    echo "JAVA_HOME already exists in ~/.bashrc - skipping append."
  fi
fi

# ------------------------------------------------------
# Microsoft TrueType core fonts (for Jasper Reports)
# ------------------------------------------------------
# shellcheck disable=SC2162
read -p "Do you want to install Microsoft TrueType core fonts package (required for Jasper Report)? (yes/no):" confirm
if [ "$confirm" == "yes" ]; then
  sudo apt update
  sudo apt install -y ttf-mscorefonts-installer
  sudo fc-cache -fv
fi
