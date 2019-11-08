from docker_record.util.strace_parser import *
from docker_record.log import *
from docker_record.util import process
import os, time


TRACES_FOLDER = 'traces'
ARCHIVE_FOLDER = 'archive'

class SystemChangeTracker():
    def __init__(self, container):
        self.container = container

        # os.getcwd()
        absolute_path = os.getcwd()
        volume_session_path = absolute_path + "traces/{container_name}/".format(container_name=self.container.container_name)
        self.trace_path = volume_session_path + TRACES_FOLDER
        self.archive_path = volume_session_path + ARCHIVE_FOLDER

    def get_changes(self):
        pass

    def _parse_strace_output(self, strace_changes_command):
       out = process.execute_shell(strace_changes_command)
       raw_output = out.decode('utf-8').split('\n')

       diff = []
       for line in raw_output:
           try:
               if not line.strip():
                   continue
               path = STraceParser(line).get_path()
               diff.append(path)
           except WrongSTraceFormatException:
               #logging.warning("Unexpected STrace Output could not be parsed: " + line)
               log("GET_LATEST_CHANGES: Unexpected STrace Output could not be parsed: " + line)
       return diff


    def archive_changes(self):
        pass

# The functionality in this class has an implicit dependency with the strace command
# (i.e., it assumes that only one file is generated as opposed to multiple files per PID)
class DiffChangeTracker(SystemChangeTracker):
    def __init__(self, container):
        super().__init__(container)

    def get_changes(self):
        # no changes if directory is empty
        if len(os.listdir(self.trace_path)) == 0:
            return []

        strace_changes_command = "cat {trace_path}/trace.log | grep -a 'WRONLY' | grep -av '{session_path}'"\
                                    .format(
                                        trace_path=self.trace_path,
                                        session_path=self.container.SESSION_PATH)
        return self._parse_strace_output(strace_changes_command)

    def archive_changes(self, cmd):
        # no changes if directory is empty
        if len(os.listdir(self.trace_path)) == 0:
            return

        #TODO: replace trace.log with information from STraceContainerWrapper
        archive_command = ": > {trace_path}/trace.log".format(trace_path=self.trace_path)
        process.execute_shell(archive_command)


class NoOpChangeTracker(SystemChangeTracker):
    def __init__(self, container):
        return

    def get_changes(self):
        return []

    def archive_changes(self, cmd):
        return


class DeleteChangeTracker(SystemChangeTracker):
    def __init__(self, container):
        super(DeleteChangeTracker, self).__init__(container)

    def get_changes(self):
        # no changes if directory is empty
        if len(os.listdir(self.trace_path)) == 0:
            return []

        strace_changes_command = "cd {trace_path} && ls | xargs cat | grep 'WRONLY' | grep -v '{session_path}'"\
                                    .format(
                                        trace_path=self.trace_path,
                                        session_path=self.container.SESSION_PATH)


        return self._parse_strace_output(strace_changes_command)

    def archive_changes(self, cmd):
        # no changes if directory is empty
        if len(os.listdir(self.trace_path)) == 0:
            return

        #archive_command = " (cd {trace_path} && ls | xargs cat) > {archive_path}/{cmd}-{timestamp}-changes.log && rm -f {trace_path}/*"\


        archive_command = "rm -rf {trace_path}/*"\
                                    .format(
                                        cmd=cmd.strip().split(' ')[0],
                                        trace_path=self.trace_path,
                                        archive_path=self.archive_path,
                                        timestamp=round(time.time())
                                     )
        process.execute_shell(archive_command)

class MoveChangeTracker(SystemChangeTracker):
    def __init__(self, container):
        super(MoveChangeTracker, self).__init__(container)

    def get_changes(self):
        # no changes if directory is empty
        if len(os.listdir(self.trace_path)) == 0:
            return []

        # strace_changes_command = "cat {trace_path}/* | grep 'WRONLY' | grep -v '{session_path}'"\
        # TODO: abstract this away, have some sort of implementation of these scripts
        # --> potentially you could also have a Python implementation of this instead of executing bash, so abstraction makes sense
        strace_changes_command = "cd {trace_path} && ls | xargs cat | grep 'WRONLY' | grep -v '{session_path}'"\
                                    .format(
                                        trace_path=self.trace_path,
                                        session_path=self.container.SESSION_PATH)

        """

        TODO: This is how I want this to look like (although I'm not sure if that actually provides any robustness)

        Shell.cmd('cd', self.trace_path) \
            |Shell.conjuct| Shell.cmd('ls') \
            |Shell.pipe| Shell.cmd('xargs', 'cat') \
            |Shell.pipe| Shell.cmd('grep', "'WRONLY'") \
            |Shell.pipe| Shell.cmd('grep', '-v', self.container.container_name)
        """

        out = process.execute_shell(strace_changes_command)
        raw_output = out.decode('utf-8').split('\n')

        return self._parse_strace_output(strace_changes_command)

    def archive_changes(self, cmd):
        # no changes if directory is empty
        if len(os.listdir(self.trace_path)) == 0:
            return

        #archive_command = " (cd {trace_path} && ls | xargs cat) > {archive_path}/{cmd}-{timestamp}-changes.log && rm -f {trace_path}/*"\


        archive_command = "mkdir -p {archive_path}/{cmd}-{timestamp}/ && cd {trace_path} && ls | xargs -J % mv % {archive_path}/{cmd}-{timestamp}/"\
                                    .format(
                                        cmd=cmd.strip().split(' ')[0],
                                        trace_path=self.trace_path,
                                        archive_path=self.archive_path,
                                        timestamp=round(time.time())
                                     )
        process.execute_shell(archive_command)
