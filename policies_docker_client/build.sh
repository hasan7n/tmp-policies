rm -rf policies
mkdir policies
cp -r ../../pdo-contracts/download-contract/ policies

docker build -t pdo_policies:latest -f ./Dockerfile .