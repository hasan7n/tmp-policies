# fl server

A toy federated-learning server: the aggregator the webapp submits inference work
to, and the FL clients beside each guardian poll.

It knows nothing about PDO. A job is a script plus an opaque capability package;
a result is whatever metrics a client reports. Jobs live in memory, are handed
out oldest-first, and are never retried or expired.

A job may carry a `target_client`, and then only the client of that name may claim
it. The submitter sets it to the FL client beside the guardian the job's capability
was minted for — that capability is refused at any other guardian, so leaving the
job open would let a second data holder's client claim work it can only fail.

```bash
./run.sh --interface 0.0.0.0 --port 7920
```

| Method | Path                 | Body / query                | Returns                        |
|--------|----------------------|-----------------------------|--------------------------------|
| GET    | `/info`              |                             | `{service, jobs}`              |
| POST   | `/jobs`              | `{script, capability, target_client, ...}` | `{job_id, status}` |
| GET    | `/jobs/next`         | `?client_id=`               | `{job}` or `{job: null}`       |
| POST   | `/jobs/<id>/metrics` | `{metrics}` or `{error}`    | `{job_id, status}`             |
| GET    | `/jobs/<id>`         |                             | the job record, without script |

A status poll never returns the script or the capability: those are the client's
to see, not the submitter's to re-read.

The submitter is the webapp's inference action runner
(`webapp/app/action_runners.py`); the consumer is the FL client bundled with the
inference guardian (`tools/guardians/inference/fl_framework/`).
