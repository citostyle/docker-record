from typing import List
from .state_changes import StateChange

"""
    We do not model the actual state (starting from an initial state) but
    rather the effect an action has on the existing state
"""
class StateChangeTransitionGraph:
    def __init__(self):
        self.transitions = []

    def add_transition(self, command: str, changes: List[StateChange]):
        self.transitions.append((command, changes))

    def __iter__(self):
        for command, changes in self.transitions:
            yield command, changes