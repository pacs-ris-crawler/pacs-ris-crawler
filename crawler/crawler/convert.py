""" This file contains the locic associated with the tasks
    in the file 'ris_pacs_merge_upload.py'
"""
from datetime import date, datetime

from requests import get
from requests.auth import HTTPBasicAuth

from crawler.config import get_report_show_url
from tasks.util import load_config


def convert_pacs_file(json_in):
    """ Convert: pacs_date.json -> pacs_convert_date.json
        The converted file contains only one entry per accession number
        structured into one parent and one child for each series
    """
    acc_dict = {}
    for entry in json_in:
        if entry["AccessionNumber"] not in acc_dict:
            p_dict = {}
            p_dict["Category"] = "parent"
            if entry["AccessionNumber"] and entry["PatientID"]:
                p_dict["AccessionNumber"] = entry["AccessionNumber"]
                p_dict["PatientID"] = entry["PatientID"]
                p_dict["id"] = entry["PatientID"] + "-" + entry["AccessionNumber"]
            if "InstitutionName" in entry:
                p_dict["InstitutionName"] = entry["InstitutionName"]
            if (
                "PatientBirthDate" in entry
                and "SeriesDate" in entry
                and entry["PatientBirthDate"] is not None
            ):
                patient_birthdate = entry["PatientBirthDate"]
                p_dict["PatientBirthDate"] = patient_birthdate
                today = datetime.strptime(entry["StudyDate"], "%Y%m%d")
                birthdate = datetime.strptime(patient_birthdate, "%Y%m%d")
                p_dict["PatientAge"] = (
                    today.year
                    - birthdate.year
                    - ((today.month, today.day) < (birthdate.month, birthdate.day))
                )
            if "PatientName" in entry:
                p_dict["PatientName"] = entry["PatientName"]
            if "PatientSex" in entry:
                p_dict["PatientSex"] = entry["PatientSex"]
            if "ReferringPhysicianName" in entry:
                p_dict["ReferringPhysicianName"] = entry["ReferringPhysicianName"]
            if "SeriesDate" in entry:
                p_dict["SeriesDate"] = entry["SeriesDate"]
            p_dict["StudyDate"] = entry["StudyDate"]
            if entry["StudyDescription"]:
                p_dict["StudyDescription"] = entry["StudyDescription"]
            if "StudyID" in entry:
                p_dict["StudyID"] = entry["StudyID"]
            if "StationName" in entry:
                p_dict["StationName"] = entry["StationName"]
            p_dict["_childDocuments_"] = []
            p_dict = add_child(p_dict, entry)
            acc_dict[entry["AccessionNumber"]] = p_dict
        else:
            p_dict = acc_dict[entry["AccessionNumber"]]
            p_dict = add_child(p_dict, entry)

    return list(acc_dict.values())


def add_child(parent, entry):
    """ add child entry """
    child_dict = {}
    child_dict["Category"] = "child"
    child_dict["Modality"] = entry["Modality"]
    child_dict["StudyInstanceUID"] = entry["StudyInstanceUID"]
    child_dict["SeriesInstanceUID"] = entry["SeriesInstanceUID"]
    child_dict["id"] = entry["SeriesInstanceUID"]
    if "SeriesTime" in entry:
        child_dict["SeriesTime"] = entry["SeriesTime"]
    if "BodyPartExamined" in entry:
        child_dict["BodyPartExamined"] = entry["BodyPartExamined"]
    if "SeriesDescription" in entry:
        child_dict["SeriesDescription"] = entry["SeriesDescription"]
    if "SeriesNumber" in entry:
        child_dict["SeriesNumber"] = entry["SeriesNumber"]
    if "ProtocolName" in entry:
        child_dict["ProtocolName"] = entry["ProtocolName"]
    parent["_childDocuments_"].append(child_dict)
    return parent


def merge_pacs_ris(pacs):
    """ Insert ris report into converted pacs json file"""
    config = load_config()
    uses_basis_auth = bool(config["REPORT_USES_BASIC_AUTH"])
    use_reports = bool(config["REPORT_USE"])
    user = config["REPORT_USER"]
    pwd = config["REPORT_PWD"]
    my_dict = []
    for entry in pacs:
        dic = {}
        dic = entry
        if not use_reports:
            dic["RisReport"] = ""
            my_dict.append(dic)
            return my_dict
        elif "AccessionNumber" in entry:
            aNum = str(entry["AccessionNumber"])
            url = get_report_show_url(config) + aNum + "&output=text"
            response = get(url, auth=HTTPBasicAuth(user, pwd))
            data = response.text
            dic["RisReport"] = data
            my_dict.append(dic)
    return my_dict
