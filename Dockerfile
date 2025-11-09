FROM python:3.10-slim

WORKDIR /app

# Copy only server files
COPY requirements.txt .
COPY score_server.py .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Start command - use shell form to expand $PORT
CMD ["sh", "-c", "uvicorn score_server:app --host 0.0.0.0 --port ${PORT:-8000}"]
