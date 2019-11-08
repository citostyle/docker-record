import io, tarfile
from docker import Client
from .process import execute

def container_exists(container_name):
    client = Client()
    container_list = client.containers()
    return len([container['Names'] for container in container_list if ('/' + container_name) in container['Names']]) == 1


def create_container(container_name, image_name=None):
    client = Client()
    if not image_name:
        image_name = "ubuntu"
    client.create_container(image_name, detach=True, name=container_name)


def container_diff(container_name):
    client = Client()
    return client.diff(container_name)


def container_commit(container_name, image_name, image_tag = 'latest'):
    output = execute("docker commit {container_name} {image_name}:{image_tag}".format(container_name=container_name,
                                                                                      image_name=image_name,
                                                                                      image_tag=image_tag))
    return output


def copy(container, path):
    client = Client()
    response = client.copy(container, path)
    buffer = io.BytesIO()
    buffer.write(response.data)
    buffer.seek(0)
    tar = tarfile.open(fileobj=buffer, mode='r')
    for member in tar.getmembers():
        return tar.extractfile(member).read()


def copy_from_container(container_name, source, destination):
    file_contents = copy(container_name, source)
    with open(destination, 'w') as f:
        f.write(file_contents)


def copy(container_name, path):
    client = Client()
    response = client.copy(container_name, path)
    buffer = io.BytesIO()
    buffer.write(response.data)
    buffer.seek(0)
    tar = tarfile.open(fileobj=buffer, mode='r')
    for member in tar.getmembers():
        return tar.extractfile(member).read()