import logging
import os
import shlex

from redis import Redis
from rq import Queue

from receiver.config import dcmtk_config, new_pacs, old_pacs, pacs_config
from receiver.executor import run, run_many

logger = logging.getLogger("job")


def transfer_old_pacs_command(dcmtk_config, target, study_uid, series_uid):
    """Constructs the first part of the transfer command to a PACS node."""
    return (
        dcmtk_config.dcmtk_bin
        + "/movescu -S "
        + old_pacs()
        + _transfer_old(dcmtk_config, target, study_uid, series_uid)
    )


def transfer_new_pacs_command(dcmtk_config, target, study_uid, series_uid):
    """Constructs the first part of the transfer command to a PACS node."""
    return (
        dcmtk_config.dcmtk_bin
        + "/movescu -S "
        + new_pacs()
        + _transfer_new(target, study_uid, series_uid)
    )

def _transfer_new(target, study_uid, series_uid):
    return " -aem {} -k StudyInstanceUID={} -k SeriesInstanceUID={}".format(
        target,
        study_uid,
        series_uid
    )

def _transfer_old(dcmtk_config, target, study_uid, series_uid):
    return " -aem {} -k StudyInstanceUID={} -k SeriesInstanceUID={} {}".format(
        target,
        study_uid,
        series_uid,
        dcmtk_config.dcmin,
    )


def transfer_series(config, series_list, target):
    dcmtk = dcmtk_config(config)
    pacs = pacs_config(config)
    for entry in series_list:
        study_uid = entry["study_uid"]
        series_uid = entry["series_uid"]
        accession_number = entry["accession_number"]
        # very dummy assumpution let's if this hold true for USB
        # because new data is only in the new pacs
        # and not all old data is on the new pacs
        if accession_number.startswith("3"):
            command = transfer_new_pacs_command(dcmtk, target, study_uid, series_uid)
        else:
            command = transfer_old_pacs_command(dcmtk, target, study_uid, series_uid)
        args = shlex.split(command)
        queue_transfer(args)
        logger.debug("Running transfer command %s", args)
    return len(series_list), command


def base_command(dcmtk_config, pacs_config):
    """Constructs the first part of a dcmtk command."""
    return (
        dcmtk_config.dcmtk_bin
        + "/movescu -S -k QueryRetrieveLevel=SERIES "
        + "-aet {} -aec {} {} {} +P {}".format(
            pacs_config.ae_title,
            pacs_config.ae_called,
            pacs_config.peer_address,
            pacs_config.peer_port,
            pacs_config.incoming_port,
        )
    )


def base_command_old_pacs(dcmtk_config):
    """Constructs the first part of a dcmtk command."""
    return (
        dcmtk_config.dcmtk_bin
        + "/movescu -S -k QueryRetrieveLevel=SERIES "
        + old_pacs()
    )


def base_command_new_pacs(dcmtk_config):
    """Constructs the first part of a dcmtk command."""
    return (
        dcmtk_config.dcmtk_bin
        + "/movescu -S +xv -k QueryRetrieveLevel=SERIES "
        + new_pacs()
    )


def download_series(config, series_list, dir_name, image_type, queue_prio):
    """Download the series. The folder structure is as follows:
    MAIN_DOWNLOAD_DIR / USER_DEFINED / PATIENTID / ACCESSION_NUMBER / SERIES_NUMER
    """
    output_dir = config["IMAGE_FOLDER"]
    dcmtk = dcmtk_config(config)
    for entry in series_list:
        image_folder = _create_image_dir(output_dir, entry, dir_name)
        study_uid = entry["study_uid"]
        accession_number = entry["accession_number"]
        series_uid = entry["series_uid"]
        if not all([study_uid, series_uid, accession_number]):
            print("Error missing either study_uid, series_uid or accession number")
            print("study_uid:", study_uid)
            print("series_uid:", series_uid)
            print("accession number:", accession_number)
            continue
        command = (
            base_command_new_pacs(dcmtk)
            + " --output-directory "
            + image_folder
            + " -k StudyInstanceUID="
            + study_uid
            + " -k SeriesInstanceUID="
            + series_uid
        )
        args = shlex.split(command)
        queue(args, config, image_folder, image_type, queue_prio)
        logger.debug("Running download command %s", args)
    return len(series_list)


def create_nifti_cmd(image_folder):
    nifti_output_dir = os.path.join(image_folder, "nifti")
    os.makedirs(nifti_output_dir, exist_ok=True)
    print("dcm2niix -f %i_%g_%s -z y -o " + nifti_output_dir + " " + image_folder)
    return shlex.split(
        "dcm2niix -f %i_%g_%s_%z -z y -o " + nifti_output_dir + " " + image_folder
    )


def delete_dicom_cmd(image_folder):
    for f in os.scandir(image_folder):
        if f.is_file():
            os.remove(f)


def queue_transfer(cmd):
    redis_conn = Redis()
    q = Queue(name="transfer", connection=redis_conn)
    j = q.enqueue(run, cmd)
    return


def queue(cmd, config, image_folder, image_type, queue_prio):
    redis_conn = Redis()
    if queue_prio == 'queue-high':
        q = Queue(name='high', connection=redis_conn)
    else:
        q = Queue(name='medium', connection=redis_conn)
    download_job = q.enqueue(run, cmd)
    if image_type == "nifti":
        nifti_job = q.enqueue(
            run, create_nifti_cmd(image_folder), depends_on=download_job
        )
        delete_dicom_job = q.enqueue(
            delete_dicom_cmd, image_folder, depends_on=nifti_job
        )
        return delete_dicom_job
    if image_type == "anon-dicom":
        dicom_anonymize_job = q.enqueue(
            run_many, config, image_folder, depends_on=download_job
        )
        return dicom_anonymize_job
    return download_job


def _create_image_dir(output_dir, entry, dir_name):
    patient_id = entry["patient_id"]
    accession_number = str(entry["accession_number"])
    series_number = str(entry["series_number"])
    image_folder = os.path.join(
        output_dir, dir_name, patient_id, accession_number, series_number
    )
    if not os.path.exists(image_folder):
        os.makedirs(image_folder, exist_ok=True)
    return image_folder
