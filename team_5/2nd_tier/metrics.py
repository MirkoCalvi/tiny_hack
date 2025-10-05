"""
Comprehensive metrics for skin cancer classification evaluation
"""
import torch
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_auc_score,
    cohen_kappa_score
)
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple


class MetricsCalculator:
    """Calculate and store various classification metrics"""

    def __init__(self, num_classes: int, class_names: List[str]):
        self.num_classes = num_classes
        self.class_names = class_names
        self.reset()

    def reset(self):
        """Reset all stored predictions and labels"""
        self.all_preds = []
        self.all_labels = []
        self.all_probs = []

    def update(self, predictions: torch.Tensor, labels: torch.Tensor, probabilities: torch.Tensor = None):
        """
        Update metrics with new batch of predictions

        Args:
            predictions: Predicted class indices
            labels: True labels
            probabilities: Class probabilities (optional, for AUC calculation)
        """
        self.all_preds.extend(predictions.detach().cpu().numpy())
        self.all_labels.extend(labels.detach().cpu().numpy())
        if probabilities is not None:
            self.all_probs.extend(probabilities.detach().cpu().numpy())

    def compute(self) -> Dict[str, float]:
        """
        Compute all metrics

        Returns:
            Dictionary containing all computed metrics
        """
        preds = np.array(self.all_preds)
        labels = np.array(self.all_labels)

        metrics = {
            'accuracy': accuracy_score(labels, preds),
            'precision_macro': precision_score(labels, preds, average='macro', zero_division=0),
            'precision_weighted': precision_score(labels, preds, average='weighted', zero_division=0),
            'recall_macro': recall_score(labels, preds, average='macro', zero_division=0),
            'recall_weighted': recall_score(labels, preds, average='weighted', zero_division=0),
            'f1_macro': f1_score(labels, preds, average='macro', zero_division=0),
            'f1_weighted': f1_score(labels, preds, average='weighted', zero_division=0),
            'cohen_kappa': cohen_kappa_score(labels, preds),
        }

        # Per-class metrics
        precision_per_class = precision_score(labels, preds, average=None, zero_division=0)
        recall_per_class = recall_score(labels, preds, average=None, zero_division=0)
        f1_per_class = f1_score(labels, preds, average=None, zero_division=0)

        for idx, class_name in enumerate(self.class_names):
            metrics[f'precision_{class_name}'] = precision_per_class[idx]
            metrics[f'recall_{class_name}'] = recall_per_class[idx]
            metrics[f'f1_{class_name}'] = f1_per_class[idx]

        # AUC if probabilities are available
        if len(self.all_probs) > 0:
            probs = np.array(self.all_probs)
            try:
                # One-vs-rest AUC for multiclass
                metrics['auc_macro'] = roc_auc_score(
                    labels, probs, multi_class='ovr', average='macro'
                )
                metrics['auc_weighted'] = roc_auc_score(
                    labels, probs, multi_class='ovr', average='weighted'
                )
            except ValueError:
                # Not all classes present in predictions
                pass

        return metrics

    def get_confusion_matrix(self) -> np.ndarray:
        """Get confusion matrix"""
        return confusion_matrix(self.all_labels, self.all_preds)

    def get_classification_report(self) -> str:
        """Get detailed classification report"""
        return classification_report(
            self.all_labels,
            self.all_preds,
            target_names=self.class_names,
            zero_division=0
        )

    def plot_confusion_matrix(self, save_path: str = None, normalize: bool = True):
        """
        Plot confusion matrix

        Args:
            save_path: Path to save the plot
            normalize: Whether to normalize the confusion matrix
        """
        cm = self.get_confusion_matrix()

        if normalize:
            cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
            fmt = '.2%'
            title = 'Normalized Confusion Matrix'
        else:
            fmt = 'd'
            title = 'Confusion Matrix'

        plt.figure(figsize=(12, 10))
        sns.heatmap(
            cm,
            annot=True,
            fmt=fmt,
            cmap='Blues',
            xticklabels=self.class_names,
            yticklabels=self.class_names,
            cbar_kws={'label': 'Proportion' if normalize else 'Count'}
        )
        plt.title(title, fontsize=16, pad=20)
        plt.ylabel('True Label', fontsize=12)
        plt.xlabel('Predicted Label', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Confusion matrix saved to {save_path}")

        return plt.gcf()

    def plot_per_class_metrics(self, save_path: str = None):
        """
        Plot per-class precision, recall, and F1 scores

        Args:
            save_path: Path to save the plot
        """
        metrics = self.compute()

        precision_values = [metrics[f'precision_{name}'] for name in self.class_names]
        recall_values = [metrics[f'recall_{name}'] for name in self.class_names]
        f1_values = [metrics[f'f1_{name}'] for name in self.class_names]

        x = np.arange(len(self.class_names))
        width = 0.25

        fig, ax = plt.subplots(figsize=(14, 6))
        ax.bar(x - width, precision_values, width, label='Precision', alpha=0.8)
        ax.bar(x, recall_values, width, label='Recall', alpha=0.8)
        ax.bar(x + width, f1_values, width, label='F1-Score', alpha=0.8)

        ax.set_xlabel('Class', fontsize=12)
        ax.set_ylabel('Score', fontsize=12)
        ax.set_title('Per-Class Performance Metrics', fontsize=16, pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(self.class_names, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim([0, 1.05])

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Per-class metrics plot saved to {save_path}")

        return fig


def print_metrics_summary(metrics: Dict[str, float]):
    """
    Print a formatted summary of metrics

    Args:
        metrics: Dictionary of computed metrics
    """
    print("\n" + "=" * 80)
    print("METRICS SUMMARY".center(80))
    print("=" * 80)

    # Overall metrics
    print("\nOverall Metrics:")
    print("-" * 80)
    print(f"  Accuracy:              {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
    print(f"  Precision (Macro):     {metrics['precision_macro']:.4f}")
    print(f"  Precision (Weighted):  {metrics['precision_weighted']:.4f}")
    print(f"  Recall (Macro):        {metrics['recall_macro']:.4f}")
    print(f"  Recall (Weighted):     {metrics['recall_weighted']:.4f}")
    print(f"  F1-Score (Macro):      {metrics['f1_macro']:.4f}")
    print(f"  F1-Score (Weighted):   {metrics['f1_weighted']:.4f}")
    print(f"  Cohen's Kappa:         {metrics['cohen_kappa']:.4f}")

    if 'auc_macro' in metrics:
        print(f"  AUC (Macro):           {metrics['auc_macro']:.4f}")
        print(f"  AUC (Weighted):        {metrics['auc_weighted']:.4f}")

    print("=" * 80 + "\n")


class AverageMeter:
    """Computes and stores the average and current value"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


if __name__ == '__main__':
    # Test metrics calculator
    num_classes = 7
    class_names = ['Class_A', 'Class_B', 'Class_C', 'Class_D', 'Class_E', 'Class_F', 'Class_G']

    calc = MetricsCalculator(num_classes, class_names)

    # Simulate some predictions
    for _ in range(10):
        preds = torch.randint(0, num_classes, (32,))
        labels = torch.randint(0, num_classes, (32,))
        probs = torch.nn.functional.softmax(torch.randn(32, num_classes), dim=1)

        calc.update(preds, labels, probs)

    # Compute metrics
    metrics = calc.compute()
    print_metrics_summary(metrics)

    # Print classification report
    print("\nClassification Report:")
    print(calc.get_classification_report())
