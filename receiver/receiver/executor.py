import glob
import os
import shlex
import subprocess
from subprocess import PIPE

from receiver.config import dcmtk_config

TAGS_TO_DELETE = [
    "(0010,0010)",  # Name
    "(0010,1001)",  # Other Patient Names
    "(0010,0020)",  # ID
    "(0010,0030)",  # Birthdate
    "(0010,1010)",  # Age
    "(0010,1020)",  # Size
    "(0010,1030)",  # Weight
    "(0010,1040)",  # Patient Address
    "(0008,0080)",  # Institution Name
    "(0008,0081)",  # Institution Address
    "(0008,0090)",  # Referring Physician
    "(0008,0094)",  # Referring Physician's Telephone numbers
    "(0008,1070)",  # Operator Name
    "(0010,1000)",  # Other Patient IDs
    "(0008,0092)",  # Referring Physician's Address
    "(0038,0010)",  # Admission ID
]

DELETE_TAGS_CMD = "".join([f' -ea "{tag}"' for tag in TAGS_TO_DELETE])


def run(cmd):
    completed = subprocess.run(cmd, stderr=subprocess.STDOUT, shell=False)
    return completed.returncode, completed.stdout


def create_dicom_anonymize_cmds(config, image_folder):
    dcmtk = dcmtk_config(config)
    dcmodify_cmd = dcmtk.dcmtk_bin + "/dcmodify -q -ie -gin -nb "
    files = glob.glob(os.path.join(image_folder, "*"))
    file_cmds = [f"{dcmodify_cmd} {DELETE_TAGS_CMD} {filename}" for filename in files]
    return file_cmds


def run_many(config, image_folder):
    cmds = create_dicom_anonymize_cmds(config, image_folder)
    for cmd in cmds:
        # We are not checking for errors because dcmodify complains if some
        # tags are not present
        subprocess.run(shlex.split(cmd), stderr=subprocess.STDOUT, shell=False)
