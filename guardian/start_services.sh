#!/bin/bash
: "${F_GUARDIAN_HOST?Missing environment variable F_GUARDIAN_HOST}"

export PDO_HOME="/project/pdo/run/opt/pdo"
export PDO_SOURCE_ROOT="/project/pdo/src"
export PDO_INSTALL_ROOT="/project/pdo/run"
export PDO_LEDGER_URL="http://localhost:19088"  # not used?
source ${PDO_SOURCE_ROOT}/build/common-config.sh

# This is sourced mainly for shell helpers like yell, try, and die
source ${PDO_HOME}/bin/lib/common.sh
source ${PDO_INSTALL_ROOT}/bin/activate

# Create key for the guardian services
KEYGEN=${PDO_SOURCE_ROOT}/build/__tools__/make-keys
${KEYGEN} --keyfile ${PDO_HOME}/keys/guardian_service --format pem
${KEYGEN} --keyfile ${PDO_HOME}/keys/guardian_sservice --format pem


# Start the guardian storage service (TODO: this is not used? but an error pops up if not started)
try ${PDO_HOME}/contracts/contracts/scripts/ss_start.sh -c -o ${PDO_HOME}/logs -- \
    --loglevel debug \
    --config guardian_service.toml \
    --config-dir ${PDO_HOME}/etc/contracts \
    --identity guardian_sservice \
    --bind host ${F_GUARDIAN_HOST}

sleep 3

# Start the guardian service
try ${PDO_HOME}/contracts/contracts/scripts/gs_start.sh -c -o ${PDO_HOME}/logs -- \
    --loglevel debug \
    --config guardian_service.toml \
    --config-dir ${PDO_HOME}/etc/contracts \
    --identity guardian_service \
    --bind host ${F_GUARDIAN_HOST}

tail -f /dev/null