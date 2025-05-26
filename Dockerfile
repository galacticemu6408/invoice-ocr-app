# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && \
    apt-get install -y poppler-utils tesseract-ocr && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . /app/

# Expose port
EXPOSE 10000

# Run the application
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]

