![preview](https://hackmd.io/_uploads/ByCdrokpel.png)


<h1 align="center">  Low Power Space Debris Monitoring</h1>


## Overview

The main objective is to tackle the issue of space debris by developing a multi-class classification model to increase debris awareness, space pollution mapping and eventually collision avoidance.

Our solution is low power, low cost and with a low bandwidth usage, specifically designed to be implemented efficiently on a cubesat. 


## Quickstart

### 1. Clone the repository
```bash
git clone https://github.com/TinyHack-Group-8/project.git
cd project
```

### 2. Train you model and do quantization
Follow the notebook [model_example.ipynb](notebooks/model_example.ipynb) to load, quantize and then test your model. 

### 3. Deploy the model

Drag the quantized model `.onnx` file inside the `src/` directory. This will generate the library, build and flash it on the Nicla connected on the serial device specified in `~/pipeline/vars.sh`.

Run the pipeline (make sure your tensor shapes , in the root dir:
```bash
make
```

### 4. Run Flask server and React client

At last, in order to access the dashboard, and save the serial communication with the Nicla. You can build the frontend and serve the backend with the following commands:


```bash=
make build-frontend
make serve
```

## Contributors

- [@KokkuApples](https://github.com/KokkuApples) - Federico Mele
- [@pasc4le](https://github.com/pasc4le/) - Giuseppe Pascale
- [@Paolo410](https://github.com/Paolo410) - Paolo Malugani
- [@Sampli1](https://github.com/Sampli1) - Sandro Marghella

## Further on...

You can check out the detailed technical README in the docs folder.
