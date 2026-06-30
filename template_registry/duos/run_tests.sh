#!/usr/bin/env bash
# Run the per-DUO Rego unit tests.
#
# Each DUO lives in its own folder so that the (intentionally identical)
# `package duo` modules are compiled independently and do not collide -- this
# mirrors how the rego_policy_agent contract evaluates each module in its own
# regorus engine.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prefer the opa binary already vendored in rego_ws, else fall back to PATH.
opa="${here}/../../../rego_ws/opa"
if [[ ! -x "$opa" ]]; then
    opa="$(command -v opa || true)"
fi
if [[ -z "${opa}" ]]; then
    echo "error: opa binary not found (looked in rego_ws/opa and on PATH)" >&2
    exit 1
fi

status=0
for duo in gs is; do
    echo "== testing ${duo} =="
    if ! "$opa" test "${here}/${duo}" -v; then
        status=1
    fi
done

exit "$status"
