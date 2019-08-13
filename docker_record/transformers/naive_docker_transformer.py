from ..container.state_change_transition_graph import *
from ..model.dockerfile import *

BUILD_CONTEXT_PATH = './build/'

class NaiveDockerTransformer:

    def __init__(self, stg: StateChangeTransitionGraph):
        self.stg = stg

    def transformer(self) -> Dockerfile:
        dockerfile = Dockerfile()
        for command, changes in self.stg:
            if self.is_docker_cmd(command):
                # there can only be one, and this current heuristic
                # just picks the last that has been executed
                dockerfile.cmd = command
            elif self.is_editor(command):
                # now check whether the file was actually created/changed in the FS
                """
                changed_path = extract_path_from_editor_command(command).replace('\n', '')
                if changed_in_filesystem(fs_changes, changed_path):
                    if changed_path.startswith('/'):
                        source_path = changed_path
                    else:
                        source_path = workdir + "/" + changed_path

                    destination_path = BUILD_CONTEXT_PATH + self.flatten_path(source_path)
                    copy_from_container(container, source_path, destination_path)
                    dockerfile.append("ADD " + destination_path + " " + source_path)
                """
            else:
                dockerfile.add_instruction(RUNInstruction(command))

            workdir = self.get_workdir_change(changes)
            if workdir is not None:
                dockerfile.add_instruction(workdir)

        return dockerfile

    @staticmethod
    def get_workdir_change(changes: List[StateChange]):
        for change in changes:
            if type(change) == 'WorkdirStateChange':
                return change.workdir
        return None

    @staticmethod
    def startswith_elemet_in_list(string, collection):
        for item in collection:
            if string.startswith(item):
                return True
        return False

    @staticmethod
    def flatten_path(path: str) -> str:
        return path.replace('/', '_')

    @staticmethod
    def is_service(command):
        # Heuristic: these commands are likely to be "service"
        SERVICE_FOLDER_WHITELIST = ['service', '/etc/init.d/']
        return NaiveDockerTransformer.startswith_elemet_in_list(command, SERVICE_FOLDER_WHITELIST)

    @staticmethod
    def is_editor(command):
        # Heuristic: add files that were opened by an editor and correspond to docker diff
        EDITOR_WHITELIST = ['nano', 'vim', 'emacs', 'joe']
        return NaiveDockerTransformer.startswith_elemet_in_list(command, EDITOR_WHITELIST)