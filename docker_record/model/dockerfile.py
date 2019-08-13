from .docker_instructions import *

class Dockerfile:
    def __init__(self):
        # default values
        self.from_image = FROMInstruction("ubuntu")
        self.ordered_instruction = []
        self.exposes = set()
        self.volumes = set()
        self.cmd = CMDInstruction(None)

    def add_instruction(self, instruction: OrderedInstruction):
        self.ordered_instruction.append(instruction)

    def __str__(self):
        output = []

        for instruction_set in [[self.from_image], self.ordered_instruction, self.exposes, self.volumes, [self.cmd]]:
            for instruction in instruction_set:
                output.append(str(instruction))

        return "\n".join(output)