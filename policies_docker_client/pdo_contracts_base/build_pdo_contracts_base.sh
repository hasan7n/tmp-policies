set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Some config
REPOSITORY="https://github.com/hasan7n/pdo-contracts"
BRANCH="data-download"
TMP_PDO_CONTRACTS_DIR=/tmp/pdo-contracts
PDO_VERSION=0.4.29
CONTRACTS_VERSION=0.4.29
PDO_DEBUG_BUILD=1
PDO_LOG_LEVEL=debug
CONTRACT_FAMILIES="exchange-contract identity-contract"

# Clone and setup the repo
rm -rf $TMP_PDO_CONTRACTS_DIR
git clone $REPOSITORY $TMP_PDO_CONTRACTS_DIR
cd $TMP_PDO_CONTRACTS_DIR
git checkout $BRANCH

# Build the pdo images
PDO_VERSION=$PDO_VERSION \
    PDO_DEBUG_BUILD=$PDO_DEBUG_BUILD \
    PDO_LOG_LEVEL=$PDO_LOG_LEVEL \
    CONTRACTS_VERSION=$CONTRACTS_VERSION \
    CONTRACT_FAMILIES="$CONTRACT_FAMILIES" \
    make -C $TMP_PDO_CONTRACTS_DIR/docker build_contracts
