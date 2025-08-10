# Use PyTorch official image with CUDA support
FROM pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# # Install PyTorch with CUDA support (compatible with CUDA 12.x)
# RUN pip3 install --break-system-packages torch torchvision

# Copy application code
COPY . .

# Create cache directory for stanza models
RUN mkdir -p /app/cache

# Expose port
EXPOSE 7888
# Run the application
CMD ["python", "start.py"]
