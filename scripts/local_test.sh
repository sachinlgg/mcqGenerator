#!/bin/bash

# Define PostgreSQL container name
CONTAINER_NAME="postgres_local_test"

# Check if the container exists
if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
  # Container exists, so stop and remove it
  docker stop $CONTAINER_NAME
  docker rm $CONTAINER_NAME
  echo "Container '$CONTAINER_NAME' has been stopped and removed."
else
  # Container doesn't exist
  echo "Container '$CONTAINER_NAME' does not exist."
fi

# Define PostgreSQL password (change this to a secure value)
POSTGRES_PASSWORD="pytest"

# Define the port on which PostgreSQL will run inside the container
POSTGRES_PORT=5432

# Define the name of the database you want to create
DATABASE_NAME="your_database_name"

# Pull the official PostgreSQL Docker image (adjust the version as needed)
docker pull postgres:13

# Run a PostgreSQL container with the specified settings
docker run --name $CONTAINER_NAME -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD -p $POSTGRES_PORT:5432 -d postgres:13

# Wait for the container to fully start (you can adjust the sleep time as needed)
sleep 5

# Check the status of the PostgreSQL container
docker ps -a | grep $CONTAINER_NAME

# Create the database if it doesn't exist
docker exec -i $CONTAINER_NAME psql -U postgres -c "CREATE DATABASE IF NOT EXISTS $DATABASE_NAME"

echo "PostgreSQL container is running on port $POSTGRES_PORT."
echo "Database '$DATABASE_NAME' has been created (if it didn't already exist)."
echo "You can connect to it using:"
echo "Host: localhost"
echo "Port: $POSTGRES_PORT"
echo "Username: postgres"
echo "Password: $POSTGRES_PASSWORD"

cd ..
cd backend/
pip3 install -r requirements.txt
pip3 install "pytest>=7.1.2"
pip3 install "pytest-mock>=3.10.0"
pip3 install "pytest-env>=0.8.1"

pytest -vv tests/