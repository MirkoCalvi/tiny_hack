DEVICE = /dev/ttyACM0

.PHONY: all

all: clean codegen build flash

codegen:
	./pipeline/codegen.sh

build:
	./pipeline/build.sh

flash:
	./pipeline/flash.sh

clean:
	./pipeline/clean.sh

build-frontend:
	./pipeline/build-frontend.sh

serve:
	./pipeline/serve.sh

watch:
	screen $(DEVICE) 921600
