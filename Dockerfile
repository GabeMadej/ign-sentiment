# Use a specific version of the Python image
FROM python:3.8-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install Google Chrome
RUN apt-get update -qqy && \
    apt-get -qqy install \
      wget \
      gnupg2 \
      unzip && \
    wget https://dl.google.com/linux/direct/google-chrome-beta_current_amd64.deb && \
    dpkg -i google-chrome-beta_current_amd64.deb; apt-get -fy install && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* && \
    rm google-chrome-beta_current_amd64.deb

# Copy chromedriver to container
COPY ./chromedriver /usr/local/bin/chromedriver
RUN chmod +x /usr/local/bin/chromedriver

# Copy the Python script into the container
COPY main.py .

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 80 to the outside world
EXPOSE 8080

# Define environment variable
ENV PORT 8080

# List contents of /app
RUN ls -la /app

# Command to run the application
CMD ["python3", "main.py"]
