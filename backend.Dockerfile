# backend.Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed by some Python packages
RUN apt-get update && apt-get install -y build-essential

# Install poetry
RUN pip install poetry

# Copy only the files needed for dependency installation to leverage Docker layer caching
COPY poetry.lock pyproject.toml /app/

# Configure Poetry and install dependencies
# We don't create a virtual env inside Docker and install only production dependencies
# RUN poetry config virtualenvs.create false && poetry install --without-dev --no-root
RUN poetry config virtualenvs.create false && poetry install --only main --no-root

# Copy the rest of the application source code into the container
COPY ./app /app/app
COPY ./data_ingestion /app/data_ingestion
COPY ./.env /app/.env

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]