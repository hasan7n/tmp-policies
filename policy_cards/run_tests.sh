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
for duo in \
    geographical-restriction \
    institution-specific-restriction \
    disease-specific-research \
    health-or-medical-or-biomedical-research \
    genetic-studies-only \
    no-general-methods-research \
    non-commercial-use-only \
    research-specific-restrictions \
    population-origins-or-ancestry-research-prohibited \
    population-origins-or-ancestry-research-only \
    project-specific-restriction \
    collaboration-required \
    publication-required \
    ethics-approval-required \
    general-research-use \
    publication-moratorium \
    return-to-database-or-resource \
    time-limit-on-use \
    user-specific-restriction \
    not-for-profit-organisation-use-only \
    not-for-profit-non-commercial-use-only; do
    echo "== testing ${duo} =="
    if ! "$opa" test "${here}/${duo}" -v; then
        status=1
    fi
done

exit "$status"
