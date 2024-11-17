# Use the official Python slim image
FROM python:3.9-slim

# Install system dependencies and ODBC Driver 17
RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    gnupg2 \
    unixodbc \
    unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17

# Set environment variables for the ODBC driver
ENV ACCEPT_EULA=Y
ENV LD_LIBRARY_PATH=/opt/microsoft/msodbcsql17/lib64:$LD_LIBRARY_PATH

# Install Python dependencies
COPY requirements.txt /app/
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . /app

# Expose the port Flask will use
EXPOSE 5000

# Start the application with Gunicorn
CMD ["gunicorn", "app:app"]
