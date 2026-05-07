FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for OpenCV and AI models
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    libx11-6 \
    gcc \
    pkg-config \
    zlib1g-dev \
    libjpeg-dev \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (Railway will provide PORT environment variable)
EXPOSE 8080

# Start command (Runs app.py directly from the backend folder)
CMD ["python", "app.py"]
