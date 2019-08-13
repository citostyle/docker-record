from ..container.state_change_transition_graph import StateChangeTransitionGraph

from ..container.instrumented_container import InstrumentedContainer
from ..container.state_changes import WorkdirStateChange


# a
class Curation:
    def curate(self):
        pass


class NaiveCuration:
    def __init__(self, container: InstrumentedContainer):
        self.container = container

    def curate(self):
        commands = self.container.read_session_file(InstrumentedContainer.COMMANDS_FILE).split("\n")
        environments = self.container.read_session_file(InstrumentedContainer.ENVIRONMENTS_FILE).split("\n")
        workdirs = self.container.read_session_file(InstrumentedContainer.WORKDIRS_FILE).split("\n")
        #raw_transitions = self.container.get_tracked_changes()

        dockerfile = []
        dockerfile_cmd_command = ""

        raw_changes = self.container.filesystem_diff()
        fs_changes = {}
        for raw_change in raw_changes:
            fs_changes[raw_change['Path']] = raw_change['Kind']

        stg = StateChangeTransitionGraph()

        # Extract RUN and CMD directives from our history logs into the STG
        for command, environment, workdir in zip(commands, environments, workdirs):
            if self.is_blacklisted(command):
                continue

            stg.add_transition(command, [WorkdirStateChange(workdir)])


    @staticmethod
    def changed_in_filesystem(fs_changes, filename):
        # ignore the Kind parameter for now
        for change_paths in fs_changes.keys():
            if filename == change_paths:
                return True
        return False

    @staticmethod
    def extract_path_from_editor_command(command: str) -> str:
        return command.split(' ')[1]

    @staticmethod
    def startswith_elemet_in_list(string, collection):
        for item in collection:
            if string.startswith(item):
                return True
        return False

    def is_blacklisted(self, command):
        if not command.strip():
            return True

        # these commands from the history should not be included in the STG
        # list has to be extended, for now there are just common setup/maintenance commands
        COMMAND_BLACKLIST = ['ls', 'cd', 'pwd', 'history', 'du', 'top', 'ps',
                             'exit', 'clear', 'git status', 'cat']
        return NaiveCuration.startswith_elemet_in_list(command, COMMAND_BLACKLIST)




    #dockerfile.append(dockerfile_cmd_command)