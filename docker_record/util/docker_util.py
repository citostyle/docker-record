import io
import tarfile
from docker import Client


def is_running_container(id):
    docker_client = Client()
    containers = docker_client.containers()
    for container in containers:
        if container['Id'].startswith(id):
            return True
    return False


def copy_from_container(container, source, destination):
    file_contents = copy(container, source)
    with open(destination, 'w') as f:
        f.write(file_contents)


def filesystem_diff(container):
    client = Client()
    raw_changes = client.diff(container)
    changes = {}
    for raw_change in raw_changes:
        changes[raw_change['Path']] = raw_change['Kind']
    return changes


def copy(container, path):
    client = Client()
    # client.copy(..) is deprecated, use client.get_archive(..) instead
    stream, status = client.get_archive(container, path)
    buffer = io.BytesIO()
    buffer.write(stream.read())
    buffer.seek(0)
    tar = tarfile.open(fileobj=buffer, mode='r')
    for member in tar.getmembers():
        return tar.extractfile(member).read()
