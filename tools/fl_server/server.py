"""A mock federated-learning server.

This is the aggregator side of the FL story and knows nothing about PDO: to it, a
job is a script plus an opaque capability package, and a result is whatever
metrics a client reports back. It exists so the inference flow has a realistic
shape -- the requester hands work to an FL server, and the FL client sitting
beside the data pulls that work down -- without a real FL framework in the way.

Jobs live in memory and are handed to clients in submission order.

| Method | Path                    | Body / query                       | Returns                        |
|--------|-------------------------|------------------------------------|--------------------------------|
| GET    | `/info`                 |                                    | `{service, jobs}`              |
| POST   | `/jobs`                 | `{script, capability, ...}`        | `{job_id, status}`             |
| GET    | `/jobs/next`            | `?client_id=`                      | `{job}` or `{job: null}`       |
| POST   | `/jobs/<id>/metrics`    | `{metrics}` or `{error}`           | `{job_id, status}`             |
| GET    | `/jobs/<id>`            |                                    | the job record, without script |
"""

import argparse
import json
import logging
import threading
import uuid
from collections import OrderedDict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

SERVICE_NAME = "fl_server"

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETE = "complete"
STATUS_FAILED = "failed"


class JobStore:
    """In-memory job queue, FIFO across all clients.

    A job moves pending -> running when a client claims it, then to complete or
    failed when that client reports back. Nothing is retried and nothing expires:
    a client that claims a job and dies leaves it running forever, which is
    acceptable for a demo and would not be for anything else.
    """

    def __init__(self):
        self._jobs = OrderedDict()
        self._lock = threading.Lock()

    def submit(self, *, script, capability, script_name=None, asset_did=None):
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": STATUS_PENDING,
                "script": script,
                "capability": capability,
                "script_name": script_name,
                "asset_did": asset_did,
                "client_id": None,
                "metrics": None,
                "error": None,
            }
        logger.info("job %s submitted (%s)", job_id, script_name or "unnamed script")
        return job_id

    def claim_next(self, client_id):
        """Hand the oldest pending job to a client, or return ``None``."""
        with self._lock:
            for job in self._jobs.values():
                if job["status"] == STATUS_PENDING:
                    job["status"] = STATUS_RUNNING
                    job["client_id"] = client_id
                    logger.info("job %s claimed by %s", job["job_id"], client_id)
                    return {
                        "job_id": job["job_id"],
                        "script": job["script"],
                        "capability": job["capability"],
                        "script_name": job["script_name"],
                        "asset_did": job["asset_did"],
                    }
        return None

    def report(self, job_id, *, metrics=None, error=None):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if error is not None:
                job["status"] = STATUS_FAILED
                job["error"] = error
            else:
                job["status"] = STATUS_COMPLETE
                job["metrics"] = metrics
            logger.info("job %s reported %s", job_id, job["status"])
            return job

    def get(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            # the script and the capability are the client's to see, not the
            # submitter's to re-read; a status poll returns neither
            return {k: v for k, v in job.items() if k not in ("script", "capability")}

    def count(self):
        with self._lock:
            return len(self._jobs)


class FLServerHandler(BaseHTTPRequestHandler):
    server_version = f"{SERVICE_NAME}/0.1"

    # -----------------------------------------------------------------
    def do_GET(self):
        url = urlparse(self.path)
        path = url.path.rstrip("/") or "/"

        if path == "/info":
            self._respond({"service": SERVICE_NAME, "jobs": self.server.jobs.count()})
        elif path == "/jobs/next":
            client_id = (parse_qs(url.query).get("client_id") or [""])[0]
            if not client_id:
                self._respond({"error": "client_id is required"}, HTTPStatus.BAD_REQUEST)
                return
            self._respond({"job": self.server.jobs.claim_next(client_id)})
        elif path.startswith("/jobs/"):
            job = self.server.jobs.get(path[len("/jobs/") :])
            if job is None:
                self._respond({"error": "unknown job"}, HTTPStatus.NOT_FOUND)
            else:
                self._respond(job)
        else:
            self._respond({"error": f"unknown path: {path}"}, HTTPStatus.NOT_FOUND)

    # -----------------------------------------------------------------
    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"

        body = self._read_json()
        if body is None:
            self._respond({"error": "invalid JSON body"}, HTTPStatus.BAD_REQUEST)
            return

        if path == "/jobs":
            self._submit_job(body)
        elif path.startswith("/jobs/") and path.endswith("/metrics"):
            job_id = path[len("/jobs/") : -len("/metrics")]
            self._report_job(job_id, body)
        else:
            self._respond({"error": f"unknown path: {path}"}, HTTPStatus.NOT_FOUND)

    # -----------------------------------------------------------------
    def _submit_job(self, body):
        script = body.get("script")
        capability = body.get("capability")
        if not isinstance(script, str) or not script.strip():
            self._respond({"error": "'script' must be a non-empty string"}, HTTPStatus.BAD_REQUEST)
            return
        if not isinstance(capability, dict) or not capability:
            self._respond({"error": "'capability' must be an object"}, HTTPStatus.BAD_REQUEST)
            return

        job_id = self.server.jobs.submit(
            script=script,
            capability=capability,
            script_name=body.get("script_name"),
            asset_did=body.get("asset_did"),
        )
        self._respond({"job_id": job_id, "status": STATUS_PENDING}, HTTPStatus.CREATED)

    def _report_job(self, job_id, body):
        error = body.get("error")
        metrics = body.get("metrics")
        if error is None and not isinstance(metrics, dict):
            self._respond(
                {"error": "one of 'metrics' (object) or 'error' is required"},
                HTTPStatus.BAD_REQUEST,
            )
            return

        job = self.server.jobs.report(job_id, metrics=metrics, error=error)
        if job is None:
            self._respond({"error": "unknown job"}, HTTPStatus.NOT_FOUND)
        else:
            self._respond({"job_id": job_id, "status": job["status"]})

    # -----------------------------------------------------------------
    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return None
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _respond(self, body, status=HTTPStatus.OK):
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        logger.info("%s - %s", self.address_string(), format % args)


def serve(interface, port):
    httpd = ThreadingHTTPServer((interface, port), FLServerHandler)
    httpd.jobs = JobStore()
    logger.info("%s listening on %s:%d", SERVICE_NAME, interface, port)
    httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Run the mock FL server.")
    parser.add_argument(
        "-n", "--interface", default="0.0.0.0", help="interface to bind (default: 0.0.0.0)"
    )
    parser.add_argument("-p", "--port", type=int, default=7920, help="port to bind (default: 7920)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    serve(args.interface, args.port)


if __name__ == "__main__":
    main()
