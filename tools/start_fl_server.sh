set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The FL server is reached from two directions: the webapp submits jobs to it and
# each inference guardian's FL client polls it, so it binds every interface.
bash ${SCRIPT_DIR}/fl_server/run.sh --interface 0.0.0.0 --port 7920 &
