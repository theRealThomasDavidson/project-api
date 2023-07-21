# Use an official Python runtime as the base image
FROM python:3.11.4-alpine3.18

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the dependencies
RUN apk update && apk add --no-cache mariadb-connector-c-dev
RUN pip install --no-cache-dir -r requirements.txt
RUN apk add --no-cache bash
# Copy the application code to the container
COPY . .
RUN wget -O /usr/local/bin/wait-for-it.sh https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh
RUN chmod +x /usr/local/bin/wait-for-it.sh

# Set the environment variables
ENV DB_USERNAME=$DB_USERNAME
ENV DB_PASSWORD=$DB_PASSWORD
ENV DB_HOST=$DB_HOST
ENV DB_NAME=$DB_NAME
ENV FLASK_APP=$FLASK_APP

# Expose the port your Flask application runs on
EXPOSE 5000

# Define the command to run your Flask application
CMD ["sh", "-c", "/usr/local/bin/wait-for-it.sh ${DB_HOST}:3306} --timeout=120 -- flask run --host=0.0.0.0"]