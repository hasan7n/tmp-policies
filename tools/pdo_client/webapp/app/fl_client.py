"""HTTP client for the mock FL server (``tools/fl_server``).

Used server-side by the inference action runner: it submits a job (a script plus
the capability the policy authorized) and then waits for the FL client beside the
guardian to claim it, run it, and report metrics back.
"""

import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = ("complete", "failed")


def _url(path):
    return f"{settings.FL_SERVER_URL.rstrip('/')}{path}"


def submit_job(script, capability, *, script_name=None, asset_did=None):
    """Queue an inference job. Returns the job id."""
    payload = {
        "script": script,
        "capability": capability,
        "script_name": script_name,
        "asset_did": asset_did,
    }
    resp = requests.post(_url("/jobs"), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["job_id"]


def get_job(job_id):
    """Return a job's current record (status, metrics, error)."""
    resp = requests.get(_url(f"/jobs/{job_id}"), timeout=30)
    resp.raise_for_status()
    return resp.json()


def wait_for_job(job_id, *, timeout=180, interval=2):
    """Poll a job until it completes or fails, and return its record.

    Raises ``TimeoutError`` if no FL client has reported on it within ``timeout``
    seconds — the usual cause being that no client is polling this server.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = get_job(job_id)
        if job.get("status") in TERMINAL_STATUSES:
            return job
        time.sleep(interval)
    raise TimeoutError(
        f"No FL client reported on job {job_id} within {timeout}s; "
        "check that a client is polling the FL server."
    )
