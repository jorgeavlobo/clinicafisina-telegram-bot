# Base image: secure & slim
FROM python:3.10-slim-bookworm

# Working directory inside container
WORKDIR /app

# Optional system packages (only if you need curl for self-pings)
# RUN apt-get update -qq && apt-get install -y -qq curl && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the full app after pip install to keep caching efficient
COPY . .

# Container listens on 8444 internally (matches docker-compose + main.py)
EXPOSE 8444

# Run your bot
CMD ["python", "app.py"]
