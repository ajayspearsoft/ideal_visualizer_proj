# Stage 1: Build Frontend
FROM node:20 AS frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Final Image (Python)
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for OpenCV and other ML libs
# libgl1 is for OpenCV, libglib2 is for various libs, libxcb is what was missing
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

# Copy backend requirements and install
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy built frontend from Stage 1
# app.py expects 'dist' to be in the parent directory of 'backend'
COPY --from=frontend-builder /app/dist ./dist

# Copy backend code
COPY backend ./backend

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port (Railway uses PORT env var, but we'll default to 8080)
EXPOSE 8080

# Start command
# We run from /app so backend/app.py can find ../dist
CMD ["python", "backend/app.py"]
