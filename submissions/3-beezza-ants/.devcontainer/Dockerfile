# Use the base image of Ubuntu
# FROM ubuntu:22.04
FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04
# FROM mcr.microsoft.com/devcontainers/base:noble

# Set the DEBIAN_FRONTEND variable to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Update packages and install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    wget \
    ca-certificates \
    gnupg \
    software-properties-common \
    vim \
    sudo \
    usbutils \
    dfu-util \
    && rm -rf /var/lib/apt/lists/*

# Install Zig (replace the version with the desired one)
ENV ZIG_VERSION=0.14.0
RUN wget https://ziglang.org/download/${ZIG_VERSION}/zig-linux-$(arch)-${ZIG_VERSION}.tar.xz \
    && tar xf zig-linux-$(arch)-${ZIG_VERSION}.tar.xz \
    && mv zig-linux-$(arch)-${ZIG_VERSION} /opt/zig \
    && ln -s /opt/zig/zig /usr/local/bin/zig \
    && rm zig-linux-$(arch)-${ZIG_VERSION}.tar.xz

# Install Arduino CLI under /usr/local/bin
RUN mkdir -p /usr/local \
    && cd /usr/local \
    && curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh

# # Set the working directory
# WORKDIR /workspace

# # Set a non-root user (optional but recommended)
# ARG USERNAME=vscode
# ARG USER_UID=1000
# ARG USER_GID=$USER_UID

# # Create the user
# RUN groupadd --gid $USER_GID $USERNAME \
#     && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
#     && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/$USERNAME \
#     && chmod 0440 /etc/sudoers.d/$USERNAME

# # Switch to the non-root user
# USER $USERNAME

# # Default command
# CMD [ "/bin/bash" ]

# EOF
