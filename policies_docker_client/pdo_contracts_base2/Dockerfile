FROM ubuntu:22.04

WORKDIR /

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y cmake curl git pkg-config unzip xxd libssl-dev build-essential
RUN apt install -y swig python3 python3-dev python3-venv virtualenv
RUN apt install -y liblmdb-dev libprotobuf-dev libsecp256k1-dev protobuf-compiler libncurses5-dev
RUN apt install -y wget curl

RUN wget -q -P /tmp https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-27/wasi-sdk-27.0-x86_64-linux.deb
RUN dpkg --install /tmp/wasi-sdk-27.0-x86_64-linux.deb

RUN git clone https://github.com/hasan7n/pdo-contracts
RUN cd pdo-contracts && git checkout data-download && git submodule update --init --recursive

ENV PDO_CONTRACTS_ROOT=/pdo-contracts
ENV PDO_INSTALL_ROOT=/pdo_install
ENV PDO_SOURCE_ROOT=/pdo-contracts/private-data-objects

RUN bash -c 'source ${PDO_SOURCE_ROOT}/build/common-config.sh && make -C ${PDO_SOURCE_ROOT}/build client'
RUN ${PDO_INSTALL_ROOT}/bin/pip install jupyterlab papermill ipywidgets jupytext

RUN echo "SET(CONTRACT_FAMILIES exchange-contract identity-contract)" > /pdo-contracts/Local.cmake
RUN bash -c 'source ${PDO_INSTALL_ROOT}/bin/activate && source ${PDO_SOURCE_ROOT}/build/common-config.sh && make -C ${PDO_CONTRACTS_ROOT}'
RUN bash -c 'source ${PDO_INSTALL_ROOT}/bin/activate && source ${PDO_SOURCE_ROOT}/build/common-config.sh && make -C ${PDO_CONTRACTS_ROOT} install'

