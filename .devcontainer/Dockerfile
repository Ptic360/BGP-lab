FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        iproute2 \
        iptables \
        iputils-ping \
        net-tools \
        procps \
        sudo \
        wget \
        software-properties-common \
        lsb-release \
        python3 \
        python3-pip && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://apt.kathara.org/kathara.gpg | gpg --dearmor -o /etc/apt/keyrings/kathara.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/kathara.gpg] https://apt.kathara.org/ $(lsb_release -cs) main" > /etc/apt/sources.list.d/kathara.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends kathara && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN usermod -aG docker vscode || true
