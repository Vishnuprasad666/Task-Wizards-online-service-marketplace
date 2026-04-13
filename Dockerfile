# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project code into the container
COPY . /app/

# Create a directory for static files and set permissions
RUN mkdir -p /app/staticfiles assets
RUN chmod +x /app/build.sh

# The build process cannot run migrations because secrets aren't available yet.
# So we run collectstatic here and migrations in the start command.
RUN python manage.py collectstatic --no-input

# Expose the port Hugging Face expects
EXPOSE 7860

# Command to run migrations and then start the server
CMD python manage.py migrate && gunicorn --bind 0.0.0.0:7860 Task_Wizards.wsgi:application
