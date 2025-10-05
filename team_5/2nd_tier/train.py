"""
Training script for skin cancer classification
Includes mixed precision training, learning rate scheduling, and comprehensive logging
"""
import os
import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.amp import GradScaler, autocast
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm
import numpy as np
from datetime import datetime

from dataset import create_dataloaders
from model import create_model
from metrics import MetricsCalculator, AverageMeter, print_metrics_summary


class FocalLoss(nn.Module):
    """
    Focal Loss for handling class imbalance
    https://arxiv.org/abs/1708.02002
    """

    def __init__(self, alpha=None, gamma=2.0, reduction='mean'):
        super(FocalLoss, self).__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, inputs, targets):
        ce_loss = nn.functional.cross_entropy(inputs, targets, reduction='none', weight=self.alpha)
        pt = torch.exp(-ce_loss)
        focal_loss = ((1 - pt) ** self.gamma) * ce_loss

        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss


class LabelSmoothingCrossEntropy(nn.Module):
    """
    Label Smoothing Cross Entropy Loss
    """

    def __init__(self, smoothing=0.1):
        super(LabelSmoothingCrossEntropy, self).__init__()
        self.smoothing = smoothing

    def forward(self, pred, target):
        confidence = 1.0 - self.smoothing
        logprobs = nn.functional.log_softmax(pred, dim=-1)
        nll_loss = -logprobs.gather(dim=-1, index=target.unsqueeze(1))
        nll_loss = nll_loss.squeeze(1)
        smooth_loss = -logprobs.mean(dim=-1)
        loss = confidence * nll_loss + self.smoothing * smooth_loss
        return loss.mean()


def train_epoch(model, train_loader, criterion, optimizer, scaler, device, epoch, writer):
    """Train for one epoch"""
    model.train()

    losses = AverageMeter()
    metrics_calc = MetricsCalculator(
        num_classes=len(train_loader.dataset.classes),
        class_names=train_loader.dataset.classes
    )

    pbar = tqdm(train_loader, desc=f'Epoch {epoch} [Train]')

    for batch_idx, (images, labels) in enumerate(pbar):
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        # Mixed precision training
        with autocast('cuda'):
            outputs = model(images)
            loss = criterion(outputs, labels)

        # Backward pass with gradient scaling
        optimizer.zero_grad()
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

        # Update metrics
        _, preds = torch.max(outputs, 1)
        probs = torch.softmax(outputs, dim=1)

        losses.update(loss.item(), images.size(0))
        metrics_calc.update(preds, labels, probs)

        # Update progress bar
        pbar.set_postfix({
            'loss': f'{losses.avg:.4f}',
        })

        # Log to tensorboard
        global_step = epoch * len(train_loader) + batch_idx
        if batch_idx % 10 == 0:
            writer.add_scalar('Train/BatchLoss', loss.item(), global_step)

    # Compute epoch metrics
    metrics = metrics_calc.compute()

    # Log epoch metrics to tensorboard
    writer.add_scalar('Train/Loss', losses.avg, epoch)
    writer.add_scalar('Train/Accuracy', metrics['accuracy'], epoch)
    writer.add_scalar('Train/F1_Macro', metrics['f1_macro'], epoch)
    writer.add_scalar('Train/F1_Weighted', metrics['f1_weighted'], epoch)

    return losses.avg, metrics


@torch.no_grad()
def validate(model, val_loader, criterion, device, epoch, writer, prefix='Val'):
    """Validate the model"""
    model.eval()

    losses = AverageMeter()
    metrics_calc = MetricsCalculator(
        num_classes=len(val_loader.dataset.classes),
        class_names=val_loader.dataset.classes
    )

    pbar = tqdm(val_loader, desc=f'Epoch {epoch} [{prefix}]')

    for images, labels in pbar:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        # Forward pass
        with autocast('cuda'):
            outputs = model(images)
            loss = criterion(outputs, labels)

        # Update metrics
        _, preds = torch.max(outputs, 1)
        probs = torch.softmax(outputs, dim=1)

        losses.update(loss.item(), images.size(0))
        metrics_calc.update(preds, labels, probs)

        pbar.set_postfix({
            'loss': f'{losses.avg:.4f}',
        })

    # Compute metrics
    metrics = metrics_calc.compute()

    # Log to tensorboard
    writer.add_scalar(f'{prefix}/Loss', losses.avg, epoch)
    writer.add_scalar(f'{prefix}/Accuracy', metrics['accuracy'], epoch)
    writer.add_scalar(f'{prefix}/F1_Macro', metrics['f1_macro'], epoch)
    writer.add_scalar(f'{prefix}/F1_Weighted', metrics['f1_weighted'], epoch)
    writer.add_scalar(f'{prefix}/Precision_Macro', metrics['precision_macro'], epoch)
    writer.add_scalar(f'{prefix}/Recall_Macro', metrics['recall_macro'], epoch)

    return losses.avg, metrics, metrics_calc


def main(args):
    # Set random seeds for reproducibility
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(args.seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    # Device configuration
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"Available GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

    # Create output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join(args.output_dir, f'{args.model_name}_{timestamp}')
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # TensorBoard writer
    writer = SummaryWriter(log_dir=os.path.join(output_dir, 'logs'))

    # Create dataloaders
    print("\nLoading data...")
    train_loader, val_loader, test_loader, num_classes, class_names = create_dataloaders(
        root_dir=args.data_dir,
        batch_size=args.batch_size,
        img_size=args.img_size,
        num_workers=args.num_workers
    )

    print(f"Number of classes: {num_classes}")
    print(f"Class names: {class_names}")
    print(f"Train samples: {len(train_loader.dataset)}")
    print(f"Val samples: {len(val_loader.dataset)}")
    print(f"Test samples: {len(test_loader.dataset)}")

    # Create model
    print(f"\nCreating model: {args.model_name}")
    model = create_model(
        model_name=args.model_name,
        num_classes=num_classes,
        pretrained=args.pretrained,
        dropout=args.dropout
    )
    model = model.to(device)

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")

    # Loss function
    if args.loss == 'focal':
        criterion = FocalLoss(gamma=args.focal_gamma)
        print(f"Using Focal Loss (gamma={args.focal_gamma})")
    elif args.loss == 'label_smoothing':
        criterion = LabelSmoothingCrossEntropy(smoothing=args.label_smoothing)
        print(f"Using Label Smoothing Cross Entropy (smoothing={args.label_smoothing})")
    else:
        criterion = nn.CrossEntropyLoss()
        print("Using Cross Entropy Loss")

    # Optimizer
    if args.optimizer == 'adamw':
        optimizer = optim.AdamW(
            model.parameters(),
            lr=args.lr,
            weight_decay=args.weight_decay
        )
    elif args.optimizer == 'sgd':
        optimizer = optim.SGD(
            model.parameters(),
            lr=args.lr,
            momentum=0.9,
            weight_decay=args.weight_decay
        )
    else:
        optimizer = optim.Adam(
            model.parameters(),
            lr=args.lr,
            weight_decay=args.weight_decay
        )

    print(f"Optimizer: {args.optimizer}, LR: {args.lr}, Weight Decay: {args.weight_decay}")

    # Learning rate scheduler
    if args.scheduler == 'cosine':
        scheduler = optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=args.epochs,
            eta_min=args.min_lr
        )
    elif args.scheduler == 'step':
        scheduler = optim.lr_scheduler.StepLR(
            optimizer,
            step_size=args.step_size,
            gamma=0.1
        )
    elif args.scheduler == 'reduce_plateau':
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode='min',
            factor=0.5,
            patience=args.patience,
            verbose=True
        )
    else:
        scheduler = None

    # Mixed precision scaler
    scaler = GradScaler('cuda')

    # Training loop
    best_val_f1 = 0.0
    best_val_acc = 0.0
    patience_counter = 0

    print(f"\nStarting training for {args.epochs} epochs...")
    print("=" * 80)

    for epoch in range(1, args.epochs + 1):
        print(f"\nEpoch {epoch}/{args.epochs}")
        print("-" * 80)

        # Train
        train_loss, train_metrics = train_epoch(
            model, train_loader, criterion, optimizer, scaler, device, epoch, writer
        )

        print(f"Train Loss: {train_loss:.4f}, Accuracy: {train_metrics['accuracy']:.4f}, "
              f"F1 (Macro): {train_metrics['f1_macro']:.4f}")

        # Validate
        val_loss, val_metrics, val_calc = validate(
            model, val_loader, criterion, device, epoch, writer, 'Val'
        )

        print(f"Val Loss: {val_loss:.4f}, Accuracy: {val_metrics['accuracy']:.4f}, "
              f"F1 (Macro): {val_metrics['f1_macro']:.4f}")

        # Learning rate scheduling
        if scheduler is not None:
            if args.scheduler == 'reduce_plateau':
                scheduler.step(val_loss)
            else:
                scheduler.step()

        current_lr = optimizer.param_groups[0]['lr']
        writer.add_scalar('Train/LearningRate', current_lr, epoch)
        print(f"Learning Rate: {current_lr:.6f}")

        # Save best model
        if val_metrics['f1_macro'] > best_val_f1:
            best_val_f1 = val_metrics['f1_macro']
            best_val_acc = val_metrics['accuracy']
            patience_counter = 0

            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict() if scheduler else None,
                'scaler_state_dict': scaler.state_dict(),
                'val_f1': best_val_f1,
                'val_acc': best_val_acc,
                'args': args
            }

            torch.save(checkpoint, os.path.join(output_dir, 'best_model.pth'))
            print(f"✓ Saved best model (F1: {best_val_f1:.4f})")

            # Save confusion matrix for best model
            val_calc.plot_confusion_matrix(
                save_path=os.path.join(output_dir, 'confusion_matrix_best.png'),
                normalize=True
            )
            val_calc.plot_per_class_metrics(
                save_path=os.path.join(output_dir, 'per_class_metrics_best.png')
            )
        else:
            patience_counter += 1

        # Save last checkpoint
        if epoch % args.save_freq == 0:
            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict() if scheduler else None,
                'scaler_state_dict': scaler.state_dict(),
                'val_f1': val_metrics['f1_macro'],
                'val_acc': val_metrics['accuracy'],
                'args': args
            }
            torch.save(checkpoint, os.path.join(output_dir, f'checkpoint_epoch_{epoch}.pth'))

        # Early stopping
        if args.early_stopping and patience_counter >= args.patience:
            print(f"\nEarly stopping triggered after {epoch} epochs")
            break

    print("\n" + "=" * 80)
    print("Training completed!")
    print(f"Best Validation F1: {best_val_f1:.4f}")
    print(f"Best Validation Accuracy: {best_val_acc:.4f}")
    print("=" * 80)

    # Final evaluation on test set
    print("\nEvaluating on test set...")
    checkpoint = torch.load(os.path.join(output_dir, 'best_model.pth'), weights_only=False)
    model.load_state_dict(checkpoint['model_state_dict'])

    test_loss, test_metrics, test_calc = validate(
        model, test_loader, criterion, device, epoch, writer, 'Test'
    )

    print_metrics_summary(test_metrics)
    print("\nDetailed Classification Report:")
    print(test_calc.get_classification_report())

    # Save test set visualizations
    test_calc.plot_confusion_matrix(
        save_path=os.path.join(output_dir, 'confusion_matrix_test.png'),
        normalize=True
    )
    test_calc.plot_per_class_metrics(
        save_path=os.path.join(output_dir, 'per_class_metrics_test.png')
    )

    # Save final results to text file
    with open(os.path.join(output_dir, 'results.txt'), 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("FINAL RESULTS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Model: {args.model_name}\n")
        f.write(f"Image Size: {args.img_size}\n")
        f.write(f"Batch Size: {args.batch_size}\n")
        f.write(f"Epochs: {epoch}\n\n")
        f.write("Test Set Metrics:\n")
        f.write("-" * 80 + "\n")
        for key, value in test_metrics.items():
            f.write(f"{key}: {value:.4f}\n")
        f.write("\n\nClassification Report:\n")
        f.write("-" * 80 + "\n")
        f.write(test_calc.get_classification_report())

    writer.close()
    print(f"\nResults saved to: {output_dir}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train skin cancer classification model')

    # Data parameters
    parser.add_argument('--data_dir', type=str, default='./',
                        help='Root directory containing the dataset')
    parser.add_argument('--output_dir', type=str, default='./outputs',
                        help='Directory to save outputs')

    # Model parameters
    parser.add_argument('--model_name', type=str, default='vit_large_patch16_384',
                        help='Model architecture to use')
    parser.add_argument('--pretrained', type=bool, default=True,
                        help='Use pretrained weights')
    parser.add_argument('--dropout', type=float, default=0.3,
                        help='Dropout rate')

    # Training parameters
    parser.add_argument('--epochs', type=int, default=50,
                        help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=16,
                        help='Batch size for training')
    parser.add_argument('--img_size', type=int, default=384,
                        help='Input image size')
    parser.add_argument('--num_workers', type=int, default=8,
                        help='Number of data loading workers')

    # Optimizer parameters
    parser.add_argument('--optimizer', type=str, default='adamw',
                        choices=['adam', 'adamw', 'sgd'],
                        help='Optimizer to use')
    parser.add_argument('--lr', type=float, default=1e-4,
                        help='Learning rate')
    parser.add_argument('--weight_decay', type=float, default=1e-4,
                        help='Weight decay')
    parser.add_argument('--min_lr', type=float, default=1e-6,
                        help='Minimum learning rate for cosine scheduler')

    # Scheduler parameters
    parser.add_argument('--scheduler', type=str, default='cosine',
                        choices=['cosine', 'step', 'reduce_plateau', 'none'],
                        help='Learning rate scheduler')
    parser.add_argument('--step_size', type=int, default=10,
                        help='Step size for StepLR scheduler')

    # Loss parameters
    parser.add_argument('--loss', type=str, default='focal',
                        choices=['ce', 'focal', 'label_smoothing'],
                        help='Loss function to use')
    parser.add_argument('--focal_gamma', type=float, default=2.0,
                        help='Gamma parameter for Focal Loss')
    parser.add_argument('--label_smoothing', type=float, default=0.1,
                        help='Label smoothing parameter')

    # Other parameters
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed')
    parser.add_argument('--save_freq', type=int, default=10,
                        help='Save checkpoint every N epochs')
    parser.add_argument('--early_stopping', type=bool, default=True,
                        help='Use early stopping')
    parser.add_argument('--patience', type=int, default=10,
                        help='Patience for early stopping')

    args = parser.parse_args()

    main(args)
