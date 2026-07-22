set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INTERFACE="$(hostname -I | awk '{print $1}')"
# The template registry seeds from the shared credential/policy-card folders at
# the top of the tmp-policies tree (one level above this tools/ directory).
TMP_POLICIES_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
bash asset_registry/run_docker.sh \
    --image mlcommons/pdo_toy_asset_registry:latest \
    --interface $INTERFACE \
    --port 8001 &
bash template_registry/run_docker.sh \
    --image mlcommons/pdo_toy_template_registry:latest \
    --interface $INTERFACE \
    --port 8002 \
    --credentials-dir "$TMP_POLICIES_DIR/credentials" \
    --policy-cards-dir "$TMP_POLICIES_DIR/policy_cards" &
