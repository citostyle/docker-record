from docker import Client
import io
import os
import sys
import tarfile
import subprocess
import csv


## restructure
# c = InstrumentedContainer(name)
# c.record()
# --> introduce another abstracted helper function for stuff like
# execute(['docker', 'exec', container_name, '>', '/tmp/record/diff_trigger'])
# c.exec('>', '/tmp/record/diff_trigger')
#
# Make container util class for stuff like container_exists
#
# There is a central place where we store info on where the state changes are persisted
# right now it's statically encoded in read_fs_changes (track_state_changes then takes these to not start from scratch)
#
# Have exclusion patterns for limiting the queries to filesystem in container for timing information
#
# Introduce transient change tracking (probably in track_state_changes)
#
# Have another class that takes in all the state change information and tries to create the Dockerfile
# That can be totally abstracted away, probably we can provide a super simple base class for this
# class Generator:
#   def generate <-- weird name, I can probably do better than this
#
#   --> base generator also has a standard I/O provider
#
# Probably it's actually that simple, because then I can have subclasses like
# DockerfileGenerator
# AnsibleGenerator
# DockerfileIdiomaticGenerator (inherits from DockerfileGenerator and
# adds the opaque function from our probabilistic model)
#
# g = DockerfileGenerator()
#
# g.generate()
# In that sense, the InstrumentedContainer and the generators can be
# seen as two totally orthogonal programs  that only communicate over
# the shared state change data structures
#
# Although it might make sense to do some of the optimizations on the fly
# (like remove commands that have no state changes, might make tracking harder and more convoluted though)
#
# class DockerfileGenerator()
#    def __init__(container_name):
#
#    # returns a Dockerfile Object
#    def generate():
#
#
# class OutputProvider() # base class
#   def __init__():
#
#   def ... <-- not sure how the output provider should look like
#
#
#

# record
def record(container_name):
    if not container_exists(container_name):
        #create_container(container_name)
        print("Container does not exist. Please start the container that we can attach to", file=sys.stderr)
        exit()


    # use docker exec to drop the user into an instrumented bash session

    pid = os.fork()
    if pid > 0:
        start_instrumented_container(container_name)
    else:
        execute(['docker', 'exec', container_name, 'mkdir', '-p', '/tmp/record/'])
        execute(['docker', 'exec', container_name, 'touch', '/tmp/record/cmd'])
        execute(['docker', 'exec', container_name, '>', '/tmp/record/diff_trigger'])

        fs_changes = read_fs_changes(container_name)
        track_state_changes(container_name, fs_changes)


EXIT_SIGNAL = "!EXIT!"

#TODO: replace #EXIT# with constant
def start_instrumented_container(container_name):
    # construct the bash script that will instrument the user's session
    RECORD_TEMPLATE = """bash --init-file <(echo '{instrumentation}')"""
    INSTRUMENTATION = '''
SESSION_ROOT=/tmp/record;
EXIT_SIGNAL="!EXIT!"
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

#function __finish() {
#   $EXIT_SIGNAL >> $SESSION_ROOT/diff_trigger;
#};
#trap __finish EXIT;

    RECORD_COMMAND = RECORD_TEMPLATE.format(instrumentation=INSTRUMENTATION.replace('\n', ' '))

    os.execlp('docker', 'docker', 'exec', '-ti', container_name, 'bash', '-c', RECORD_COMMAND)


def container_exists(container_name):
    client = Client()
    container_list = client.containers()
    return len([container['Names'] for container in container_list if ('/' + container_name) in container['Names']]) == 1


def create_container(container_name):
    client = Client()
    image_name = input("Container does not exist. We'll start one. What should the base image be?")
    if not image_name:
        image_name = "ubuntu"
    create_container(image_name, detach=True, name=container_name)


# create class/module that deals with all things filesystem (changes, tracking, etc.)
def write_filesystem_changes(fs_changes, fout_fs):
    fout_fs.write((",".join([str(change['path']) + "::" + str(change['timestamp']) for change in fs_changes]) + "\n").encode())

def read_filesystem_changes(line):
    if not "," in line: return None

    for change in line.split(","):
        if not "::" in change:
            next
        path, timestamp = change.split("::")
        yield path, timestamp

def read_fs_changes(container_name):
    fs_changes = {}
    try:
        fin_fs = open(get_filesystem_track_filename(container_name), 'rb', 0)
        for line in fin_fs:
            for path, timestamp in read_filesystem_changes(str(line)):
                fs_changes[path] = timestamp
        fin_fs.close()
        return fs_changes
    except Exception as ex:
        print(ex.with_traceback())
        return {}



def get_command_track_filename(container_name):
    return "traces/" + container_name + "_cmd.txt"


def get_filesystem_track_filename(container_name):
    return "traces/" + container_name + "_fs.txt"


def track_state_changes(container_name, persisted_fs_changes):
    fout_cmd = open(get_command_track_filename(container_name), 'ab', 0)
    fout_fs = open(get_filesystem_track_filename(container_name), 'ab', 0)
    # react to every line added in the 'diff_trigger' file by the instrumented container
    client = Client()
    previous_changes = set()
    fs_changes = persisted_fs_changes
    print(fs_changes)
    for line in execute_lines(['docker', 'exec', container_name, 'tail', '-f', '/tmp/record/diff_trigger']):
        # store changes for every command
        raw_changes = client.diff(container_name)
        current_command_changes = []
        for raw_change in raw_changes:
            path = raw_change['Path']
            if not path in fs_changes:
                previous_changes.add(path)
                path_change_timestamp = get_container_file_timestamp(container_name, path)
                fs_changes[path] = path_change_timestamp
                current_command_changes.append({'path': path, 'timestamp': path_change_timestamp})
        fout_cmd.write((line.rstrip() + "\n").encode())
        write_filesystem_changes(current_command_changes, fout_fs)

    fout_fs.close()
    fout_cmd.close()


def get_container_file_timestamp(container_name, filename):
    # date -r beehive-1930_cmd.txt +%s
    # +%s returns a timestamp
    timestamp = execute(['docker', 'exec', container_name, 'date', '-r', filename, '+%s'])
    return timestamp.rstrip()



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
