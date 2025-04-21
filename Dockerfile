# Base image (stable & minimal)
FROM python:3.10-slim-bookworm

# Set working directory
WORKDIR /app

# Upgrade pip before anything else
RUN pip install --no-cache-dir --upgrade pip

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose webhook port (used inside container)
EXPOSE 8443

# Entrypoint
CMD ["python", "main.py"]
