#!/bin/bash

# Detect the operating system
if [[ "$(uname)" == "Darwin" ]]; then
  # macOS
  DOCKER_SOCKET_PATH="/Users/home/.docker/run/docker.sock"
elif [[ "$(uname)" == "Linux" ]]; then
  # Linux
  DOCKER_SOCKET_PATH="/var/run/docker.sock"
else
  echo "Unsupported operating system."
  exit 1
fi

# Export the variable so docker-compose can use it
export DOCKER_SOCKET_PATH

# Run docker-compose with the provided arguments
docker-compose "$@"