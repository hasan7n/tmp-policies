"""A mock federated-learning client, running beside the guardian core.

This stands in for the FL framework a data holder would run inside their own
environment. It never listens for work: it polls an FL server, and each job it
gets back carries the script to run together with the capability package
authorizing that run.

The client is the party that turns a claim about code into a fact about code. It
hashes the script it actually holds and presents that digest with the capability
to the guardian core over localhost; the guardian core releases the data only
when the digest matches the one the capability authorizes. Everything after that
is simulated -- the client prints what it would run and reports fixed metrics.

The client deliberately depends on nothing from PDO. A real FL framework would
not be a PDO component either; all it has to know is how to POST a capability
package to a guardian.
"""

import hashlib
import logging
import time

import requests

logger = logging.getLogger(__name__)

DIGEST_PREFIX = "sha256:"


def script_digest(script):
    """Return the digest naming a script, in the form the policy records.

    The prefix names the algorithm, so a capability stays readable about what it
    committed to and a later change of algorithm cannot be mistaken for a match.
    """
    return DIGEST_PREFIX + hashlib.sha256(script.encode("utf-8")).hexdigest()


class FLClient:
    """Poll an FL server for jobs and run each one against the local guardian."""

    def __init__(
        self,
        *,
        server_url,
        guardian_url,
        client_id,
        poll_interval=3.0,
        timeout=30.0,
    ):
        self.server_url = server_url.rstrip("/")
        self.guardian_url = guardian_url.rstrip("/")
        self.client_id = client_id
        self.poll_interval = poll_interval
        self.timeout = timeout

    # -----------------------------------------------------------------
    # FL server
    # -----------------------------------------------------------------
    def poll_job(self):
        """Ask the server for the next pending job, or ``None`` if there is none."""
        resp = requests.get(
            f"{self.server_url}/jobs/next",
            params={"client_id": self.client_id},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json().get("job")

    def report_metrics(self, job_id, metrics):
        """Report a finished run back to the server."""
        resp = requests.post(
            f"{self.server_url}/jobs/{job_id}/metrics",
            json={"client_id": self.client_id, "metrics": metrics},
            timeout=self.timeout,
        )
        resp.raise_for_status()

    def report_failure(self, job_id, error):
        """Report a run that never happened, so the submitter stops waiting."""
        resp = requests.post(
            f"{self.server_url}/jobs/{job_id}/metrics",
            json={"client_id": self.client_id, "error": str(error)},
            timeout=self.timeout,
        )
        resp.raise_for_status()

    # -----------------------------------------------------------------
    # guardian core
    # -----------------------------------------------------------------
    def fetch_data(self, capability, calculated_digest):
        """Redeem a capability at the local guardian core and return the asset.

        ``calculated_digest`` is this client's own measurement of the script it
        holds; the guardian core compares it against the digest the capability
        authorizes and refuses the request if they differ.
        """
        request = dict(capability)
        request["request_context"] = {"calculated_script_digest": calculated_digest}

        resp = requests.post(
            f"{self.guardian_url}/process_capability", json=request, timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()

    # -----------------------------------------------------------------
    # the run itself
    # -----------------------------------------------------------------
    def run_script(self, job, script, data):
        """Stand in for executing the script over the data.

        A real client hands both to the training framework here. This one narrates
        the run and returns fixed metrics, which is enough to show the data
        reaching the compute without ever leaving the guardian's host.
        """
        print(
            f"[fl_client:{self.client_id}] running job {job['job_id']} "
            f"({len(script)} bytes of script) over {len(data)} bytes of data"
        )
        return {
            "accuracy": 0.42,
            "loss": 1.23,
            "samples": len(data),
            "client_id": self.client_id,
        }

    def handle_job(self, job):
        """Run one job end to end: measure, redeem, run, report."""
        job_id = job["job_id"]
        script = job["script"]
        capability = job["capability"]

        digest = script_digest(script)
        logger.info("job %s: computed script digest %s", job_id, digest)

        try:
            data = self.fetch_data(capability, digest)
        except Exception as e:
            logger.exception("job %s: guardian refused the capability", job_id)
            self.report_failure(job_id, f"guardian refused the capability: {e}")
            return

        metrics = self.run_script(job, script, data)
        self.report_metrics(job_id, metrics)
        logger.info("job %s: reported metrics %s", job_id, metrics)

    # -----------------------------------------------------------------
    def run_forever(self):
        """Poll for jobs until interrupted.

        A polling error is logged and retried rather than fatal: the FL server
        coming up after the client is the normal case in a demo.
        """
        logger.info(
            "fl client %s polling %s every %ss, guardian at %s",
            self.client_id,
            self.server_url,
            self.poll_interval,
            self.guardian_url,
        )
        while True:
            try:
                job = self.poll_job()
            except Exception as e:
                logger.warning("could not reach the FL server (%s); retrying", e)
                job = None

            if job is None:
                time.sleep(self.poll_interval)
                continue

            try:
                self.handle_job(job)
            except Exception:
                logger.exception("job %s failed", job.get("job_id"))
