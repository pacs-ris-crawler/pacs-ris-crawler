"""Customize embedded rq-dashboard: compact layout and safe run-command display."""

from __future__ import annotations

import re
import shlex

from flask import current_app
from rq.job import Job
from rq.utils import get_call_string

_SECRET_KEY_PATTERN = re.compile(
    r"((?:'|\")(?:DICOMWEB_PASSWORD|DICOMWEB_TOKEN|DICOMWEB_USER|PASSWORD|TOKEN|SECRET)(?:'|\")"
    r"\s*:\s*(?:'|\")?)([^'\"}\s,]+)",
    re.IGNORECASE,
)
_URL_CREDENTIALS_PATTERN = re.compile(r"://([^:/@]+):([^@]+)@")


def redact_secrets(text: str) -> str:
    if not text:
        return text
    text = _SECRET_KEY_PATTERN.sub(r"\1***", text)
    text = _URL_CREDENTIALS_PATTERN.sub(r"://\1:***@", text)
    return text


def format_movescu_command(cmd) -> str:
    if isinstance(cmd, (list, tuple)):
        return shlex.join(str(x) for x in cmd)
    return str(cmd)


def format_dicomweb_job_command(config: dict, entry: dict, dir_name: str | None = None) -> str:
    base = (config.get("DICOMWEB_WADO_BASE_URL") or "").rstrip("/")
    study_uid = entry.get("study_uid", "")
    series_uid = entry.get("series_uid", "")
    accession_number = entry.get("accession_number", "")
    uri = f"{base}/studies/{study_uid}/series/{series_uid}"
    parts = [f"WADO-RS GET {uri}"]
    if accession_number:
        parts.insert(0, f"accession={accession_number}")
    if dir_name:
        parts.append(f"-> {dir_name}")
    return " | ".join(parts)


def _is_dicomweb_download_job(job: Job) -> bool:
    if not job.func_name:
        return False
    name = job.func_name
    return "download_series_entry" in name or name.endswith("_download_series_entry")


def _format_by_function_name(job: Job) -> str | None:
    name = job.func_name or ""
    if name.endswith("run_many") and len(job.args) >= 2:
        return f"Anonymize DICOM in {job.args[1]}"
    if "delete_dicom_cmd" in name and job.args:
        return f"Delete DICOM files in {job.args[0]}"
    if name.endswith(".run") and job.args and isinstance(job.args[0], (list, tuple)):
        return format_movescu_command(job.args[0])
    return None


def format_job_command(job: Job) -> str:
    meta = job.get_meta() or {}
    command = meta.get("command")
    if command:
        return redact_secrets(str(command))

    if _is_dicomweb_download_job(job) and len(job.args) >= 2:
        config, entry = job.args[0], job.args[1]
        dir_name = job.args[2] if len(job.args) > 2 else None
        if isinstance(config, dict) and isinstance(entry, dict):
            return format_dicomweb_job_command(config, entry, dir_name)

    by_name = _format_by_function_name(job)
    if by_name:
        return by_name

    call = get_call_string(job.func_name, job.args, job.kwargs, max_length=None)
    if call:
        return redact_secrets(call)
    return redact_secrets(job.description or "")


def patch_rq_dashboard() -> None:
    import rq_dashboard.web as rq_web

    original_serialize = rq_web.serialize_job

    def serialize_job(job: Job):
        data = original_serialize(job)
        data["call_string"] = format_job_command(job)
        return data

    rq_web.serialize_job = serialize_job

    original_job_info = rq_web.job_info
    while hasattr(original_job_info, "__wrapped__"):
        original_job_info = original_job_info.__wrapped__

    @rq_web.jsonify
    def job_info(instance_number: int, job_id: str):
        result = original_job_info(instance_number, job_id)
        job = Job.fetch(
            job_id,
            serializer=rq_web.config.serializer,
            connection=current_app.redis_conn,
        )
        result["call_string"] = format_job_command(job)
        return result

    rq_web.job_info = job_info
