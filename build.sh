#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
python -m pip install -r requirements.txt

# Create static directory
mkdir -p staticfiles

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate
