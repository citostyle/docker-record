from typing import List
from .change_tracking import DiffChangeTracker
from .state_transition import StateTransition, StateTransitionGraph


class ContainerPersistentStateChanges:
    """
        Manages writes of persistent state changes in the container

        For each change in persistent state (container filesystem) we add the line with following syntax
        path in container filesystem
    """

    def __init__(self, instrumented_container):
        self.container = instrumented_container
        self.state_transitions = StateTransitionGraph(self.container.container_name)
        self.system_change_tracker = DiffChangeTracker(self.container)

    def track_state(self, line: str):
        current_command = str(line)
        current_command_changes = self.system_change_tracker.get_changes()
        transition = StateTransition(current_command, current_command_changes)

        self.state_transitions.add(transition)
        self.archive_latest_changes(current_command)

    def get_latest_changes(self):
        diff = self.system_change_tracker.get_changes()
        return diff

    def archive_latest_changes(self, cmd):
        self.system_change_tracker.archive_changes(cmd)