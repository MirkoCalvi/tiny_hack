"""
Data loading and preprocessing for skin cancer classification
"""
import os
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import albumentations as A
from albumentations.pytorch import ToTensorV2
import numpy as np


class SkinCancerDataset(Dataset):
    """Custom dataset for skin cancer classification"""

    def __init__(self, root_dir, split='train', transform=None):
        """
        Args:
            root_dir: Root directory containing train/valid/test folders
            split: 'train', 'valid', or 'test'
            transform: Albumentations transform to apply
        """
        self.root_dir = os.path.join(root_dir, split)
        self.transform = transform
        self.classes = sorted([d for d in os.listdir(self.root_dir)
                              if os.path.isdir(os.path.join(self.root_dir, d))])
        self.class_to_idx = {cls: idx for idx, cls in enumerate(self.classes)}

        # Load all image paths and labels
        self.samples = []
        for class_name in self.classes:
            class_dir = os.path.join(self.root_dir, class_name)
            class_idx = self.class_to_idx[class_name]
            for img_name in os.listdir(class_dir):
                if img_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                    self.samples.append((os.path.join(class_dir, img_name), class_idx))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]

        # Load image
        image = Image.open(img_path).convert('RGB')
        image = np.array(image)

        # Apply transforms
        if self.transform:
            transformed = self.transform(image=image)
            image = transformed['image']

        return image, label


def get_transforms(img_size=384, split='train'):
    """
    Get albumentations transforms for different splits

    Args:
        img_size: Target image size
        split: 'train', 'valid', or 'test'
    """
    if split == 'train':
        return A.Compose([
            A.Resize(img_size, img_size),
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.5),
            A.RandomRotate90(p=0.5),
            A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.15, rotate_limit=45, p=0.5),
            A.OneOf([
                A.OpticalDistortion(p=0.3),
                A.GridDistortion(p=0.1),
                A.ElasticTransform(p=0.3),
            ], p=0.3),
            A.OneOf([
                A.GaussNoise(p=0.3),
                A.GaussianBlur(p=0.3),
                A.MotionBlur(p=0.3),
            ], p=0.3),
            A.OneOf([
                A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.3),
                A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30, val_shift_limit=20, p=0.3),
                A.RGBShift(r_shift_limit=20, g_shift_limit=20, b_shift_limit=20, p=0.3),
            ], p=0.5),
            A.CoarseDropout(num_holes_range=(1, 8), hole_height_range=(16, 32), hole_width_range=(16, 32), p=0.3),
            A.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
            ToTensorV2(),
        ])
    else:
        return A.Compose([
            A.Resize(img_size, img_size),
            A.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
            ToTensorV2(),
        ])


def create_dataloaders(root_dir, batch_size=32, img_size=384, num_workers=4):
    """
    Create train, validation, and test dataloaders

    Args:
        root_dir: Root directory containing Skin_Cancer_FullSize folder
        batch_size: Batch size for training
        img_size: Image size for model input
        num_workers: Number of workers for data loading

    Returns:
        train_loader, val_loader, test_loader, num_classes, class_names
    """
    data_dir = os.path.join(root_dir, 'Skin_Cancer_FullSize')

    # Create datasets
    train_dataset = SkinCancerDataset(
        data_dir,
        split='train',
        transform=get_transforms(img_size, 'train')
    )

    val_dataset = SkinCancerDataset(
        data_dir,
        split='valid',
        transform=get_transforms(img_size, 'valid')
    )

    test_dataset = SkinCancerDataset(
        data_dir,
        split='test',
        transform=get_transforms(img_size, 'test')
    )

    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        persistent_workers=True if num_workers > 0 else False
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
        persistent_workers=True if num_workers > 0 else False
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
        persistent_workers=True if num_workers > 0 else False
    )

    num_classes = len(train_dataset.classes)
    class_names = train_dataset.classes

    return train_loader, val_loader, test_loader, num_classes, class_names


if __name__ == '__main__':
    # Test the dataloader
    train_loader, val_loader, test_loader, num_classes, class_names = create_dataloaders(
        root_dir='./',
        batch_size=8,
        img_size=384,
        num_workers=2
    )

    print(f"Number of classes: {num_classes}")
    print(f"Class names: {class_names}")
    print(f"Train batches: {len(train_loader)}")
    print(f"Val batches: {len(val_loader)}")
    print(f"Test batches: {len(test_loader)}")

    # Test loading a batch
    images, labels = next(iter(train_loader))
    print(f"Batch shape: {images.shape}")
    print(f"Labels: {labels}")
