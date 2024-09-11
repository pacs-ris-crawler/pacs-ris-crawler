import shlex
import subprocess
import logging

from typing import List, Dict, Tuple
from crawler.dicom import get_results

log = logging.getLogger("crawler.app")

def run(query: str, parse_results=True) ->Tuple[List[Dict[str, str]], int]:
    """
    Executes a findscu query and parses the result
    :param query: findscu query
    :return: a tuple where the first value is a list of DICOM tags and values
    and second value is result size
    """
    log.debug(query)
    cmd = shlex.split(query)
    completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = completed.stderr.decode('latin1').splitlines()
    result = ""
    if parse_results:
        result = get_results(lines)
    return result, len(result)
