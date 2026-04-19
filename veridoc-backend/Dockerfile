# Use Python 3.10 slim
FROM python:3.10-slim

# Install system dependencies
# We changed 'libgl1-mesa-glx' to 'libgl1' to fix the Debian Trixie error
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-tel \
    tesseract-ocr-hin \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend code
COPY . .

# Hugging Face Spaces port
EXPOSE 7860

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]