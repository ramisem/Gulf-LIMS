#!/bin/bash

source env/bin/activate
pip install -r requirements.txt
pip install django gunicorn
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic
