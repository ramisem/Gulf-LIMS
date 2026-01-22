#!/bin/bash

echo "Do you want to modify the file /etc/redis/redis.conf to allow Redis to bind to all interfaces (be cautious with security implications)?"
echo "For modification: Find the line: 'bind 127.0.0.1 ::1' and change it to 'bind 0.0.0.0' ."
read -p "Enter yes/no: " confirm
if [ "$confirm" == "yes" ]; then
  sudo vim "/etc/redis/redis.conf"
  echo "File /etc/redis/redis.conf has been modified."
fi

postgresql_restart_required="false"

echo "Do you want to modify the file /etc/postgresql/15/main/postgresql.conf to update listen_addresses and timezone property?"
echo "For modification: find the line: 'listen_addresses' and change it to listen_addresses='*'."
echo "Also search for the properties 'log_timezone' and 'timezone' and change its values to 'UTC'."
read -p "Enter yes/no: " confirm
if [ "$confirm" == "yes" ]; then
  sudo vim "/etc/postgresql/15/main/postgresql.conf"
  echo "File /etc/postgresql/15/main/postgresql.conf has been modified."
  postgresql_restart_required="true"
fi

echo "Do you want to modify the file /etc/postgresql/15/main/pg_hba.conf  to update IPV4 & IPV6 host connections & methods?"
echo "For IPV4 change the ADDRESS to '0.0.0.0/0' and METHOD to 'md5'"
echo "For IPV6 change the ADDRESS to '::0/0' and METHOD to 'md5'"
read -p "Enter yes/no: " confirm
if [ "$confirm" == "yes" ]; then
  sudo vim "/etc/postgresql/15/main/pg_hba.conf"
  echo "File /etc/postgresql/15/main/pg_hba.conf  has been modified."
  postgresql_restart_required="true"
fi

if [ "$postgresql_restart_required" = "true" ]; then
  sudo systemctl restart postgresql
  netstat -tuln -p | grep 5432
fi

read -p "Do you want to create the database?(yes/no): " confirm
if [ "$confirm" == "yes" ]; then
  # Switch to the postgres user and execute the psql commands
  dbname=""
  while [ -z "$dbname" ]; do
      read -p "Provide the Database name: " dbname
  done
  sudo -i -u postgres bash <<EOF
psql << SQL
CREATE DATABASE $dbname
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'C.UTF-8'
    LC_CTYPE = 'C.UTF-8'
    LOCALE_PROVIDER = 'libc'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;
SQL

# Check if the database was created successfully
psql -c "\l" | grep $dbname && echo "Database $dbname created successfully" || echo "Failed to create database $dbname"
EOF
fi
