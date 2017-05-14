import subprocess

def run(cmd):
    return subprocess.check_output(cmd, shell=True)
