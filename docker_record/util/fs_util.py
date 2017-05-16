from docker_record.util import docker_util

FSDIFF_INIT_DELIMITER = '---init-delimiter---'
FSDIFF_DELIMITER = '---cmd-delimiter---'

SESSION_DIR = '/tmp/record'


class FileChange(object):
    def __init__(self, line):
        self.line = line
        self.action = line[0]
        self.file = line[2:]

    def __str__(self):
        return self.line

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.line == other.line

    @classmethod
    def parse_changes(cls, change_lines):
        result = {}
        for line in change_lines:
            line = line.strip()
            if line:
                change = FileChange(line)
                if not change.file.startswith(SESSION_DIR):
                    result[change.file] = change
        return result

    @classmethod
    def diff(cls, old_changes, new_changes):
        result = {}
        for key, val in new_changes.iteritems():
            old_val = old_changes.get(key)
            if not old_val or not old_val.__eq__(val):
                result[key] = val
        return result


def get_file_changes_per_command(container, filepath):
    file_content = docker_util.copy(container, filepath)
    parts = file_content.split(FSDIFF_INIT_DELIMITER)
    result = []

    changes = FileChange.parse_changes(parts[0].split('\n'))
    parts = parts[1].split(FSDIFF_DELIMITER)

    for i in range(0, len(parts)):
        part = parts[i]
        new_changes = FileChange.parse_changes(part.split('\n'))
        change_diff = FileChange.diff(changes, new_changes)
        result.append(change_diff)
        changes.update(change_diff)
    return result


def changed_in_filesystem(fs_changes, filename):
    # ignore the Kind parameter for now
    for change_paths in fs_changes.keys():
        if filename == change_paths:
            return True
    return False
