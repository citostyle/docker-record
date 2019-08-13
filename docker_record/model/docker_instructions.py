class DockerInstruction:
    def __init__(self):
        pass


class EXPOSEInstruction(DockerInstruction):
    def __init__(self, port: int):
        self.port = port

    def __str__(self):
        return "EXPOSE " + str(self.port)

class FROMInstruction(DockerInstruction):
    def __init__(self, image: str):
        self.image = image

    def __str__(self):
        return "FROM " + self.image

class VOLUMEInstruction(DockerInstruction):
    def __init__(self, path: str):
        self.path = path

    def __str__(self):
        return "VOLUME " + self.path


class CMDInstruction(DockerInstruction):
    def __init__(self, command: str):
        self.command = command

    def __str__(self):
        if self.command is None:
            return ""
        return "CMD " + self.command


class OrderedInstruction(DockerInstruction):
    def __init__(self):
        pass

class RUNInstruction(OrderedInstruction):
    def __init__(self, command: str):
        self.command = command

    def __str__(self):
        return "RUN " + self.command


class COPYInstruction(OrderedInstruction):
    def __init__(self, source_path: str, destination_path: str):
        self.source_path = source_path
        self.destination_path = destination_path

    def __str__(self):
        return "COPY {source} {destination}".format(source=self.source_path, destination=self.destination_path)


class WORKDIRInstruction(OrderedInstruction):
    def __init__(self, path: str):
        self.path = path

    def __str__(self):
        return "WORKDIR " + self.path
