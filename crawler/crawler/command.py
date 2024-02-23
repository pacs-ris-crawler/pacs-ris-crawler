from datetime import date, datetime
from typing import Tuple

from crawler.config import pacs_settings


def study_uid_query(configuration, accession_number):
    """It is not possible to query by accession number therefore we need
    to first fetch the studyinstanceuid.
    """
    return f"""findscu -to 60 -S -k 0008,0052=STUDY {pacs_settings(configuration)}
           -k StudyInstanceUID
           -k AccessionNumber={accession_number}"""
    


def accs_per_day(configuration, day, time):
    """
    Query for all studyinstanceuids for a given day.
    """
    return f"""findscu -to 60 -S -k 0008,0052=STUDY {pacs_settings(configuration)}
           -k AccessionNumber
           -k StudyDate={day}
           -k StudyTime={time}"""


def basic_query(configuration):
    """Returns a basic findscu command with no query parameters set."""
    return f"""findscu -to 60 -S -k 0008,0052=SERIES {pacs_settings(configuration)}
           -k PatientName
           -k PatientBirthDate
           -k PatientID
           -k PatientSex
           -k StudyID
           -k StudyDate
           -k Modality
           -k AccessionNumber
           -k BodyPartExamined
           -k StudyDescription
           -k SeriesDescription
           -k SeriesNumber
           -k ReferringPhysicianName
           -k InstitutionName
           -k StationName
           -k ProtocolName
           -k StudyInstanceUID
           -k SeriesInstanceUID
           -k SeriesDate
           -k SeriesTime"""


def prefetch_query(configuration, study_uid):
    """This is a hack to force sectra to get exams to the online storage that afterwards seriesdescription can be retrieved"""
    return f"""movescu -to 60 -S -k 0008,0052=SERIES {pacs_settings(configuration)} -k StudyInstanceUID={study_uid}"""


def add_modality(query, modality):
    """Adds the modality to the query."""
    return query + " -k Modality=" + modality


def add_day(query, day):
    """Adds the StudyDate and SeriesDate to the query."""
    q_day = day.strftime("%Y%m%d")
    return query + " -k StudyDate=" + q_day + " -k SeriesDate=" + q_day


def add_time(query, time):
    """Adds the Series time to the query."""
    return query + " -k SeriesTime=" + time


def add_study_uid(query, study_uid):
    """Limit by Accession Number with StudyInstanceUID"""
    return query + " -k StudyInstanceUID=" + study_uid


def add_study_description(query, study_description):
    """Search only for specific  study descriptions"""
    return query + " -k StudyDescription=" + study_description


def add_day_range(query, from_day, to_day):
    """Limit by a day range"""
    return query + " -k StudyDate=" + from_day + "-" + to_day


def year_start_end(year):
    # type: (str) -> Tuple[date, date]
    y = datetime.strptime(year, "%Y")
    start = date(y.year, 1, 1)
    end = date(y.year, 12, 31)
    return start, end
