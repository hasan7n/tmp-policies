#!/usr/bin/env bash
# Run the per-DUO Rego unit tests.
#
# Each DUO lives in its own folder so that the (intentionally identical)
# `package duo` modules are compiled independently and do not collide -- this
# mirrors how the rego_policy_agent contract evaluates each module in its own
# regorus engine.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

opa="$(command -v opa || true)"

if [[ -z "${opa}" ]]; then
    echo "error: opa binary not found" >&2
    exit 1
fi

status=0
for duo in gs is ds hmb gso nmds ncu rs npoa poa ps col pub irb gru mor rtn ts us npu npuncu; do
    echo "== testing ${duo} =="
    if ! "$opa" test "${here}/${duo}" -v; then
        status=1
    fi
done

exit "$status"
