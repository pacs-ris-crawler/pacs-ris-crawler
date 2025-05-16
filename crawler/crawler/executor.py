import shlex
import subprocess
import structlog

from typing import List, Dict, Tuple
from crawler.dicom import get_results, DicomQueryError

log = structlog.get_logger()

def run(query: str, parse_results=True) ->Tuple[List[Dict[str, str]], int]:
    """
    Executes a findscu query and parses the result
    :param query: findscu query
    :return: a tuple where the first value is a list of DICOM tags and values
    and second value is result size
    """
    log.debug("Running query", query=query)
    cmd = shlex.split(query)
    # do not check=True because if segfaults with the current version of dcmtk 3.6.4 and ubuntu 20.04!!!
    completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderr = completed.stderr.decode('latin1')
    if "UnableToProcess" in stderr:
        raise DicomQueryError("Query failed at DICOM level")
    lines = stderr.splitlines()

    result = ""
    if parse_results:
        result = get_results(lines)
    return result, len(result)
