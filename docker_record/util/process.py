import subprocess
from ..log import *

def execute(cmd):
    if type(cmd) == str:
        cmd = cmd.split(" ")
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out

def execute_shell(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    if err:
        log("EXECUTE SHELL: " + cmd + " -> " + str(err))
    else:
        log("EXECUTE SHELL: " + cmd)
    return out

def execute_lines(cmd):
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)
