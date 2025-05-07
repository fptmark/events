FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY ./app ./app
COPY config.json .

ENV PYTHONPATH=/app

# Default command to run the app (FastAPI/Uvicorn assumed)
CMD ["python", "app/main.py", "es", "./config.json"]
