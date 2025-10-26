# Dockerfile

# Use a clean, known Python image (3.11 is a good, stable version)
FROM python:3.11.8-bullseye
#FROM python:3.10-slim
#FROM python:3.10 
# Set environment variables
ENV PYTHONUNBUFFERED=1
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8
#ENV PYTHONUNBUFFERED True
#FROM python:3.10.14-slim 
# Set the working directory inside the container
WORKDIR /app
# Install system dependencies that might be needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install dependencies
# This layer is cached and run first
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port that Uvicorn will listen on (default for Cloud Run/Railway)
#EXPOSE 8080

# Command to run the application using the $PORT environment variable
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
#CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
#CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
#CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8080"]