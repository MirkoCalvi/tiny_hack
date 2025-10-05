"""
Visualization utilities for training analysis and results
"""
import os
import torch
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
from torch.utils.data import DataLoader
import argparse

from dataset import create_dataloaders, get_transforms
from model import create_model


def plot_training_history(log_dir, save_path=None):
    """
    Plot training history from tensorboard logs

    Args:
        log_dir: Directory containing tensorboard logs
        save_path: Path to save the plot
    """
    from tensorboard.backend.event_processing import event_accumulator

    ea = event_accumulator.EventAccumulator(log_dir)
    ea.Reload()

    # Get available tags
    scalar_tags = ea.Tags()['scalars']

    # Create subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # Plot Loss
    if 'Train/Loss' in scalar_tags and 'Val/Loss' in scalar_tags:
        train_loss = ea.Scalars('Train/Loss')
        val_loss = ea.Scalars('Val/Loss')

        axes[0, 0].plot([x.step for x in train_loss], [x.value for x in train_loss], label='Train')
        axes[0, 0].plot([x.step for x in val_loss], [x.value for x in val_loss], label='Validation')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].set_title('Training and Validation Loss')
        axes[0, 0].legend()
        axes[0, 0].grid(alpha=0.3)

    # Plot Accuracy
    if 'Train/Accuracy' in scalar_tags and 'Val/Accuracy' in scalar_tags:
        train_acc = ea.Scalars('Train/Accuracy')
        val_acc = ea.Scalars('Val/Accuracy')

        axes[0, 1].plot([x.step for x in train_acc], [x.value for x in train_acc], label='Train')
        axes[0, 1].plot([x.step for x in val_acc], [x.value for x in val_acc], label='Validation')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Accuracy')
        axes[0, 1].set_title('Training and Validation Accuracy')
        axes[0, 1].legend()
        axes[0, 1].grid(alpha=0.3)

    # Plot F1 Score
    if 'Train/F1_Macro' in scalar_tags and 'Val/F1_Macro' in scalar_tags:
        train_f1 = ea.Scalars('Train/F1_Macro')
        val_f1 = ea.Scalars('Val/F1_Macro')

        axes[1, 0].plot([x.step for x in train_f1], [x.value for x in train_f1], label='Train')
        axes[1, 0].plot([x.step for x in val_f1], [x.value for x in val_f1], label='Validation')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('F1 Score (Macro)')
        axes[1, 0].set_title('Training and Validation F1 Score')
        axes[1, 0].legend()
        axes[1, 0].grid(alpha=0.3)

    # Plot Learning Rate
    if 'Train/LearningRate' in scalar_tags:
        lr = ea.Scalars('Train/LearningRate')

        axes[1, 1].plot([x.step for x in lr], [x.value for x in lr])
        axes[1, 1].set_xlabel('Epoch')
        axes[1, 1].set_ylabel('Learning Rate')
        axes[1, 1].set_title('Learning Rate Schedule')
        axes[1, 1].grid(alpha=0.3)
        axes[1, 1].set_yscale('log')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Training history plot saved to {save_path}")

    return fig


def visualize_predictions(model, data_loader, device, class_names, num_images=16, save_path=None):
    """
    Visualize model predictions on a batch of images

    Args:
        model: The model to use
        data_loader: DataLoader for the dataset
        device: Device to use
        class_names: List of class names
        num_images: Number of images to visualize
        save_path: Path to save the visualization
    """
    model.eval()

    # Get a batch of images
    images, labels = next(iter(data_loader))
    images = images.to(device)
    labels = labels.to(device)

    # Get predictions
    with torch.no_grad():
        outputs = model(images)
        probs = torch.softmax(outputs, dim=1)
        _, preds = torch.max(outputs, 1)

    # Move to CPU
    images = images.cpu()
    labels = labels.cpu()
    preds = preds.cpu()
    probs = probs.cpu()

    # Denormalize images
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    images = images * std + mean
    images = torch.clamp(images, 0, 1)

    # Plot
    num_images = min(num_images, images.size(0))
    rows = int(np.sqrt(num_images))
    cols = int(np.ceil(num_images / rows))

    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 3.5))
    if rows == 1 and cols == 1:
        axes = [[axes]]
    elif rows == 1 or cols == 1:
        axes = axes.reshape(rows, cols)

    for idx in range(num_images):
        row = idx // cols
        col = idx % cols
        ax = axes[row, col]

        # Display image
        img = images[idx].permute(1, 2, 0).numpy()
        ax.imshow(img)

        # Get prediction info
        true_label = class_names[labels[idx]]
        pred_label = class_names[preds[idx]]
        confidence = probs[idx, preds[idx]].item()

        # Set title with color coding
        is_correct = labels[idx] == preds[idx]
        title_color = 'green' if is_correct else 'red'
        title = f"True: {true_label[:20]}\nPred: {pred_label[:20]}\nConf: {confidence:.2%}"

        ax.set_title(title, color=title_color, fontsize=9)
        ax.axis('off')

    # Hide empty subplots
    for idx in range(num_images, rows * cols):
        row = idx // cols
        col = idx % cols
        axes[row, col].axis('off')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Predictions visualization saved to {save_path}")

    return fig


def visualize_class_distribution(data_loader, class_names, save_path=None):
    """
    Visualize class distribution in the dataset

    Args:
        data_loader: DataLoader for the dataset
        class_names: List of class names
        save_path: Path to save the plot
    """
    # Count samples per class
    class_counts = torch.zeros(len(class_names))

    for _, labels in data_loader:
        for label in labels:
            class_counts[label] += 1

    # Plot
    fig, ax = plt.subplots(figsize=(12, 6))

    bars = ax.bar(range(len(class_names)), class_counts.numpy())

    # Color bars
    colors = plt.cm.viridis(np.linspace(0, 1, len(class_names)))
    for bar, color in zip(bars, colors):
        bar.set_color(color)

    ax.set_xlabel('Class', fontsize=12)
    ax.set_ylabel('Number of Samples', fontsize=12)
    ax.set_title('Class Distribution', fontsize=16, pad=20)
    ax.set_xticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=45, ha='right')
    ax.grid(axis='y', alpha=0.3)

    # Add value labels on bars
    for i, (bar, count) in enumerate(zip(bars, class_counts)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(count)}',
                ha='center', va='bottom', fontsize=10)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Class distribution plot saved to {save_path}")

    return fig


def visualize_sample_images(data_loader, class_names, samples_per_class=3, save_path=None):
    """
    Visualize sample images from each class

    Args:
        data_loader: DataLoader for the dataset
        class_names: List of class names
        samples_per_class: Number of samples to show per class
        save_path: Path to save the visualization
    """
    num_classes = len(class_names)

    # Collect samples from each class
    class_samples = {i: [] for i in range(num_classes)}

    for images, labels in data_loader:
        for img, label in zip(images, labels):
            label = label.item()
            if len(class_samples[label]) < samples_per_class:
                class_samples[label].append(img)

        # Check if we have enough samples
        if all(len(samples) >= samples_per_class for samples in class_samples.values()):
            break

    # Denormalize images
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)

    # Plot
    fig, axes = plt.subplots(num_classes, samples_per_class, figsize=(samples_per_class * 3, num_classes * 3))

    if num_classes == 1:
        axes = [axes]

    for class_idx in range(num_classes):
        for sample_idx in range(samples_per_class):
            ax = axes[class_idx][sample_idx] if samples_per_class > 1 else axes[class_idx]

            if sample_idx < len(class_samples[class_idx]):
                img = class_samples[class_idx][sample_idx]
                img = img * std + mean
                img = torch.clamp(img, 0, 1)
                img = img.permute(1, 2, 0).numpy()

                ax.imshow(img)

                if sample_idx == 0:
                    ax.set_ylabel(class_names[class_idx], fontsize=10, rotation=0, ha='right', va='center')

            ax.axis('off')

    plt.suptitle('Sample Images from Each Class', fontsize=16, y=0.995)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Sample images visualization saved to {save_path}")

    return fig


def main(args):
    """Main function for visualization"""

    if args.mode == 'training_history':
        if not args.log_dir:
            raise ValueError("--log_dir is required for training_history mode")

        print(f"Plotting training history from {args.log_dir}")
        plot_training_history(args.log_dir, args.output)

    elif args.mode == 'predictions':
        if not args.checkpoint:
            raise ValueError("--checkpoint is required for predictions mode")

        # Device configuration
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {device}")

        # Load checkpoint
        print(f"Loading checkpoint from {args.checkpoint}")
        checkpoint = torch.load(args.checkpoint, map_location=device)

        # Get parameters
        saved_args = checkpoint.get('args', None)
        if saved_args:
            model_name = saved_args.model_name
            img_size = saved_args.img_size
            dropout = saved_args.dropout
        else:
            model_name = args.model_name
            img_size = args.img_size
            dropout = args.dropout

        # Load data
        print("Loading data...")
        train_loader, val_loader, test_loader, num_classes, class_names = create_dataloaders(
            root_dir=args.data_dir,
            batch_size=args.batch_size,
            img_size=img_size,
            num_workers=args.num_workers
        )

        # Create model
        print("Creating model...")
        model = create_model(
            model_name=model_name,
            num_classes=num_classes,
            pretrained=False,
            dropout=dropout
        )
        model.load_state_dict(checkpoint['model_state_dict'])
        model = model.to(device)

        # Visualize predictions
        print("Generating predictions visualization...")
        data_loader = test_loader if args.split == 'test' else val_loader
        visualize_predictions(
            model, data_loader, device, class_names,
            num_images=args.num_images,
            save_path=args.output
        )

    elif args.mode == 'class_distribution':
        print("Loading data...")
        train_loader, val_loader, test_loader, num_classes, class_names = create_dataloaders(
            root_dir=args.data_dir,
            batch_size=32,
            img_size=384,
            num_workers=args.num_workers
        )

        data_loader = {'train': train_loader, 'val': val_loader, 'test': test_loader}[args.split]

        print(f"Plotting class distribution for {args.split} set...")
        visualize_class_distribution(data_loader, class_names, args.output)

    elif args.mode == 'sample_images':
        print("Loading data...")
        train_loader, val_loader, test_loader, num_classes, class_names = create_dataloaders(
            root_dir=args.data_dir,
            batch_size=32,
            img_size=384,
            num_workers=args.num_workers
        )

        data_loader = {'train': train_loader, 'val': val_loader, 'test': test_loader}[args.split]

        print(f"Visualizing sample images from {args.split} set...")
        visualize_sample_images(
            data_loader, class_names,
            samples_per_class=args.samples_per_class,
            save_path=args.output
        )

    print("Done!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Visualization utilities')

    parser.add_argument('--mode', type=str, required=True,
                        choices=['training_history', 'predictions', 'class_distribution', 'sample_images'],
                        help='Visualization mode')

    # General parameters
    parser.add_argument('--data_dir', type=str, default='./',
                        help='Root directory containing the dataset')
    parser.add_argument('--output', type=str, default=None,
                        help='Path to save the visualization')

    # Training history
    parser.add_argument('--log_dir', type=str, default=None,
                        help='TensorBoard log directory')

    # Predictions
    parser.add_argument('--checkpoint', type=str, default=None,
                        help='Path to model checkpoint')
    parser.add_argument('--split', type=str, default='test',
                        choices=['train', 'val', 'test'],
                        help='Dataset split to use')
    parser.add_argument('--num_images', type=int, default=16,
                        help='Number of images to visualize')
    parser.add_argument('--batch_size', type=int, default=32,
                        help='Batch size')
    parser.add_argument('--num_workers', type=int, default=4,
                        help='Number of data loading workers')

    # Model parameters (fallback)
    parser.add_argument('--model_name', type=str, default='vit_large_patch16_384',
                        help='Model architecture (fallback)')
    parser.add_argument('--img_size', type=int, default=384,
                        help='Input image size (fallback)')
    parser.add_argument('--dropout', type=float, default=0.3,
                        help='Dropout rate (fallback)')

    # Sample images
    parser.add_argument('--samples_per_class', type=int, default=3,
                        help='Number of sample images per class')

    args = parser.parse_args()

    main(args)
