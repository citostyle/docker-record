import os
import time
import subprocess
from docker_record.util import docker_util, fs_util, cmd_util, common

# file path constants
COMMAND_FILEPATH = '%s/cmd' % fs_util.SESSION_DIR
ENVIRONMENT_FILEPATH = '%s/env' % fs_util.SESSION_DIR
WORKDIR_FILEPATH = '%s/pwd' % fs_util.SESSION_DIR
FSDIFF_FILEPATH = '%s/fsdiff' % fs_util.SESSION_DIR

BUILD_CONTEXT_PATH = './build/'
DOCKER_SOCKET_PATH = '/var/run/docker.sock'
CONTAINER_BOOTSTRAP_SECS = 5

# record

def record(container_or_image):

    # run container if the given parameter is an image
    container = container_or_image
    if not docker_util.is_running_container(container_or_image):
        # start container from image
        cmd = 'docker run -it -d -v {sock}:{sock} -e DOCKER_HOST=unix://{sock} --entrypoint= {img} /bin/sh'
        result = common.run(cmd.format(sock=DOCKER_SOCKET_PATH, img=container_or_image))
        container = result.strip()[:12]
        print('Started container from image %s: %s' % (container_or_image, container))
        print('Waiting a few moments until container has initialized')
        time.sleep(CONTAINER_BOOTSTRAP_SECS)

    # construct the bash script that will instrument the user's session
    RECORD_TEMPLATE = """bash --init-file <(echo '{instrumentation}')"""
    INSTRUMENTATION = '''
SESSION_ROOT=%s;
CONTAINER_ID=%s;
mkdir -p $SESSION_ROOT;
function __instrument() {
  echo $EUID >> $SESSION_ROOT/euid &&
  echo $BASH_COMMAND >> $SESSION_ROOT/cmd &&
  echo $PWD >> $SESSION_ROOT/pwd &&
  echo $(export | tr "\\n" ";") >> $SESSION_ROOT/env &&
  docker diff $CONTAINER_ID >> $SESSION_ROOT/fsdiff &&
  echo "%s" >> $SESSION_ROOT/fsdiff &&
  true ||
  exit;
};
docker diff $CONTAINER_ID >> $SESSION_ROOT/fsdiff; echo "%s" >> $SESSION_ROOT/fsdiff;
shopt -s extdebug;
trap __instrument DEBUG;''' % (fs_util.SESSION_DIR, container, fs_util.FSDIFF_DELIMITER, fs_util.FSDIFF_INIT_DELIMITER)
    RECORD_COMMAND = RECORD_TEMPLATE.format(instrumentation=INSTRUMENTATION.replace('\n', ' '))

    # use docker exec to drop the user into an instrumented bash session
    os.execlp('docker', 'docker', 'exec', '-ti', container, 'bash', '-c', RECORD_COMMAND)


# replay

def replay(container):

    commands = read_session(container, COMMAND_FILEPATH)
    environments = read_session(container, ENVIRONMENT_FILEPATH)
    workdirs = read_session(container, WORKDIR_FILEPATH)
    fschanges = fs_util.get_file_changes_per_command(container, FSDIFF_FILEPATH)
    # make sure we have the same array lengths
    fschanges = fschanges[-len(commands):]

    dockerfile = []
    dockerfile_cmd_command = ""

    fs_changes = docker_util.filesystem_diff(container)

    # Extract RUN and CMD directives from our history logs into the Dockerfile
    for command, environment, workdir, fschange in zip(commands, environments, workdirs, fschanges):

        if cmd_util.is_blacklisted(command):
            continue

        if cmd_util.is_docker_cmd(command):
            # there can only be one, and this current heuristic
            # just picks the last that has been executed
            dockerfile_cmd_command = "CMD " + command
        elif cmd_util.is_editor(command):
            # now check whether the file was actually created/changed in the FS
            changed_path = cmd_util.extract_path_from_editor_command(command).replace('\n', '')
            if fs_util.changed_in_filesystem(fs_changes, changed_path):
                if changed_path.startswith('/'):
                    source_path = changed_path
                else:
                    source_path = workdir + "/" + changed_path

                destination_path = BUILD_CONTEXT_PATH + flatten_path(source_path)
                docker_util.copy_from_container(container, source_path, destination_path)
                dockerfile.append("ADD " + destination_path + " " + source_path)
        else:
            dockerfile.append("# creates filesystem changes: %s" % fschange.values())
            dockerfile.append("RUN " + command)

    dockerfile.append(dockerfile_cmd_command)

    for instruction in dockerfile:
        print instruction


def flatten_path(path):
    return path.replace('/', '_')


def read_session(container, filepath):
    return docker_util.copy(container, filepath).strip().split("\n")
