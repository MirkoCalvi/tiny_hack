FROM ubuntu:22.04

# Set the DEBIAN_FRONTEND variable to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Update packages and install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    wget \
    ca-certificates \
		cmake \
    gnupg \
    software-properties-common \
    vim \
		neovim \
		python3.10-dev \
		python3.10-venv \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# pin zig version
ENV ZIG_VERSION=0.14.0
RUN wget https://ziglang.org/download/${ZIG_VERSION}/zig-linux-$(arch)-${ZIG_VERSION}.tar.xz \
    && tar xf zig-linux-$(arch)-${ZIG_VERSION}.tar.xz \
    && mv zig-linux-$(arch)-${ZIG_VERSION} /opt/zig \
    && ln -s /opt/zig/zig /usr/local/bin/zig \
    && rm zig-linux-$(arch)-${ZIG_VERSION}.tar.xz

WORKDIR /workspace

ENV ZANT=/workspace/Z-Ant
RUN git clone https://github.com/ZantFoundation/Z-Ant.git $ZANT

# Install ONNX dependencies
RUN python3 -m venv $ZANT/.venv
RUN $ZANT/.venv/bin/python -m pip install --upgrade pip && \
    $ZANT/.venv/bin/pip install onnx onnxruntime onnxsim
ENV PATH="$ZANT/.venv/bin:$PATH"

USER root

WORKDIR $ZANT

CMD [ "/bin/bash" ]
