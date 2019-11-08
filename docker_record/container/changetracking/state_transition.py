from typing import List

class StateTransition:
    def __init__(self, command: str, changes: List[str]):
        self.command = command
        self.changes = changes

    @staticmethod
    def from_file_line(line: str):
        command, changes_str_list = line.split(":")
        changes = changes_str_list.split(",")
        return StateTransition(command, changes)

    def __str__(self):
        return (self.command.rstrip() + ":" + (",".join(self.changes)) + "\n")

class StateTransitionGraph:
    def __init__(self, container_name):
        self.container_name = container_name
        self.stg_filename = "traces/" + self.container_name + ".stg"
        self.transitions = []

    """
        Adds new transition to graph (list) and at the same time appends it to STG file
    """
    def add(self, transition: StateTransition):
        self.transitions.append(transition)
        file_handle = open(self.stg_filename, 'ab', 0)
        file_handle.write(str(transition).encode())
        file_handle.close()

    def read_from_file(self):
        file_handle = open(self.stg_filename, 'rb', 0)
        state_transitions = []
        for line in file_handle:
            state_transitions.append(StateTransition.from_file_line(line))
        return state_transitions
