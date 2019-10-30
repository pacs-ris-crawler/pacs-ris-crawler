import shlex
import subprocess

from typing import List, Dict, Tuple
from crawler.dicom import get_results


def run(query: str) ->Tuple[List[Dict[str, str]], int]:
    """
    Executes a findscu query and parses the result
    :param query: findscu query
    :return: a tuple where the first value is a list of DICOM tags and values
    and second value is result size
    """
    cmd = shlex.split(query)
    completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = completed.stderr.decode('latin1').splitlines()
    result = get_results(lines)
    return result, len(result)
