"""DICOMweb WADO-RS retrieval with parallel downloads.

This module provides an alternative to movescu for retrieving
DICOM data from a PACS that supports DICOMweb (WADO-RS).
"""

import logging
import os
import sys
from pathlib import Path

import requests
from redis import Redis
from rq import Queue

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.rq_dashboard_custom import format_dicomweb_job_command

logger = logging.getLogger("dicomweb")


def query_by_accession_number(config, accession_number):
    """Use QIDO-RS to find studies/series for a given accession number.

    Returns a list of dicts with study_uid, series_uid, series_number,
    patient_id, and accession_number.
    """
    qido_url = _qido_rs_base_url(config)
    session = _session(config)
    session.headers["Accept"] = "application/dicom+json"

    query_templates = [
        "/mrnissuers/all/series/?AccessionNumber={}",
        "/series?AccessionNumber={}",
        "/studies?AccessionNumber={}",
        "/series?AccessionNumber={}&includefield=all",
    ]
    all_series = None
    last_error = None
    for template in query_templates:
        url = f"{qido_url}{template.format(accession_number)}"
        logger.debug("QIDO-RS query attempt: %s", url)
        try:
            resp = session.get(url)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            all_series = resp.json()
            if all_series:
                break
        except Exception as exc:
            last_error = exc
            logger.debug("QIDO-RS query failed for %s: %s", url, exc)
            continue

    if all_series is None:
        logger.error("QIDO-RS query failed for accession number %s", accession_number)
        if last_error:
            raise last_error
        return []

    if not all_series:
        logger.warning("No series found for accession number %s", accession_number)
        return []

    series_list = []
    for s in all_series:
        study_uid = _tag_value(s, "0020000D")
        series_uid = _tag_value(s, "0020000E")
        patient_id = _tag_value(s, "00100020")
        series_number = _tag_value(s, "00200011") or "0"
        series_list.append({
            "study_uid": study_uid,
            "series_uid": series_uid,
            "series_number": series_number,
            "patient_id": patient_id,
            "accession_number": accession_number,
        })

    study_uids = {s["study_uid"] for s in series_list}
    logger.info(
        "Found %d series in %d studies for accession %s",
        len(series_list), len(study_uids), accession_number,
    )
    return series_list


def _tag_value(dataset, tag):
    """Extract the first value from a DICOM JSON tag entry."""
    entry = dataset.get(tag, {})
    value = entry.get("Value", [])
    if value:
        return str(value[0])
    return ""


def _validate_dicomweb_config(config):
    """Ensure WADO-RS settings are present when using DICOMweb retrieval."""
    wado_url = (config.get("DICOMWEB_WADO_BASE_URL") or "").strip()
    if not wado_url:
        raise ValueError(
            "DICOMWEB_WADO_BASE_URL must be set in config when RETRIEVE_METHOD='dicomweb'",
        )
    token = config.get("DICOMWEB_TOKEN")
    user = config.get("DICOMWEB_USER")
    password = config.get("DICOMWEB_PASSWORD")
    if not token and not (user and password):
        raise ValueError(
            "DICOMWEB_TOKEN or DICOMWEB_USER/DICOMWEB_PASSWORD must be set "
            "when RETRIEVE_METHOD='dicomweb'",
        )


def _image_folder_path(config, entry, dir_name):
    """Same layout as job.download_series: IMAGE_FOLDER/dir/patient/accession/series."""
    from receiver.job import image_subdir

    output_dir = config["IMAGE_FOLDER"]
    patient_id = entry.get("patient_id", "")
    accession_number = str(entry.get("accession_number", ""))
    series_number = image_subdir(entry)
    return os.path.join(
        output_dir, dir_name, patient_id, accession_number, series_number,
    )


def _qido_rs_base_url(config):
    return config["DICOMWEB_QIDO_BASE_URL"].rstrip("/")


def _wado_rs_base_url(config):
    return config["DICOMWEB_WADO_BASE_URL"].rstrip("/")


def _session(config):
    session = requests.Session()
    token = config.get("DICOMWEB_TOKEN")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    user = config.get("DICOMWEB_USER")
    password = config.get("DICOMWEB_PASSWORD")
    if user and password:
        session.auth = (user, password)
    session.headers["Accept"] = "application/dicom"
    verify = config.get("DICOMWEB_VERIFY_SSL", True)
    session.verify = verify
    return session


def _retrieve_instance(session, base_url, study_uid, series_uid, sop_uid, output_dir):
    """Retrieve one SOP instance via WADO-RS."""
    attempted_urls = []
    for endpoint in [
        f"{base_url}/mrnissuers/all/studies/{study_uid}/series/{series_uid}/instances/{sop_uid}",
        f"{base_url}/studies/{study_uid}/series/{series_uid}/instances/{sop_uid}",
    ]:
        attempted_urls.append(endpoint)
        logger.debug("WADO-RS instance retrieve attempt: %s", endpoint)
        resp = session.get(endpoint, headers={"Accept": "application/dicom"}, stream=True)
        if resp.status_code == 404:
            logger.debug("WADO-RS instance endpoint returned 404: %s", endpoint)
            continue
        resp.raise_for_status()
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.join(output_dir, "000000.dcm")
        with open(filename, "wb") as f:
            f.write(resp.content)
        logger.info(
            "Retrieved 1 instance %s for series %s (study %s)",
            sop_uid, series_uid, study_uid,
        )
        return 1
    raise ValueError(
        "Failed to retrieve DICOM instance with any WADO-RS endpoint. "
        f"Attempted urls: {attempted_urls}",
    )


def _retrieve_series(session, base_url, study_uid, series_uid, output_dir):
    """Retrieve all instances of a series via WADO-RS and write .dcm files."""
    attempted_urls = []
    for endpoint in [
        # Sectra PACS uses /mrnissuers/all/ prefix (same as QIDO-RS)
        f"{base_url}/mrnissuers/all/studies/{study_uid}/series/{series_uid}",
        f"{base_url}/mrnissuers/all/studies/{study_uid}/series/{series_uid}/instances",
        f"{base_url}/studies/{study_uid}/series/{series_uid}",
        f"{base_url}/studies/{study_uid}/series/{series_uid}/instances",
    ]:
        attempted_urls.append(endpoint)
        logger.debug("WADO-RS retrieve attempt: %s", endpoint)
        resp = session.get(
            endpoint,
            headers={"Accept": "multipart/related; type=\"application/dicom\""},
            stream=True,
        )
        if resp.status_code == 404:
            logger.debug("WADO-RS endpoint returned 404: %s", endpoint)
            continue
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        boundary = _parse_boundary(content_type)

        os.makedirs(output_dir, exist_ok=True)
        if boundary is None:
            if "application/dicom" in content_type or "application/octet-stream" in content_type:
                filename = os.path.join(output_dir, "000000.dcm")
                with open(filename, "wb") as f:
                    f.write(resp.content)
                logger.info(
                    "Retrieved 1 instance for series %s (study %s) as single DICOM response",
                    series_uid, study_uid,
                )
                return 1
            raise ValueError(f"Could not parse boundary from Content-Type: {content_type}")

        count = _save_multipart_dicom(resp.content, boundary, output_dir)
        logger.info(
            "Retrieved %d instances for series %s (study %s)",
            count, series_uid, study_uid,
        )
        return count

    raise ValueError(
        "Failed to retrieve DICOM series with any WADO-RS endpoint. "
        f"Attempted urls: {attempted_urls}",
    )


def _parse_boundary(content_type):
    for part in content_type.split(";"):
        part = part.strip()
        if part.startswith("boundary="):
            boundary = part[len("boundary="):]
            return boundary.strip('"')
    return None


def _save_multipart_dicom(data, boundary, output_dir):
    boundary_bytes = boundary.encode() if isinstance(boundary, str) else boundary
    sep = b"--" + boundary_bytes
    parts = data.split(sep)
    count = 0
    for part in parts:
        part = part.strip()
        if not part or part == b"--":
            continue
        idx = part.find(b"\r\n\r\n")
        if idx == -1:
            continue
        body = part[idx + 4:]
        if body.endswith(b"\r\n"):
            body = body[:-2]
        if len(body) < 132:
            continue
        filename = os.path.join(output_dir, f"{count:06d}.dcm")
        with open(filename, "wb") as f:
            f.write(body)
        count += 1
    return count


def _download_series_entry(config, entry, dir_name):
    """Download one series (RQ worker). Uses a dedicated session per job."""
    study_uid = entry["study_uid"]
    series_uid = entry["series_uid"]
    sop_uid = (entry.get("sop_instance_uid") or "").strip()
    accession_number = entry.get("accession_number")
    if not all([study_uid, series_uid, accession_number]):
        raise ValueError(
            f"Missing study_uid, series_uid, or accession_number: {entry}",
        )
    image_folder = _image_folder_path(config, entry, dir_name)
    session = _session(config)
    base_url = _wado_rs_base_url(config)
    if sop_uid:
        count = _retrieve_instance(
            session, base_url, study_uid, series_uid, sop_uid, image_folder,
        )
    else:
        count = _retrieve_series(session, base_url, study_uid, series_uid, image_folder)
    logger.info(
        "Downloaded %d instances for series %s (accession %s)",
        count, series_uid, accession_number,
    )
    return count


def _queue_dicomweb_download(config, entry, dir_name, image_type, queue_prio):
    """Enqueue a DICOMweb series download and optional post-processing (like movescu)."""
    from receiver.executor import run, run_many
    from receiver.job import create_nifti_cmd, delete_dicom_cmd

    redis_conn = Redis()
    if queue_prio == "queue-high":
        q = Queue(name="high", connection=redis_conn)
    else:
        q = Queue(name="medium", connection=redis_conn)

    accession_number = entry.get("accession_number", "")
    series_uid = entry["series_uid"]
    image_folder = _image_folder_path(config, entry, dir_name)

    download_job = q.enqueue(
        _download_series_entry,
        config,
        entry,
        dir_name,
        job_timeout="30m",
        description=(
            f"AccessionNr: {accession_number} / SeriesInstanceUID: {series_uid} (DICOMweb)"
        ),
        meta={"command": format_dicomweb_job_command(config, entry, dir_name)},
    )
    if image_type == "nifti":
        nifti_job = q.enqueue(
            run, create_nifti_cmd(image_folder), depends_on=download_job,
        )
        q.enqueue(delete_dicom_cmd, image_folder, depends_on=nifti_job)
    elif image_type == "anon-dicom":
        q.enqueue(run_many, config, image_folder, depends_on=download_job)
    return download_job


def download_series_dicomweb(config, series_list, dir_name, image_type, queue_prio):
    """Download series via DICOMweb WADO-RS.

    Drop-in replacement for job.download_series: enqueues one RQ job per series.
    """
    _validate_dicomweb_config(config)
    for entry in series_list:
        study_uid = entry.get("study_uid")
        series_uid = entry.get("series_uid")
        accession_number = entry.get("accession_number")
        if not all([study_uid, series_uid, accession_number]):
            logger.error(
                "Missing study_uid, series_uid, or accession_number: %s", entry,
            )
            continue
        _queue_dicomweb_download(config, entry, dir_name, image_type, queue_prio)
        logger.debug(
            "Queued DICOMweb download for series %s (accession %s)",
            series_uid, accession_number,
        )
    return len(series_list)


def download_series_debug_dicomweb(config, study_uid, series_uid, dir_name):
    """Debug download of a single series via DICOMweb. Returns (count, output)."""
    _validate_dicomweb_config(config)
    output_dir = config["IMAGE_FOLDER"]
    base_url = _wado_rs_base_url(config)
    session = _session(config)
    image_folder = os.path.join(output_dir, dir_name)
    os.makedirs(image_folder, exist_ok=True)
    try:
        count = _retrieve_series(session, base_url, study_uid, series_uid, image_folder)
        return 0, f"Retrieved {count} instances to {image_folder}"
    except Exception as exc:
        logger.exception("DICOMweb debug download failed")
        return 1, str(exc)


def transfer_series_dicomweb(config, target, series_list):
    """Transfer is not supported via DICOMweb — falls back to movescu."""
    raise NotImplementedError(
        "DICOMweb transfer (STOW-RS) is not implemented. "
        "Use RETRIEVE_METHOD = 'movescu' for transfer operations."
    )
