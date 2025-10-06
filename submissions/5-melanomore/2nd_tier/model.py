"""
State-of-the-art models for skin cancer classification
Using Vision Transformers and EfficientNet architectures
"""
import torch
import torch.nn as nn
import timm
from typing import Optional


class SkinCancerClassifier(nn.Module):
    """
    Skin cancer classifier using pretrained models from timm library
    Supports Vision Transformers (ViT), EfficientNet, and other state-of-the-art architectures
    """

    def __init__(
        self,
        model_name: str = 'vit_large_patch16_384',
        num_classes: int = 7,
        pretrained: bool = True,
        dropout: float = 0.3
    ):
        """
        Args:
            model_name: Name of the timm model to use
            num_classes: Number of output classes
            pretrained: Whether to use pretrained weights
            dropout: Dropout rate for the classifier head
        """
        super(SkinCancerClassifier, self).__init__()

        self.model_name = model_name
        self.num_classes = num_classes

        # Create the base model
        self.model = timm.create_model(
            model_name,
            pretrained=pretrained,
            num_classes=0,  # Remove the classifier head
            drop_rate=dropout
        )

        # Get the number of features from the model
        if hasattr(self.model, 'num_features'):
            num_features = self.model.num_features
        elif hasattr(self.model, 'head'):
            num_features = self.model.head.in_features
        else:
            # Fallback: pass a dummy input to get feature size
            with torch.no_grad():
                dummy_input = torch.randn(1, 3, 384, 384)
                num_features = self.model(dummy_input).shape[1]

        # Custom classifier head with dropout and batch normalization
        self.classifier = nn.Sequential(
            nn.Linear(num_features, 1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout / 2),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        # Extract features
        features = self.model(x)

        # Classify
        output = self.classifier(features)

        return output


def create_model(
    model_name: str = 'vit_large_patch16_384',
    num_classes: int = 7,
    pretrained: bool = True,
    dropout: float = 0.3
) -> SkinCancerClassifier:
    """
    Factory function to create a model

    Recommended models:
    - Vision Transformers (best for medical imaging):
        - 'vit_large_patch16_384' (recommended for 24GB VRAM)
        - 'vit_base_patch16_384'
        - 'vit_huge_patch14_224'

    - EfficientNet (efficient and accurate):
        - 'tf_efficientnetv2_l'
        - 'tf_efficientnetv2_m'
        - 'efficientnet_b7'

    - ConvNext (modern CNN):
        - 'convnext_large'
        - 'convnext_base'

    - Swin Transformer:
        - 'swin_large_patch4_window12_384'
        - 'swin_base_patch4_window12_384'

    Args:
        model_name: Name of the model architecture
        num_classes: Number of output classes
        pretrained: Use pretrained weights
        dropout: Dropout rate

    Returns:
        SkinCancerClassifier model
    """
    model = SkinCancerClassifier(
        model_name=model_name,
        num_classes=num_classes,
        pretrained=pretrained,
        dropout=dropout
    )

    return model


class EnsembleModel(nn.Module):
    """
    Ensemble of multiple models for better performance
    """

    def __init__(self, models: list, weights: Optional[list] = None):
        """
        Args:
            models: List of models to ensemble
            weights: Optional weights for each model's predictions
        """
        super(EnsembleModel, self).__init__()
        self.models = nn.ModuleList(models)

        if weights is None:
            self.weights = [1.0 / len(models)] * len(models)
        else:
            assert len(weights) == len(models), "Number of weights must match number of models"
            total = sum(weights)
            self.weights = [w / total for w in weights]

    def forward(self, x):
        # Get predictions from all models
        predictions = []
        for model in self.models:
            pred = model(x)
            predictions.append(pred)

        # Weighted average
        ensemble_pred = sum(w * pred for w, pred in zip(self.weights, predictions))

        return ensemble_pred


if __name__ == '__main__':
    # Test model creation
    print("Testing model creation...")

    # Test ViT Large
    model = create_model(
        model_name='vit_large_patch16_384',
        num_classes=7,
        pretrained=True,
        dropout=0.3
    )

    print(f"Model created: {model.model_name}")
    print(f"Number of parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(f"Trainable parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

    # Test forward pass
    dummy_input = torch.randn(2, 3, 384, 384)
    with torch.no_grad():
        output = model(dummy_input)
    print(f"Input shape: {dummy_input.shape}")
    print(f"Output shape: {output.shape}")

    # Test EfficientNet
    print("\nTesting EfficientNetV2...")
    model_eff = create_model(
        model_name='tf_efficientnetv2_l',
        num_classes=7,
        pretrained=True
    )
    print(f"EfficientNetV2 parameters: {sum(p.numel() for p in model_eff.parameters()):,}")
