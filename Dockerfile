# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt



# Copy application code
COPY . .

# Create cache directory
RUN mkdir -p /app/cache

# Expose port
EXPOSE 7888
# Run the application
CMD ["python", "start.py"]
