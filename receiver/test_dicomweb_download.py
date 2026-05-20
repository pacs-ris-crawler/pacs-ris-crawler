"""Test script to download DICOM data via DICOMweb by accession number."""
import logging
import sys
import os

from flask import Flask

sys.path.insert(0, os.path.dirname(__file__))

from receiver.dicomweb import query_by_accession_number, _retrieve_series, _session, _wado_rs_base_url

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("test_dicomweb")

_CONFIG_KEYS = (
    "DICOMWEB_QIDO_BASE_URL",
    "DICOMWEB_WADO_BASE_URL",
    "DICOMWEB_TOKEN",
    "DICOMWEB_USER",
    "DICOMWEB_PASSWORD",
    "DICOMWEB_VERIFY_SSL",
    "DICOMWEB_MAX_WORKERS",
    "IMAGE_FOLDER",
)


def _load_config():
    app = Flask(
        __name__,
        instance_relative_config=True,
        instance_path=os.path.join(os.path.dirname(__file__), "instance"),
    )
    app.config.from_pyfile("config.cfg")
    config = {key: app.config[key] for key in _CONFIG_KEYS}
    for key in ("DICOMWEB_TOKEN", "DICOMWEB_USER", "DICOMWEB_PASSWORD"):
        if os.environ.get(key):
            config[key] = os.environ[key]
    return config


config = _load_config()

if not config.get("DICOMWEB_TOKEN") and not (
    config.get("DICOMWEB_USER") and config.get("DICOMWEB_PASSWORD")
):
    print(
        "Set DICOMWEB_TOKEN or DICOMWEB_USER/DICOMWEB_PASSWORD in "
        "instance/config.cfg (or via environment).",
        file=sys.stderr,
    )
    sys.exit(1)

accession_number = "30061576"

print(f"\n=== Querying for accession number {accession_number} ===\n")

try:
    series_list = query_by_accession_number(config, accession_number)
except Exception as e:
    logger.error("QIDO-RS query failed: %s", e)
    sys.exit(1)

if not series_list:
    print("No series found.")
    sys.exit(0)

print(f"Found {len(series_list)} series:")
for i, s in enumerate(series_list):
    print(f"  {i+1}. StudyUID={s['study_uid']}, SeriesUID={s['series_uid']}, "
          f"SeriesNumber={s['series_number']}, PatientID={s['patient_id']}")

print(f"\n=== Downloading all {len(series_list)} series ===\n")

base_url = _wado_rs_base_url(config)
session = _session(config)

total = 0
for s in series_list:
    output_dir = os.path.join(
        config["IMAGE_FOLDER"], "test_dicomweb",
        s["patient_id"], accession_number, str(s["series_number"]),
    )
    try:
        count = _retrieve_series(session, base_url, s["study_uid"], s["series_uid"], output_dir)
        total += count
        print(f"  Series {s['series_number']}: {count} instances -> {output_dir}")
    except Exception as e:
        logger.error("Failed series %s: %s", s["series_uid"], e)

print(f"\n=== Done. Total instances downloaded: {total} ===")
