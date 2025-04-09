# Use the official Python image as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the application files to the container
COPY . /app

# Create an uploads directory
RUN mkdir -p /app/uploads

# Install the required Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the FLASK_APP environment variable to point to the app module
ENV FLASK_APP=/app/app.py

# Expose the port for the web application
EXPOSE 80

# Command to run the Flask application
CMD ["flask", "run", "--host=0.0.0.0", "--port=80", "--reload"]
