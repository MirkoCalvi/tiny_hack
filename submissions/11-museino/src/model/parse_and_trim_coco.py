import json
import os
import shutil
import argparse

from tqdm import tqdm
import random

def parse_and_trim_coco(coco_path, new_coco_path):
    splits = ['train', 'valid', 'test']

    for split in splits:
        new_gt = {"images": [], "annotations": []}
        im_cache = {}
        ann_cache = {}
        with open(os.path.join(coco_path, split, '_annotations.coco.json'), 'r') as f:
            data = json.load(f)
        for image in tqdm(data['images'], "create image cache"):
            im_cache[image['id']] = image
        for ann in tqdm(data['annotations'], "create ann cache"):
            if ann['image_id'] not in ann_cache:
                ann_cache[ann['image_id']] = []
            ann_cache[ann['image_id']].append(ann)

        human_imgs = set()
        non_human_imgs = set()
        image_id = []
        for im_id in im_cache:
            is_human = False
            for ann in ann_cache.get(im_id, []):
                if ann['category_id'] == 1:
                    ann['category_id'] = 2
                if ann['category_id'] == 50:
                    ann['category_id'] = 1
                    is_human = True
            if is_human:
                human_imgs.add(im_id)
            else:
                non_human_imgs.add(im_id)

        human_imgs = list(human_imgs)
        non_human_imgs = list(non_human_imgs)

        for im_id in human_imgs:
            cleaned_annotations = []
            for ann in ann_cache.get(im_id, []):
                if ann['category_id'] == 1:
                    if ann['bbox'][3] > 100 and ann['bbox'][2] > 50:
                        cleaned_annotations.append(ann)
            ann_cache[im_id] = cleaned_annotations

        new_proportion = len(human_imgs) // 4
        new_humans = random.sample(human_imgs, new_proportion)
        new_non_humans = random.sample(non_human_imgs, new_proportion)

        total_new_images = new_humans + new_non_humans

        new_gt['categories'] = [
            {'id': 0, 'name': 'object', 'supercategory': 'none'},
            {'id': 1, 'name': 'person', 'supercategory': 'object'},
            {'id': 2, 'name': 'no_person', 'supercategory': 'object'}
        ]

        for img_id in total_new_images:
            new_gt['images'].append(im_cache[img_id])
            for x in ann_cache.get(img_id, []):
                if x['category_id'] != 1:
                    x['category_id'] = 2
            new_gt['annotations'] += ann_cache.get(img_id, [])
        new_gt['info'] = data['info']
        new_gt['licenses'] = data['licenses']
        os.makedirs(os.path.join(new_coco_path, split), exist_ok=True)

        for image in tqdm(new_gt['images'], "saving images..."):
            shutil.copy(os.path.join(coco_path, split, image['file_name']), os.path.join(new_coco_path, split, image['file_name']))

        with open(os.path.join(new_coco_path, split, "_annotations.coco.json"), 'w') as f:
            json.dump(new_gt, f, indent=4)

if __name__ == '__main__':
    argparse = argparse.ArgumentParser()
    argparse.add_argument('--coco_root_folder', type=str)
    argparse.add_argument('--new_coco_folder', type=str)

    args = argparse.parse_args()

    parse_and_trim_coco(args.coco_root_folder, args.new_coco_folder)