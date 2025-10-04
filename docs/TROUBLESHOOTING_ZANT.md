
# error while using ./create
When using ./create remember to set  --do-user-tests --do-extract --optimize --cpu --target properly!


# -Dfuse
When using -Dfuse ensure the -Denable_user_tests are enabled

# XIP on macOS
When using XIP on macOS you must build the static library inside the provided Docker container, 
otherwise the build will fail due to missing toolchain support.

# Bash error for zant input_setter. 
In macbook, when running 

```shell

./zant input_setter --model test --shape 1,3,224,224

```

 gives output:

```shell
./zant: line 9: declare: -A: invalid option

declare: usage: declare [-afFirtx] [-p] [name[=value] ...]

```

Add bash in front to force correct bash call.

### Correct command: 

```shell
bash ./zant input_setter --model test --shape 1,3,224,224
```