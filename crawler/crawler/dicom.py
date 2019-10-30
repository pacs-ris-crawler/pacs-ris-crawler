""" A simple regex based parser for DICOM (DCMTK output to be more precise). """
import re
from typing import List, Dict, Tuple

PATIENT_NAME = "PatientName"
PATIENT_BIRTHDATE = "PatientBirthDate"
PATIENT_ID = "PatientID"
PATIENT_SEX = "PatientSex"
STUDY_DATE = "StudyDate"
SERIES_DATE = "SeriesDate"
SERIES_TIME = "SeriesTime"
MODALITY = "Modality"
BODY_PART_EXAMINED = "BodyPartExamined"
STUDY_DESCRIPTION = "StudyDescription"
SERIES_DESCRIPTION = "SeriesDescription"
ACCESSION_NUMBER = "AccessionNumber"
STUDY_ID = "StudyID"
SERIES_NUMBER = "SeriesNumber"
INSTANCE_NUMBER = "InstanceNumber"
REFERRING_PHYSICIAN_NAME = "ReferringPhysicianName"
INSTANCE_AVAILABILITY = "InstanceAvailability"
INSTITUTION_NAME = "InstitutionName"
STUDY_INSTANCE_UID = "StudyInstanceUID"
SERIES_INSTANCE_UID = "SeriesInstanceUID"
SPECIFIC_CHARACTER_SET = "SpecificCharacterSet"
QUERY_RETRIEVE_LEVEL = "QueryRetrieveLevel"
RETRIEVE_AE_TITLE = "RetrieveAETitle"
STATION_NAME = "StationName"
PROTOCOL_NAME = "ProtocolName"

TAGS = {
    "(0010,0010)": PATIENT_NAME,
    "(0010,0030)": PATIENT_BIRTHDATE,
    "(0010,0020)": PATIENT_ID,
    "(0010,0040)": PATIENT_SEX,
    "(0008,0020)": STUDY_DATE,
    "(0008,0021)": SERIES_DATE,
    "(0008,0031)": SERIES_TIME,
    "(0008,0060)": MODALITY,
    "(0018,0015)": BODY_PART_EXAMINED,
    "(0008,1010)": STATION_NAME,
    "(0008,1030)": STUDY_DESCRIPTION,
    "(0008,103e)": SERIES_DESCRIPTION,
    "(0008,0050)": ACCESSION_NUMBER,
    "(0020,0010)": STUDY_ID,
    "(0020,0011)": SERIES_NUMBER,
    "(0020,0013)": INSTANCE_NUMBER,
    "(0008,0090)": REFERRING_PHYSICIAN_NAME,
    "(0008,0056)": INSTANCE_AVAILABILITY,
    "(0008,0080)": INSTITUTION_NAME,
    "(0018,1030)": PROTOCOL_NAME,
    "(0020,000d)": STUDY_INSTANCE_UID,
    "(0020,000e)": SERIES_INSTANCE_UID,
    "(0008,0005)": SPECIFIC_CHARACTER_SET,
    "(0008,0052)": QUERY_RETRIEVE_LEVEL,
    "(0008,0054)": RETRIEVE_AE_TITLE,
}

START_OR_END = re.compile(r"^I:\s*$")


def get_results(strings: List[str]) -> List[Dict[str, str]]:
    """
    Get list of results found. A single result is a dictionary
    where the keys are the DICOM tags and the value is the DICOM value.
    :param strings: list of strings
    :return: list of results (result is a dictionary)
    """
    result = []
    single_result = {}
    for line in strings:
        if _is_valid(line):
            single_result[_get_tag(line)] = _get_value(line)
        if _is_start_or_end(line) and single_result:
            result.append(single_result.copy())
            single_result.clear()
    result.append(single_result.copy())
    return result[1:]


def _sanity_check(single_result: Dict[str, str]):
    """ Only return results which have a PatientID and a Accession Number"""
    return "PatientID" in single_result and "AccessionNumber" in single_result


def _is_start_or_end(line: str) -> bool:
    """ Returns True if it is the start or end of a DICOM header. """
    return line.startswith("I: ---------------------------") or line.startswith(
        "W: ---------------------------"
    )


def _is_valid(line: str) -> bool:
    return (
        line.startswith("I:")
        and "(" in line
        and ")" in line
        and "[" in line
        and "]" in line
    ) or (
        line.startswith("W:")
        and "(" in line
        and ")" in line
        and "[" in line
        and "]" in line
    )


def _get_tag_value(line: str) -> Tuple[str, str]:
    return _get_tag(line), _get_value(line)


def _get_tag(line: str) -> str:
    """
    Returns the resolved tag value of the line. It first gets the content
    between the first round brackets and then makes a lookup to get the
    tag value.
    For example on this line
        I: (0010,0040) CS [F ]
    tag value would be (0010,0040) and resolved would be 'Modality'.
    """
    return TAGS[line[3:14]]


def _get_value(line: str) -> str:
    """
    Returns the value of the line, which is everything between
    the first and last square bracket.
    :param line: a line of the Dicom file
    :return: value
    """
    start = line.find("[") + 1
    end = line.rfind("]")
    return line[start:end].strip(" \t\r\n\0")
