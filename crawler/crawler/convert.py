""" This file contains the locic associated with the tasks
    in the file 'ris_pacs_merge_upload.py'
"""
from datetime import datetime

from requests import get
from requests.auth import HTTPBasicAuth
from tasks.util import load_config

from crawler.config import get_report_show_url


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
                and "StudyDate" in entry
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
            if "StudyDate" in entry:
                p_dict["StudyDate"] = entry["StudyDate"]
            if "StudyTime" in entry:
                p_dict["StudyTime"] = entry["StudyTime"]
            if "StudyDescription" in entry:
                p_dict["StudyDescription"] = entry["StudyDescription"]
            if "StudyID" in entry:
                p_dict["StudyID"] = entry["StudyID"]
            if "StationName" in entry:
                p_dict["StationName"] = entry["StationName"]
            if "ProtocolName" in entry and entry["ProtocolName"]:
                p_dict["ProtocolName"] = []
                p_dict["ProtocolName"].append(entry["ProtocolName"])
            p_dict["_childDocuments_"] = []
            p_dict = add_child(p_dict, entry)
            acc_dict[entry["AccessionNumber"]] = p_dict
        else:
            p_dict = acc_dict[entry["AccessionNumber"]]
            p_dict = add_child(p_dict, entry)

    # pos processing
    # all protocolnames (a list datatype) is concated to a single string
    # a dictionary with only keys (to filter out duplicates) is used 
    # https://stackoverflow.com/a/53657523
    values = list(acc_dict.values())
    for v in values:
        if "ProtocolName" in v:
            v["ProtocolName"] = ";".join(dict.fromkeys(v["ProtocolName"]).keys())
    return values


def add_child(parent, entry):
    """ add child entry """
    child_dict = {}
    child_dict["Category"] = "child"
    child_dict["Modality"] = entry["Modality"]
    child_dict["StudyInstanceUID"] = entry["StudyInstanceUID"]
    child_dict["SeriesInstanceUID"] = entry["SeriesInstanceUID"]
    child_dict["id"] = entry["SeriesInstanceUID"]
    if "SeriesDate" in entry:
        child_dict["SeriesDate"] = entry["SeriesDate"]
    if "SeriesTime" in entry:
        child_dict["SeriesTime"] = entry["SeriesTime"]
    if "BodyPartExamined" in entry:
        child_dict["BodyPartExamined"] = entry["BodyPartExamined"]
    if "SeriesDescription" in entry:
        child_dict["SeriesDescription"] = entry["SeriesDescription"]
    if "SeriesNumber" in entry:
        child_dict["SeriesNumber"] = entry["SeriesNumber"]
    # add protocolname to set
    if "ProtocolName" in entry and entry["ProtocolName"]:
        # if first series does not contain "ProtocolName" and e.g. second one does
        if "ProtocolName" not in parent:
            parent["ProtocolName"] = []
        parent["ProtocolName"].append(entry["ProtocolName"])
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
        dic = entry.copy()
        if not use_reports:
            dic["RisReport"] = ""
            my_dict.append(dic)
        elif "AccessionNumber" in entry:
            aNum = str(entry["AccessionNumber"])
            url = get_report_show_url(config) + aNum + "&output=text"
            if uses_basis_auth:
                response = get(url, auth=HTTPBasicAuth(user, pwd), verify=False)
            else:
                response = get(url, verify=False)
            response.raise_for_status()
            data = response.text
            dic["RisReport"] = data
            my_dict.append(dic)
    return my_dict
