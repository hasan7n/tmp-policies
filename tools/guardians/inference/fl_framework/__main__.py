"""Entry point for the FL client: ``python -m fl_framework``."""

import argparse
import logging
import os
import socket

from .client import FLClient


def main():
    parser = argparse.ArgumentParser(description="Run the mock FL client.")
    parser.add_argument(
        "-s",
        "--server-url",
        default=os.environ.get("FL_SERVER_URL"),
        help="FL server to poll for jobs (default: $FL_SERVER_URL)",
    )
    parser.add_argument(
        "-g",
        "--guardian-url",
        default=os.environ.get("GUARDIAN_CORE_URL", "http://localhost:7900"),
        help="guardian core to redeem capabilities at (default: $GUARDIAN_CORE_URL)",
    )
    parser.add_argument(
        "-c",
        "--client-id",
        default=os.environ.get("FL_CLIENT_ID") or socket.gethostname(),
        help="identifies this client to the FL server (default: $FL_CLIENT_ID or hostname)",
    )
    parser.add_argument(
        "-i",
        "--poll-interval",
        type=float,
        default=float(os.environ.get("FL_POLL_INTERVAL", "3")),
        help="seconds between polls (default: $FL_POLL_INTERVAL or 3)",
    )
    args = parser.parse_args()

    if not args.server_url:
        parser.error("an FL server is required: pass --server-url or set FL_SERVER_URL")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    FLClient(
        server_url=args.server_url,
        guardian_url=args.guardian_url,
        client_id=args.client_id,
        poll_interval=args.poll_interval,
    ).run_forever()


if __name__ == "__main__":
    main()
