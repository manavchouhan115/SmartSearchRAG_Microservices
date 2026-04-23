FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if required for some python tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# We override the CMD in docker-compose.yml for each specific microservice
CMD ["uvicorn", "services.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
