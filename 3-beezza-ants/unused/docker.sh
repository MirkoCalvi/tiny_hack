#!/bin/bash

# docker build -t myimage .devcontainer

# Run container with volume mount to access local Z-Ant repo
docker run -it \
    -v "$(pwd):/workspace" \
    -v "$HOME/Arduino:/home/user/Arduino" \
    myimage \
    bash -c "
        cd /workspace &&
        zig build lib-gen \
            -Dmodel=\"beer\" \
            -Dxip=true \
            -Ddo_export \
            -Ddynamic \
            -Denable_user_tests &&
        zig build lib-test \
            -Dmodel=\"beer\" \
            -Dxip=true \
            -Ddo_export \
            -Ddynamic \
            -Denable_user_tests &&
        zig build lib \
            -Dmodel=\"beer\" \
            -Dtarget=thumb-freestanding \
            -Dcpu=cortex_m7 \
            -Dxip=true \
            -freference-trace \
            -Doptimize=ReleaseFast &&
        cp zig-out/beer/libzant.a /home/user/Arduino/libraries/ZantLib/src/cortex-m7/libzant.a &&
        echo 'Library built and copied to ~/Arduino/libraries/ZantLib/src/cortex-m7/libzant.a'
    "
