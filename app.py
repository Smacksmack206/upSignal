import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash
import docker
from docker.errors import APIError, NotFound

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Initialize Docker client
try:
    client = docker.from_env()
    # Check if Docker is running
    client.ping()
except Exception as e:
    # If Docker daemon is not running, we can't proceed.
    # A real app might have a more graceful error page.
    raise RuntimeError(f"Docker daemon is not running or accessible. Please start Docker. Error: {e}")

def get_launchable_containers():
    """
    Gets a list of running containers with their public-facing port mappings.
    This is a good example of a helper function that encapsulates a specific piece of logic.
    It keeps the main route clean and makes the code more modular and testable.
    """
    launchable_containers = []
    try:
        # We only care about running containers for the launch menu
        running_containers = client.containers.list(filters={"status": "running"})
        for container in running_containers:
            # The container.ports attribute gives us the port mappings
            # It's a dictionary where keys are the container ports and values are the host bindings
            ports = container.ports
            if not ports:
                continue

            launch_urls = []
            for container_port, host_bindings in ports.items():
                if host_bindings:
                    # A container port can be bound to multiple host ports
                    for binding in host_bindings:
                        # We only want to show ports that are bound to an external interface
                        if binding['HostIp'] == '0.0.0.0':
                            host_port = binding['HostPort']
                            # We assume http for simplicity. A more advanced implementation
                            # might try to detect https.
                            launch_urls.append(f"http://localhost:{host_port}")
            
            if launch_urls:
                launchable_containers.append({
                    "name": container.name,
                    "urls": launch_urls
                })
    except APIError as e:
        # If we can't get the list of containers, we'll just return an empty list
        # and flash a message to the user. This makes the application more resilient.
        flash(f"Could not retrieve launchable containers: {e}", "warning")

    return launchable_containers

@app.route('/')
def index():
    """Main dashboard page."""
    try:
        # System Info
        system_info = client.info()
        info_display = {
            'docker_version': system_info.get('ServerVersion', 'N/A'),
            'os_type': system_info.get('OperatingSystem', 'N/A'),
            'architecture': system_info.get('Architecture', 'N/A'),
            'total_containers': system_info.get('Containers', 0),
            'running_containers': system_info.get('ContainersRunning', 0),
            'total_images': system_info.get('Images', 0),
        }

        # Containers list
        try:
            all_containers = client.containers.list(all=True)
        except APIError as e:
            flash(f"Error listing containers: {e}", "danger")
            all_containers = []
        
        containers_with_stats = []
        for c in all_containers:
            try:
                image_tags = ', '.join(c.image.tags) if c.image.tags else 'N/A'
            except docker.errors.NotFound:
                image_tags = '[Image not found]'
            container_data = {
                'id': c.short_id,
                'name': c.name,
                'image': image_tags,
                'status': c.status
            }
            containers_with_stats.append(container_data)

    except APIError as e:
        flash(f"Error connecting to Docker: {e}", "danger")
        info_display = {}
        containers_with_stats = []

    return render_template('index.html', info=info_display, containers=containers_with_stats)

@app.route('/container/<container_id>/<action>', methods=['POST'])
def container_action(container_id, action):
    """Handle start, stop, remove actions for containers."""
    try:
        container = client.containers.get(container_id)
        if action == 'start':
            container.start()
            flash(f"Container {container.name} started successfully.", "success")
        elif action == 'stop':
            container.stop()
            flash(f"Container {container.name} stopped successfully.", "success")
        elif action == 'remove':
            container.remove(force=True) # Force removal if running
            flash(f"Container {container.name} removed successfully.", "success")
    except NotFound:
        flash(f"Container {container_id} not found.", "danger")
    except APIError as e:
        flash(f"Error performing action on container {container.name}: {e}", "danger")
    return redirect(url_for('index'))

@app.route('/container/<container_id>/logs')
def container_logs(container_id):
    """Display logs for a specific container."""
    try:
        container = client.containers.get(container_id)
        logs = container.logs(tail=500).decode('utf-8', errors='ignore')
    except NotFound:
        flash(f"Container {container_id} not found.", "danger")
        return redirect(url_for('index'))
    except APIError as e:
        flash(f"Error getting logs for container {container_id}: {e}", "danger")
        return redirect(url_for('index'))
    return render_template('logs.html', container_name=container.name, logs=logs)

@app.route('/container/<container_id>/details')
def container_details(container_id):
    """Display details (inspect) for a specific container."""
    try:
        container = client.containers.get(container_id)
        details = container.attrs
        # Pretty print the JSON for readability in the template
        details_str = json.dumps(details, indent=2)
    except NotFound:
        flash(f"Container {container_id} not found.", "danger")
        return redirect(url_for('index'))
    except APIError as e:
        flash(f"Error getting details for container {container_id}: {e}", "danger")
        return redirect(url_for('index'))
    return render_template('details.html', container_name=container.name, details=details_str)

@app.route('/launch')
def launch():
    """Launch menu page."""
    launchable_containers = get_launchable_containers()
    return render_template('launch.html', launchable_containers=launchable_containers)


@app.route('/run', methods=['POST'])
def run_container():
    """Run a new container."""
    image_name = request.form.get('image_name')
    container_name = request.form.get('container_name') or None
    ports = request.form.get('ports') # e.g., "8080:80, 9000:9000"
    
    if not image_name:
        flash("Image name is required.", "warning")
        return redirect(url_for('index'))

    port_bindings = {}
    if ports:
        try:
            for p in ports.split(','):
                host_port, container_port = p.split(':')
                port_bindings[int(container_port)] = int(host_port)
        except ValueError:
            flash("Invalid port mapping format. Use HOST:CONTAINER, e.g., 8080:80.", "danger")
            return redirect(url_for('index'))

    try:
        # Ensure image exists locally
        try:
            client.images.get(image_name)
        except docker.errors.ImageNotFound:
            flash(f"Image '{image_name}' not found locally. Pulling from Docker Hub...", "info")
            client.images.pull(image_name)

        client.containers.run(
            image_name,
            name=container_name,
            detach=True,
            ports=port_bindings
        )
        flash(f"Successfully started container from image {image_name}.", "success")
    except APIError as e:
        flash(f"Error running container: {e}", "danger")
        
    return redirect(url_for('index'))


@app.route('/images')
def images():
    """Images page: list local images and allow searching Docker Hub."""
    try:
        local_images = client.images.list()
    except APIError as e:
        flash(f"Error getting local images: {e}", "danger")
        local_images = []
    
    search_query = request.args.get('query')
    search_results = []
    if search_query:
        try:
            search_results = client.images.search(term=search_query)
        except APIError as e:
            flash(f"Error searching Docker Hub: {e}", "danger")

    return render_template('images.html', images=local_images, search_results=search_results, query=search_query)

@app.route('/image/pull', methods=['POST'])
def pull_image():
    """Pull an image from Docker Hub."""
    image_name = request.form.get('image_name')
    if not image_name:
        flash("No image name provided to pull.", "warning")
        return redirect(url_for('images'))
    
    flash(f"Pulling image '{image_name}'... This may take a while.", "info")
    try:
        client.images.pull(image_name)
        flash(f"Image '{image_name}' pulled successfully.", "success")
    except APIError as e:
        flash(f"Error pulling image '{image_name}': {e}", "danger")
        
    return redirect(url_for('images'))

@app.route('/image/remove', methods=['POST'])
def remove_image():
    """Remove a local image."""
    image_id = request.form.get('image_id')
    try:
        image = client.images.get(image_id)
        image_tags = ', '.join(image.tags) if image.tags else image.short_id
        client.images.remove(image=image_id, force=True) # Force removal
        flash(f"Image {image_tags} removed successfully.", "success")
    except NotFound:
        flash(f"Image {image_id} not found.", "danger")
    except APIError as e:
        # Check for conflict error (image is in use)
        if e.response.status_code == 409:
            flash(f"Cannot remove image: it is being used by one or more containers.", "danger")
        else:
            flash(f"Error removing image: {e}", "danger")
            
    return redirect(url_for('images'))

@app.route('/system/prune', methods=['POST'])
def system_prune():
    """Prune unused Docker resources."""
    try:
        prune_result = client.system.prune(all_items=True)
        reclaimed_space = prune_result.get('SpaceReclaimed', 0)
        reclaimed_mb = reclaimed_space / (1024*1024) if reclaimed_space else 0
        flash(f"System cleanup successful. Reclaimed {reclaimed_mb:.2f} MB.", "success")
    except APIError as e:
        flash(f"Error during system prune: {e}", "danger")
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)