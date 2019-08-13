import os, logging
from ..util import docker
from ..util import process
from ..util.strace_parser import *
from .container_persistent_changes import ContainerPersistentStateChanges

class InstrumentedContainer:
    SESSION_PATH = '/tmp/record/'
    COMMANDS_FILE = 'cmd'
    WORKDIR_FILE = 'pwd'
    ENVIRONMENT_FILE = 'env'
    DIFF_TRIGGER_FILE = 'diff_trigger'
    TRACES_FOLDER = 'traces'

    def __init__(self, container_name):
        self.container_name = container_name
        absolute_path = "/Users/IBM/MIT/projects/docker-record/bin/"
        self.volume_session_path = absolute_path + "traces/{container_name}/".format(container_name=self.container_name)

        if not docker.container_exists(container_name):
            raise Exception("Container does not exist. Please start the container that we can attach to")

    def initialize(self):
        self.execute(['mkdir', '-p', InstrumentedContainer.SESSION_PATH])
        self.execute(['touch', self.session_path(InstrumentedContainer.COMMANDS_FILE)])
        self.execute(['>', self.session_path(InstrumentedContainer.DIFF_TRIGGER_FILE)])

    def session_path(self, filename: str) -> str:
        return InstrumentedContainer.SESSION_PATH + filename

    def read_session_file(self, filename):
        return docker.copy(self.container_name, self.session_path(filename))

    def track_state_changes(self):
        persistent_state = ContainerPersistentStateChanges(self)
        persistent_state.tracking_session_start()

        # react to every line added in the 'diff_trigger' file by the instrumented container
        for line in process.execute_lines(['docker', 'exec', self.container_name, 'tail', '-f',
                                           self.session_path(InstrumentedContainer.DIFF_TRIGGER_FILE)]):
            # store changes for every command signaled through every line written into 'DIFF_TRIGGER_FILE'
            persistent_state.track_state(line)

        persistent_state.tracking_session_close()

    def get_tracked_state_changes(self):
        persistent_state = ContainerPersistentStateChanges(self)
        return persistent_state.get_state_changes()

    def execute(self, command):
        if type(command) != list:
            command = [command]
        return process.execute(['docker', 'exec', self.container_name] + command)

    def filesystem_diff(self):
        diff = docker.container_diff(self.container_name)

        # filter from exclusion patterns
        exclusion_prefix = ['/tmp', '/root']
        for prefix in exclusion_prefix:
            diff = list(filter(lambda item: not str(item['Path']).startswith(prefix), diff))
        return diff

    def get_file_timestamp(self, filename):
        # date -r beehive-1930_cmd.txt +%s
        # +%s returns a timestamp
        timestamp = self.execute(['date', '-r', filename, '+%s'])
        if not timestamp:
            return None
        return timestamp.rstrip()

    def start(self):
        # construct the bash script that will instrument the user's session
        RECORD_TEMPLATE = """strace -o /tmp/record/traces/trace.log -ff -e trace=openat bash --init-file <(echo '{instrumentation}')"""
        INSTRUMENTATION = self._get_instrumentation_sequence()

        RECORD_COMMAND = RECORD_TEMPLATE.format(instrumentation=INSTRUMENTATION.replace('\n', ' '))

        os.execlp('docker', 'docker', 'exec', '-ti', self.container_name, 'bash', '-c', RECORD_COMMAND)

    def copy_from(self, source_path, destination_path):
        return docker.copy_from_container(self.container_name, source_path, destination_path)

    @staticmethod
    def _get_instrumentation_sequence():
        #TODO: replace 'SESSION_ROOT' and 'cmd' with class constant
        return '''
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
        # bug in prompt_command --> prints multiple things into diff_trigger if some output makes the promp appear multiple times,
        # even though it's the same command, we probably need to check the line numbers here to avoid duplication





