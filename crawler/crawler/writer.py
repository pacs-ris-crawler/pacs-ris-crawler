import logging
import os
import pandas as pd

from typing import List, Dict

OUTPUT_DIR = 'data'


def _get_file_name(month: str, day: str, mod: str) -> str:
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    file_name = os.path.join(OUTPUT_DIR, 'data-')
    if month:
        return file_name + month + '.json'
    else:
        return file_name + day + '-' + mod + '.json'


def write_results(results: List[Dict[str, str]], month: str, day: str, mod: str) -> str:
    filename = _get_file_name(month, day, mod)
    frames = pd.concat([pd.DataFrame(x) for x in results if len(x) > 0])
    frames.to_json(filename, orient='records')
    return filename


def write_file(results: List[Dict[str, str]], filename: str) -> str:
    frames = pd.concat([pd.DataFrame(x) for x in results if len(x) > 0])
    frames.to_json(filename, orient='records')
    return filename
