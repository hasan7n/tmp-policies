set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Some config
REPOSITORY="https://github.com/hasan7n/pdo-contracts"
BRANCH="data-download"
TMP_PDO_CONTRACTS_DIR=/tmp/pdo-contracts
PDO_VERSION=0.4.29
PDO_DEBUG_BUILD=1
PDO_LOG_LEVEL=debug

# Clone and setup the repo
rm -rf $TMP_PDO_CONTRACTS_DIR
git clone $REPOSITORY $TMP_PDO_CONTRACTS_DIR
cd $TMP_PDO_CONTRACTS_DIR
git checkout $BRANCH
git submodule update --init --recursive
PDO_SOURCE_ROOT=$TMP_PDO_CONTRACTS_DIR/private-data-objects
cd $PDO_SOURCE_ROOT
git checkout -B tmp_branch
cp $SCRIPT_DIR/make.loc $PDO_SOURCE_ROOT/docker/

# Build the pdo images
PDO_SOURCE_ROOT=$PDO_SOURCE_ROOT \
    PDO_VERSION=$PDO_VERSION \
    PDO_DEBUG_BUILD=$PDO_DEBUG_BUILD \
    PDO_LOG_LEVEL=$PDO_LOG_LEVEL \
    make -C $PDO_SOURCE_ROOT/docker all
PDO_SOURCE_ROOT=$PDO_SOURCE_ROOT \
    PDO_VERSION=$PDO_VERSION \
    PDO_DEBUG_BUILD=$PDO_DEBUG_BUILD \
    PDO_LOG_LEVEL=$PDO_LOG_LEVEL \
    make -C $PDO_SOURCE_ROOT/docker clean_repository

