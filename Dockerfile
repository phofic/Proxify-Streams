FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY server.py index.html ./

# Expose port (Koyeb will use PORT env var, but we document 5555 as default)
EXPOSE 5555

# Run the application
CMD ["python", "server.py"]
