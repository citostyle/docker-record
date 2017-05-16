
# these commands from the history should not be included in the Dockerfile
# list has to be extended, for now there are just common setup/maintenance commands
COMMAND_BLACKLIST = ['ls', 'cd', 'pwd', 'history', 'du', 'top', 'ps',
                     'exit', 'clear', 'git status', 'cat']

# Heuristic: these commands are likely to be "service"
DOCKER_CMD_WHITELIST = ['service', '/etc/init.d/']

# Heuristic: add files that were opened by an editor and correspond to docker diff
EDITOR_WHITELIST = ['nano', 'vim', 'emacs', 'joe']


def startswith(string, collection):
    for item in collection:
        if string.startswith(item):
            return True
    return False


def is_docker_cmd(command):
    return startswith(command, DOCKER_CMD_WHITELIST)


def is_editor(command):
    return startswith(command, EDITOR_WHITELIST)


def is_blacklisted(command):
    if not command.strip():
        return True

    return startswith(command, COMMAND_BLACKLIST)


def extract_path_from_editor_command(command):
    return command.split(' ')[1]
