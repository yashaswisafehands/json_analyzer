FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy local files into container
COPY . /app

# Optional: install pip packages if needed
# RUN pip install -r requirements.txt

# Create input/output dirs (in case they don't exist)
RUN mkdir -p input output output1

# Run the main.py script
CMD ["python", "main.py"]
