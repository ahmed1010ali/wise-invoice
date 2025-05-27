# Use an official Python image
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Copy only requirements first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app
COPY . .

# Expose port (change this if your app runs on a different port)
EXPOSE 8000

# Default command to run the app
CMD ["python", "main.py"]
