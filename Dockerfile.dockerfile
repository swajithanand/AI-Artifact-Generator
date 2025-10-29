# Dockerfile

# Use a clean, known stable Python image
FROM python:3.10.14-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED True

# Set the working directory
WORKDIR /app

# Copy dependencies and install
COPY requirements.txt .
# Use Gunicorn + Uvicorn workers for production stability
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . /app

# Cloud Run injects PORT, but we EXPOSE 8080 as the standard internal port
EXPOSE 8080

# The Cloud Run standard command: Gunicorn/Uvicorn binding to 0.0.0.0:$PORT
# Cloud Run automatically sets the PORT variable.
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8080"]