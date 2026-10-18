FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Set proxy environment defaults
ENV PROXY_HOST=0.0.0.0
ENV PROXY_PORT=8080
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["python", "main.py"]
