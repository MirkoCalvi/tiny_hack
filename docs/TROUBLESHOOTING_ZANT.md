
# error while using ./create
When using ./create remember to set  --do-user-tests --do-extract --optimize --cpu --target properly!


# -Dfuse
When using -Dfuse ensure the -Denable_user_tests are enabled

# XIP on macOS
When using XIP on macOS you must build the static library inside the provided Docker container, 
otherwise the build will fail due to missing toolchain support.
