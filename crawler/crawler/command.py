from datetime import date, datetime
from typing import Tuple, List

from crawler.config import pacs_settings


INITIAL_TIME_RANGE = "000000-235959"


def modalities(configuration) ->List[str]:
    return configuration["MODALITIES"]


def study_uid_query(configuration, accession_number):
    """It is not possible to query by accession number therefore we need
    to first fetch the studyinstanceuid.
    """
    return """findscu -to 6000 -v -S -k 0008,0052=STUDY {}
           -k StudyInstanceUID
           -k AccessionNumber={}""".format(
        pacs_settings(configuration), accession_number
    )


def basic_query(configuration):
    """Returns a basic findscu command with no query parameters set."""
    return """findscu -to 6000 -v -S -k 0008,0052=SERIES {}
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
           -k InstanceNumber
           -k ReferringPhysicianName
           -k InstitutionName
           -k StationName
           -k ProtocolName
           -k StudyInstanceUID
           -k SeriesInstanceUID
           -k SeriesDate
           -k SeriesTime""".format(
        pacs_settings(configuration)
    )


def add_modality(query, modality):
    """ Adds the modality to the query. """
    return query + " -k Modality=" + modality


def add_day(query, day):
    """ Adds the StudyDate and SeriesDate to the query. """
    q_day = day.strftime("%Y%m%d")
    return query + " -k StudyDate=" + q_day + " -k SeriesDate=" + q_day


def add_time(query, time):
    """ Adds the Series time to the query. """
    return query + " -k SeriesTime=" + time


def add_study_uid(query, study_uid):
    """ Limit by Accession Number with StudyInstanceUID """
    return query + " -k StudyInstanceUID=" + study_uid


def add_study_description(query, study_description):
    """ Search only for specific  study descriptions """
    return query + " -k StudyDescription=" + study_description


def add_day_range(query, from_day, to_day):
    """ Limit by a day range """
    return query + " -k StudyDate=" + from_day + "-" + to_day


def year_start_end(year):
    # type: (str) -> Tuple[date, date]
    y = datetime.strptime(year, "%Y")
    start = date(y.year, 1, 1)
    end = date(y.year, 12, 31)
    return start, end
