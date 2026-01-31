FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY app/main.py .

# Run the application
CMD ["python", "main.py"]
