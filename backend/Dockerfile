FROM python:3.11-slim

# Install system dependencies including Tesseract OCR, OpenCV dependencies, libpq
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY backend /app/backend

# Create necessary directories
RUN mkdir -p /app/backend/uploads/screenshots \
    /app/backend/uploads/statements \
    /app/backend/uploads/receipts

ENV PYTHONPATH=/app
ENV TESSERACT_CMD=/usr/bin/tesseract

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
