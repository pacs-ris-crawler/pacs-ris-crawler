import logging
import os
import shlex
import subprocess
from rq import Queue
from redis import Redis

from mova.config import pacs_config, dcmtk_config
from mova.executor import run

logger = logging.getLogger('job')


def transfer_command(dcmkt_config, pacs_config, target, study_uid, series_uid):
    """ Constructs the first part of the transfer command to a PACS node. """
    return dcmkt_config.dcmtk_bin + '/movescu -v -S ' + _transfer(
        dcmkt_config, pacs_config, target, study_uid, series_uid)


def _transfer(dcmkt_config, pacs_config, target, study_uid, series_uid):
    return '-aem {} -aet {} -aec {} {} {} -k StudyInstanceUID={} -k SeriesInstanceUID={} {}'.format(
        target, pacs_config.ae_title, pacs_config.ae_called,
        pacs_config.peer_address, pacs_config.peer_port, study_uid, series_uid,
        dcmkt_config.dcmin)


def transfer_series(config, series_list, target):
    dcmtk = dcmtk_config(config)
    pacs = pacs_config(config)
    for entry in series_list:
        study_uid = entry['study_uid']
        series_uid = entry['series_uid']
        command = transfer_command(dcmtk, pacs, target, study_uid, series_uid)
        args = shlex.split(command)
        queue(args)
        logger.debug('Running transfer command %s', args)
    return len(series_list)


def base_command(dcmtk_config, pacs_config):
    """ Constructs the first part of a dcmtk command. """
    return dcmtk_config.dcmtk_bin \
               + '/movescu -v -S -k QueryRetrieveLevel=SERIES ' \
               + '-aet {} -aec {} {} {} +P {}'.format(pacs_config.ae_title, \
               pacs_config.ae_called, pacs_config.peer_address, \
               pacs_config.peer_port, pacs_config.incoming_port)


def download_series(config, series_list, dir_name):
    """ Download the series. The folder structure is as follows:
        MAIN_DOWNLOAD_DIR / USER_DEFINED / PATIENTID / ACCESSION_NUMBER /
          / SERIES_NUMER
    """
    output_dir = config['IMAGE_FOLDER']
    dcmtk = dcmtk_config(config)
    pacs = pacs_config(config)
    for entry in series_list:
        image_folder = _create_image_dir(output_dir, entry, dir_name)
        study_uid = entry['study_uid']
        series_uid = entry['series_uid']
        if not all([study_uid, series_uid]):
            print("Error missing either study_uid or series_uid")
            print("study_uid:", study_uid)
            print("series_uid:", series_uid)
            print("accession number:", entry.get('accession_number'))
            continue
        command = base_command(dcmtk, pacs) \
                  + ' --output-directory ' + image_folder \
                  + ' -k StudyInstanceUID=' + study_uid \
                  + ' -k SeriesInstanceUID=' + series_uid \
                  + ' ' + dcmtk.dcmin
        args = shlex.split(command)
        queue(args)
        logger.debug('Running download command %s', args)
    return len(series_list)


def queue(cmd):
    redis_conn = Redis()
    q = Queue(connection=redis_conn)  # no args implies the default queue
    j = q.enqueue(run, cmd)
    return j


def _create_image_dir(output_dir, entry, dir_name):
    patient_id = entry['patient_id']
    accession_number = str(entry['accession_number'])
    series_number = str(entry['series_number'])
    image_folder = os.path.join(output_dir, dir_name, patient_id,
                                accession_number, series_number)
    if not os.path.exists(image_folder):
        os.makedirs(image_folder, exist_ok=True)
    return image_folder
