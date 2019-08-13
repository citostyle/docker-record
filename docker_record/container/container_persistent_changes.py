from typing import List
import os

from .state_change_transition_graph import StateChangeTransitionGraph
from .state_changes import FilesystemStateChange, StateChange
#from .instrumented_container import InstrumentedContainer
from ..log import *


class ContainerPersistentStateChanges:
    """
        Manages writes of persistent state changes in the container

        For each change in persistent state (container filesystem) we add the line with following syntax
        path in container filesystem
    """
    def __init__(self, instrumented_container):
        self.container = instrumented_container

        # Commands and changes are simulatenously written into two files, each line corresponding to the other
        # The command file is (basically) a replication of the `history` shell command
        # The changes file is a comma separated line storing path (in the container) and timestamp
        # (divided by a SPLIT token -- '::')
        self.changes_filename = "traces/" + self.container.container_name + "_fs.txt"
        self.commands_filename = "traces/" + self.container.container_name + "_cmd.txt"

        # initialize by reading in existing state changes from (potential) previous session
        self.changes = self.__read_fs_changes(self.changes_filename)

    def track_state(self, line: str):
        current_command = line
        raw_changes = self.container.filesystem_diff()
        current_command_changes = []
        previous_changes = set()
        log(raw_changes)
        for raw_change in raw_changes:
            path = raw_change['Path']
            if not path in self.changes:
                previous_changes.add(path)
                path_change_timestamp = self.container.get_file_timestamp(path)
                self.changes[path] = path_change_timestamp
                current_command_changes.append(FilesystemStateChange(path, path_change_timestamp))
            else:
                path_change_timestamp = self.container.get_file_timestamp(path)
                if not (str(path_change_timestamp) == str(self.changes[path])):
                    self.changes[path] = path_change_timestamp
                    current_command_changes.append(FilesystemStateChange(path, path_change_timestamp))

        self.persist_command(current_command)
        self.persist_changes(current_command_changes)

    def persist_command(self, line: str):
        self._fout_cmd.write((line.rstrip() + "\n").encode())

    def persist_changes(self, changes: List[StateChange]):
        self._fout_fs.write((",".join([str(change) for change in changes]) + "\n").encode())

    def tracking_session_start(self):
        self._fout_cmd = open(self.commands_filename, 'ab', 0)
        self._fout_fs = open(self.changes_filename, 'ab', 0)

    def tracking_session_close(self):
        self.__fout_fs.close()
        self.__fout_cmd.close()

    def get_state_changes(self):
        stg = StateChangeTransitionGraph()
        with open(self.commands_filename) as fin_cmd, open(self.changes_filename) as fin_fs:
            for raw_cmd_line, raw_fs_line in zip(fin_cmd, fin_fs):
                cmd_line = raw_cmd_line.strip()
                fs_line = raw_fs_line.strip()
                fs_changes = []
                for path, timestamp in FilesystemStateChange.parse(str(fs_line)):
                    fs_changes.append(FilesystemStateChange(path, timestamp))
                stg.add_transition(cmd_line, fs_changes)
        return stg

    @staticmethod
    def __read_fs_changes(track_filename):
        fs_changes = {}
        try:
            if not os.path.exists(track_filename):
                return {}

            fin_fs = open(track_filename, 'rb', 0)
            for line in fin_fs:
                for path, timestamp in FilesystemStateChange.parse(str(line)):
                    fs_changes[path] = timestamp
            fin_fs.close()
            return fs_changes
        except Exception as ex:
            print(ex.with_traceback())
            return {}

