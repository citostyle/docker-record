from docker import Client
import io
import os
import sys
import tarfile
import subprocess
import time

# record
def record(container_name):
    # use docker exec to drop the user into an instrumented bash session
    pid = os.fork()
    if pid > 0:
        start_instrumented_container(container_name)
    else:
        execute(['docker', 'exec', container_name, 'mkdir', '-p', '/tmp/record/'])
        execute(['docker', 'exec', container_name, 'touch', '/tmp/record/cmd'])
        execute(['docker', 'exec', container_name, 'touch', '/tmp/record/diff_trigger'])
        track_state_changes(container_name)


def start_instrumented_container(container_name):
    # construct the bash script that will instrument the user's session
    RECORD_TEMPLATE = """bash --init-file <(echo '{instrumentation}')"""
    INSTRUMENTATION = '''
SESSION_ROOT=/tmp/record;
mkdir -p $SESSION_ROOT;
function __instrument() {
  if [[ ! $BASH_COMMAND =~ "diff_trigger" ]]; then
    echo $EUID >> $SESSION_ROOT/euid &&
    echo $BASH_COMMAND >> $SESSION_ROOT/cmd &&
    echo $PWD >> $SESSION_ROOT/pwd &&
    echo $(export | tr "\\n" ";") >> $SESSION_ROOT/env ||
    exit;
  fi
};

shopt -s extdebug;
trap __instrument DEBUG;

PROMPT_COMMAND="tail -n 1 $SESSION_ROOT/cmd >> $SESSION_ROOT/diff_trigger"
'''
    RECORD_COMMAND = RECORD_TEMPLATE.format(instrumentation=INSTRUMENTATION.replace('\n', ' '))

    os.execlp('docker', 'docker', 'exec', '-ti', container_name, 'bash', '-c', RECORD_COMMAND)


def track_state_changes(container_name):
    fout = open("t.txt", 'ab', 0)
    # react to every line added in the 'cmd' file by the instrumented container
    client = Client()
    previous_changes = set()
    for line in execute_lines(['docker', 'exec', container_name, 'tail', '-f', '/tmp/record/diff_trigger']):
        # store changes for every command
        raw_changes = client.diff(container_name)
        current_command_changes = []
        for raw_change in raw_changes:
            #changes[raw_change['Path']] = raw_change['Kind']
            path = raw_change['Path']
            if not path in previous_changes:
                previous_changes.add(path)
                current_command_changes.append(path)
        fout.write((line.rstrip() + ":" + str(current_command_changes) + "\n").encode())

    fout.close()

def execute(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out

def execute_lines(cmd):
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)




# make it work now, refactor later
SESSION_PATH = '/tmp/record/{filename}'
COMMAND_FILENAME = 'cmd'
ENVIRONMENT_FILENAME = 'env'
WORKDIR_FILENAME = 'pwd'

BUILD_CONTEXT_PATH = './build/'

# these commands from the history should not be included in the Dockerfile
# list has to be extended, for now there are just common setup/maintenance commands
COMMAND_BLACKLIST = ['ls', 'cd', 'pwd', 'history', 'du', 'top', 'ps',
                     'exit', 'clear', 'git status', 'cat']

# Heuristic: these commands are likely to be "service"
DOCKER_CMD_WHITELIST = ['service', '/etc/init.d/']

# Heuristic: add files that were opened by an editor and correspond to docker diff
EDITOR_WHITELIST = ['nano', 'vim', 'emacs', 'joe']


def replay(container):

    commands = read_session(container, COMMAND_FILENAME)
    environments = read_session(container, ENVIRONMENT_FILENAME)
    workdirs = read_session(container, WORKDIR_FILENAME)

    dockerfile = []
    dockerfile_cmd_command = ""

    fs_changes = filesystem_diff(container)

    # Extract RUN and CMD directives from our history logs into the Dockerfile
    for command, environment, workdir in zip(commands, environments, workdirs):

        if is_blacklisted(command):
            continue

        if is_docker_cmd(command):
            # there can only be one, and this current heuristic
            # just picks the last that has been executed
            dockerfile_cmd_command = "CMD " + command
        elif is_editor(command):
            # now check whether the file was actually created/changed in the FS
            changed_path = extract_path_from_editor_command(command).replace('\n', '')
            if changed_in_filesystem(fs_changes, changed_path):
                if changed_path.startswith('/'):
                    source_path = changed_path
                else:
                    source_path = workdir + "/" + changed_path

                destination_path = BUILD_CONTEXT_PATH + flatten_path(source_path)
                copy_from_container(container, source_path, destination_path)
                dockerfile.append("ADD " + destination_path + " " + source_path)
        else:
            dockerfile.append("RUN " + command)

    dockerfile.append(dockerfile_cmd_command)

    for instruction in dockerfile:
        print(instruction)


def copy_from_container(container, source, destination):
    file_contents = copy(container, source)
    with open(destination, 'w') as f:
        f.write(file_contents)


def flatten_path(path):
    return path.replace('/', '_')


def changed_in_filesystem(fs_changes, filename):
    # ignore the Kind parameter for now
    for change_paths in fs_changes.keys():
        if filename == change_paths:
            return True
    return False


def filesystem_diff(container):
    client = Client()
    raw_changes = client.diff(container)
    changes = {}
    for raw_change in raw_changes:
        changes[raw_change['Path']] = raw_change['Kind']
    return changes


def extract_path_from_editor_command(command):
    return command.split(' ')[1]


def read_session(container, filename):
    return copy(container, SESSION_PATH.format(filename=filename)).split("\n")


def is_docker_cmd(command):
    return startswith(command, DOCKER_CMD_WHITELIST)


def is_editor(command):
    return startswith(command, EDITOR_WHITELIST)


def is_blacklisted(command):
    if not command.strip():
        return True

    return startswith(command, COMMAND_BLACKLIST)


def startswith(string, collection):
    for item in collection:
        if string.startswith(item):
            return True
    return False


def copy(container, path):
    client = Client()
    response = client.copy(container, path)
    buffer = io.BytesIO()
    buffer.write(response.data)
    buffer.seek(0)
    tar = tarfile.open(fileobj=buffer, mode='r')
    for member in tar.getmembers():
        return tar.extractfile(member).read()
