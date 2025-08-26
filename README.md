# Docker Web Dashboard

A Flask-based web application to manage Docker containers and images with a Material Design interface.

## Features

- **Dashboard:** View system information and a list of all containers.
- **Container Control:** Start, stop, and remove containers.
- **Container Insights:** View container logs and inspect detailed information.
- **Image Management:** List local images, pull images from Docker Hub, and remove local images.
- **System Prune:** Clean up unused Docker resources (containers, images, networks).
- **Responsive UI:** Material Design for Bootstrap (MDB) provides a clean interface that works on all devices.

## Prerequisites

- Python 3.7+
- Docker installed and running on your machine.
- The user running the application must have permission to access the Docker socket (`/var/run/docker.sock`). You can achieve this by adding the user to the `docker` group:
  ```sh
  sudo usermod -aG docker $USER
  ```
  You may need to log out and log back in for this change to take effect.

## Setup and Run (Local Development)

1.  **Clone the repository (or download the files).**

2.  **Create and activate a virtual environment:**
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

4.  **Run the Flask application:**
    ```sh
    python app.py
    ```

5.  Open your web browser and navigate to `http://127.0.0.1:5001`.

## Build and Run (Docker)

You can also build and run this application as a Docker container itself.

1.  **Build the Docker image:**
    ```sh
    docker build -t docker-dashboard .
    ```

2.  **Run the Docker container:**
    The `-v /var/run/docker.sock:/var/run/docker.sock` flag is crucial. It mounts the host's Docker socket into the container, allowing the application to manage Docker.
    ```sh
    docker run -d -p 5001:5001 -v /var/run/docker.sock:/var/run/docker.sock --name docker-dashboard docker-dashboard
    ```

3.  Open your web browser and navigate to `http://<your-docker-host-ip>:5001`.

