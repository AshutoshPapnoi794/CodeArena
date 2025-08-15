#!/bin/bash

# Exit on error
set -o errexit

# Apply database migrations
flask db upgrade

# Start the Gunicorn server
gunicorn --bind 0.0.0.0:10000 app:app