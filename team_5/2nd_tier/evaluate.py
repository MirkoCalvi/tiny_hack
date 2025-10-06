"""
Evaluation and inference script for skin cancer classification
"""
import os
import argparse
import torch
from torch.amp import autocast
from tqdm import tqdm
import numpy as np
from PIL import Image

from dataset import create_dataloaders, get_transforms
from model import create_model
from metrics import MetricsCalculator, print_metrics_summary


@torch.no_grad()
def evaluate_model(model, data_loader, device, class_names):
    """
    Evaluate model on a dataset

    Args:
        model: The model to evaluate
        data_loader: DataLoader for the dataset
        device: Device to use
        class_names: List of class names

    Returns:
        metrics_calc: MetricsCalculator with all predictions
    """
    model.eval()

    metrics_calc = MetricsCalculator(
        num_classes=len(class_names),
        class_names=class_names
    )

    pbar = tqdm(data_loader, desc='Evaluating')

    for images, labels in pbar:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        # Forward pass
        with autocast('cuda'):
            outputs = model(images)

        # Get predictions
        _, preds = torch.max(outputs, 1)
        probs = torch.softmax(outputs, dim=1)

        # Update metrics
        metrics_calc.update(preds, labels, probs)

    return metrics_calc


def predict_single_image(model, image_path, transform, device, class_names):
    """
    Predict the class of a single image

    Args:
        model: The model to use
        image_path: Path to the image
        transform: Transform to apply to the image
        device: Device to use
        class_names: List of class names

    Returns:
        predicted_class, probabilities, predicted_idx
    """
    model.eval()

    # Load and preprocess image
    image = Image.open(image_path).convert('RGB')
    image_np = np.array(image)

    # Apply transform
    transformed = transform(image=image_np)
    image_tensor = transformed['image'].unsqueeze(0).to(device)

    # Predict
    with autocast('cuda'):
        with torch.no_grad():
            output = model(image_tensor)
            probs = torch.softmax(output, dim=1)

    # Get prediction
    _, predicted_idx = torch.max(probs, 1)
    predicted_idx = predicted_idx.item()
    predicted_class = class_names[predicted_idx]
    probabilities = probs.cpu().numpy()[0]

    return predicted_class, probabilities, predicted_idx


def main(args):
    # Device configuration
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    # Load checkpoint
    print(f"\nLoading checkpoint from {args.checkpoint}")
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)

    # Get saved arguments
    saved_args = checkpoint.get('args', None)

    # Determine model parameters
    if saved_args:
        model_name = saved_args.model_name
        img_size = saved_args.img_size
        dropout = saved_args.dropout
    else:
        model_name = args.model_name
        img_size = args.img_size
        dropout = args.dropout

    print(f"Model: {model_name}")
    print(f"Image size: {img_size}")

    # Load data if evaluating on dataset
    if args.mode == 'dataset':
        print("\nLoading data...")
        train_loader, val_loader, test_loader, num_classes, class_names = create_dataloaders(
            root_dir=args.data_dir,
            batch_size=args.batch_size,
            img_size=img_size,
            num_workers=args.num_workers
        )

        # Select dataset split
        if args.split == 'train':
            data_loader = train_loader
        elif args.split == 'val':
            data_loader = val_loader
        else:
            data_loader = test_loader

        print(f"Evaluating on {args.split} set ({len(data_loader.dataset)} samples)")

    # Single image mode
    elif args.mode == 'single':
        # Need to get class names somehow
        # Load from a small sample of the dataset
        _, _, _, num_classes, class_names = create_dataloaders(
            root_dir=args.data_dir,
            batch_size=1,
            img_size=img_size,
            num_workers=0
        )

    # Create model
    print(f"\nCreating model...")
    model = create_model(
        model_name=model_name,
        num_classes=num_classes if args.mode == 'dataset' else len(class_names),
        pretrained=False,  # We're loading trained weights
        dropout=dropout
    )

    # Load model weights
    model.load_state_dict(checkpoint['model_state_dict'])
    model = model.to(device)
    model.eval()

    print(f"Loaded checkpoint from epoch {checkpoint['epoch']}")
    if 'val_f1' in checkpoint:
        print(f"Checkpoint validation F1: {checkpoint['val_f1']:.4f}")
    if 'val_acc' in checkpoint:
        print(f"Checkpoint validation accuracy: {checkpoint['val_acc']:.4f}")

    # Evaluate
    if args.mode == 'dataset':
        print(f"\nEvaluating model on {args.split} set...")
        metrics_calc = evaluate_model(model, data_loader, device, class_names)

        # Compute and print metrics
        metrics = metrics_calc.compute()
        print_metrics_summary(metrics)

        print("\nDetailed Classification Report:")
        print(metrics_calc.get_classification_report())

        # Save visualizations if output directory specified
        if args.output_dir:
            os.makedirs(args.output_dir, exist_ok=True)

            print(f"\nSaving visualizations to {args.output_dir}...")
            metrics_calc.plot_confusion_matrix(
                save_path=os.path.join(args.output_dir, f'confusion_matrix_{args.split}.png'),
                normalize=True
            )
            metrics_calc.plot_per_class_metrics(
                save_path=os.path.join(args.output_dir, f'per_class_metrics_{args.split}.png')
            )

            # Save classification report to file
            with open(os.path.join(args.output_dir, f'classification_report_{args.split}.txt'), 'w') as f:
                f.write(metrics_calc.get_classification_report())

            print("Visualizations saved!")

    # Single image prediction
    elif args.mode == 'single':
        if not args.image_path:
            raise ValueError("--image_path is required for single image mode")

        print(f"\nPredicting class for: {args.image_path}")

        # Get transform
        transform = get_transforms(img_size=img_size, split='test')

        # Predict
        predicted_class, probabilities, predicted_idx = predict_single_image(
            model, args.image_path, transform, device, class_names
        )

        print("\n" + "=" * 80)
        print("PREDICTION RESULTS")
        print("=" * 80)
        print(f"\nPredicted Class: {predicted_class}")
        print(f"Confidence: {probabilities[predicted_idx]:.4f} ({probabilities[predicted_idx]*100:.2f}%)")
        print("\nClass Probabilities:")
        print("-" * 80)

        # Sort probabilities
        sorted_indices = np.argsort(probabilities)[::-1]
        for idx in sorted_indices:
            print(f"  {class_names[idx]:40s} {probabilities[idx]:.4f} ({probabilities[idx]*100:.2f}%)")

        print("=" * 80)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate skin cancer classification model')

    # Mode
    parser.add_argument('--mode', type=str, default='dataset',
                        choices=['dataset', 'single'],
                        help='Evaluation mode: dataset or single image')

    # Checkpoint
    parser.add_argument('--checkpoint', type=str, required=True,
                        help='Path to model checkpoint')

    # Dataset evaluation parameters
    parser.add_argument('--data_dir', type=str, default='./',
                        help='Root directory containing the dataset')
    parser.add_argument('--split', type=str, default='test',
                        choices=['train', 'val', 'test'],
                        help='Dataset split to evaluate on')
    parser.add_argument('--batch_size', type=int, default=32,
                        help='Batch size for evaluation')
    parser.add_argument('--num_workers', type=int, default=8,
                        help='Number of data loading workers')

    # Single image parameters
    parser.add_argument('--image_path', type=str, default=None,
                        help='Path to single image for prediction')

    # Model parameters (fallback if not in checkpoint)
    parser.add_argument('--model_name', type=str, default='vit_large_patch16_384',
                        help='Model architecture (fallback)')
    parser.add_argument('--img_size', type=int, default=384,
                        help='Input image size (fallback)')
    parser.add_argument('--dropout', type=float, default=0.3,
                        help='Dropout rate (fallback)')

    # Output
    parser.add_argument('--output_dir', type=str, default=None,
                        help='Directory to save evaluation results')

    args = parser.parse_args()

    main(args)
