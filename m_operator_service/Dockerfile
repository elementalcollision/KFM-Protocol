# Use an official Python runtime as a parent image
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /code

# Install system dependencies if any (e.g., database drivers)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Copy only the requirements file first to leverage Docker cache
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /code/requirements.txt

# Copy project code
# Copy the entire service directory
COPY . /code/m_operator_service

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using uvicorn
# Use 0.0.0.0 to make it accessible outside the container
CMD ["uvicorn", "m_operator_service.app.main:app", "--host", "0.0.0.0", "--port", "8000"] 