# ==========================================
# Stage 1: Build React Frontend with Vite
# ==========================================
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# Copy package files
COPY frontend/metube/package*.json ./

# Install dependencies
RUN npm install

# Copy frontend source code
COPY frontend/metube/ ./

# Build with Vite (creates dist/ folder)
RUN npm run build

# ==========================================
# Stage 2: Python Backend + Frontend
# ==========================================
FROM python:3.11-slim

# Install system dependencies including FFmpeg and tools for yt-dlp
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# IMPORTANT: Upgrade yt-dlp to latest version after requirements install
RUN pip install --no-cache-dir --upgrade yt-dlp

# Copy backend code
COPY backend/main.py .

# Copy Vite build output (dist/) from frontend-builder stage
COPY --from=frontend-builder /app/dist ./frontend/build

# Create downloads directory
RUN mkdir -p downloads

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/status || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
