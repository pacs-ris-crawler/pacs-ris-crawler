import subprocess
from subprocess import PIPE


def run(cmd):
    completed = subprocess.run(cmd, stderr=subprocess.STDOUT, shell=False)
    return completed.returncode, completed.stdout

