# Abstract state change class
class StateChange:
    def __init__(self):
        pass

class WorkdirStateChange(StateChange):
    def __init__(self, workdir):
        self.workdir = workdir

class FilesystemStateChange(StateChange):
    SPLIT_TOKEN = "::"

    def __init__(self, path: str, timestamp: str):
        self.path = path
        self.timestamp = timestamp

    def __str__(self) -> str:
        return str(self.path) + FilesystemStateChange.SPLIT_TOKEN + str(self.timestamp)

    @staticmethod
    def parse(line: str):
        if not "," in line: return None

        for change in line.split(","):
            if not "::" in change:
                next
            path, timestamp = change.split(FilesystemStateChange.SPLIT_TOKEN)
            yield path, timestamp