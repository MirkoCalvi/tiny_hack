import os
from PIL import Image
import numpy as np
import torch
import json
from tqdm import tqdm
import argparse
from focoos import FocoosHUB
from focoos import ModelRegistry

def infer_stats(model_id, input_folder):
    FOCOOS_API_KEY = os.getenv(
        "FOCOOS_API_KEY"
    )
    hub = FocoosHUB(api_key=FOCOOS_API_KEY)

    model_registry = ModelRegistry()

    for m in model_registry.list_models():
        model_info = model_registry.get_model_info(m)
        model_info.pprint()

    from focoos import ModelManager

    model = ModelManager.get("hub://" + model_id, hub=hub)
    model.model_info.pprint()

    with open(os.path.join(input_folder, '_annotations.coco.json')) as f:
        data = json.load(f)

    person_recall = []
    person_precision = []
    no_person_recall = []
    no_person_precision = []

    for img in tqdm(data['images']):

        annotations = [x for x in data['annotations'] if x['image_id'] == img['id']]
        img_big = Image.open(os.path.join(input_folder, img['file_name']))
        img = img_big.resize((96, 96))

        inp = np.array(img)

        pixel_mean = np.array([123.675, 116.28, 103.53])
        pixel_std = np.array([58.395, 57.12, 57.375])
        inp = (inp - pixel_mean) / pixel_std
        inp= np.transpose(inp, (2, 0, 1))

        inp = torch.from_numpy(inp).float()
        out = model.model(inp.unsqueeze(0))

        pred = torch.softmax(out[0][0].detach(), dim=0)

        cls = int(np.argmax(pred, axis=0).numpy()) + 1

        is_human = False
        for ann in annotations:
            if ann['category_id'] == 1:
                is_human = True
                break

        if is_human:
            if cls == 1:
                person_recall.append(1)
                person_precision.append(1)
            else:
                no_person_precision.append(0)
                person_recall.append(0)

        else:
            if cls == 2:
                no_person_recall.append(1)
                no_person_precision.append(1)
            else:
                no_person_recall.append(0)
                person_precision.append(0)

    print("Person recall:", np.mean(np.array(person_recall)))
    print("Person precision:", np.mean(np.array(person_precision)))
    print("No Person recall:", np.mean(np.array(no_person_recall)))
    print("No Person precision:", np.mean(np.array(no_person_precision)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_id", type=str, required=True)
    parser.add_argument("--dataset_test_folder", type=str, required=True)

    args = parser.parse_args()

    infer_stats(args.model_id, args.dataset_test_folder)

