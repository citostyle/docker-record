import os
from docker_record.container.changetracking.container_persistent_changes import ContainerPersistentStateChanges
from docker_record.container.container_wrapper import ContainerWrapper, STraceContainerWrapper
from docker_record.container.changetracking.state_transition import StateTransitionGraph
from ..util import docker
from ..util import process


class InstrumentedContainer:
    SESSION_PATH = '/tmp/record/'
    COMMANDS_FILE = 'cmd'
    WORKDIR_FILE = 'pwd'
    ENVIRONMENT_FILE = 'env'
    DIFF_TRIGGER_FILE = 'diff_trigger'

    def __init__(self, container_name):
        self.container_name = container_name

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

        # react to every line added in the 'diff_trigger' file by the instrumented container
        for line in process.execute_lines(['docker', 'exec', self.container_name, 'tail', '-f',
                                           self.session_path(InstrumentedContainer.DIFF_TRIGGER_FILE)]):
            # store changes for every command signaled through every line written into 'DIFF_TRIGGER_FILE'
            persistent_state.track_state(line)
            if str(line) == "exit":
                break

    def get_tracked_state_changes(self):
        return StateTransitionGraph(self.container_name).read_from_file()

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

    def start(self):
        STraceContainerWrapper(self).start_container()

    def copy_from(self, source_path, destination_path):
        return docker.copy_from_container(self.container_name, source_path, destination_path)