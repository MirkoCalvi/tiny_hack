"""
Lesion classification using the trained skin cancer detection model.
Integrates SkinCancerPredictor from inference_api.py
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

LOGGER = logging.getLogger("nicla.classifier")


@dataclass
class PredictionResult:
    """Result of a classification prediction."""
    
    label: str
    confidence: float
    provider: str
    model_version: Optional[str] = None
    raw_predictions: Optional[List[Dict[str, Any]]] = None
    latency_ms: Optional[float] = None


class BaseClassifier:
    """Base class for lesion classifiers."""
    
    def predict(
        self, 
        image_path: Path, 
        suspicious_score: Optional[float] = None
    ) -> PredictionResult:
        """
        Predict the lesion type from an image.
        
        Args:
            image_path: Path to the image file
            suspicious_score: Optional suspicious score from Nicla Vision (0-1)
            
        Returns:
            PredictionResult with classification details
        """
        raise NotImplementedError


class RealLesionClassifier(BaseClassifier):
    """
    Real classifier using the trained deep learning model.
    Uses SkinCancerPredictor from inference_api.py
    """
    
    def __init__(self, class_labels: List[str], model_path: Optional[Path] = None):
        """
        Initialize the classifier with the trained model.
        
        Args:
            class_labels: List of class names (expected order)
            model_path: Path to best_model.pth file. If None, uses default location.
        """
        self.class_labels = class_labels
        
        # Import SkinCancerPredictor
        try:
            import sys
            models_dir = Path(__file__).parent / "models"
            if str(models_dir) not in sys.path:
                sys.path.insert(0, str(models_dir))
            
            from inference_api import SkinCancerPredictor
            
            # Default model path
            if model_path is None:
                model_path = Path(__file__).parent / "models" / "best_model.pth"
            
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Model file not found: {model_path}. "
                    f"Please ensure best_model.pth is in the models directory."
                )
            
            LOGGER.info(f"Loading skin cancer detection model from {model_path}")
            self.predictor = SkinCancerPredictor(str(model_path))
            self.model_version = "vit_large_patch16_384_v1"
            LOGGER.info("Model loaded successfully!")
            
        except ImportError as exc:
            raise RuntimeError(
                f"Failed to import SkinCancerPredictor: {exc}. "
                f"Make sure inference_api.py is in the models directory."
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Failed to load model: {exc}") from exc
    
    def predict(
        self, 
        image_path: Path, 
        suspicious_score: Optional[float] = None
    ) -> PredictionResult:
        """
        Predict lesion type using the trained model.
        
        Args:
            image_path: Path to the image file
            suspicious_score: Optional suspicious score (not used by this model)
            
        Returns:
            PredictionResult with classification details
        """
        start_time = time.time()
        
        try:
            # Run inference using the predictor
            result = self.predictor.predict(str(image_path))
            
            # Get top 3 predictions for additional context
            top_3 = self.predictor.predict_top_k(str(image_path), k=3)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Build raw predictions list
            raw_predictions = [
                {
                    "class": pred["class"],
                    "friendly_name": pred["friendly_name"],
                    "confidence": pred["confidence"]
                }
                for pred in top_3
            ]
            
            return PredictionResult(
                label=result["predicted_class"],
                confidence=result["confidence"],
                provider="SkinCancerPredictor",
                model_version=self.model_version,
                raw_predictions=raw_predictions,
                latency_ms=latency_ms
            )
            
        except Exception as exc:
            LOGGER.error(f"Prediction failed for {image_path}: {exc}")
            raise RuntimeError(f"Model prediction failed: {exc}") from exc


class MockLesionClassifier(BaseClassifier):
    """
    Mock classifier for testing and fallback.
    Returns random predictions from the class list.
    """
    
    def __init__(self, class_labels: List[str]):
        self.class_labels = class_labels
        LOGGER.warning("Using MOCK classifier - predictions are random!")
    
    def predict(
        self, 
        image_path: Path, 
        suspicious_score: Optional[float] = None
    ) -> PredictionResult:
        """
        Generate a mock prediction.
        
        Args:
            image_path: Path to the image file (not actually used)
            suspicious_score: Optional suspicious score (influences mock confidence)
            
        Returns:
            PredictionResult with random classification
        """
        # Random class selection
        label = random.choice(self.class_labels)
        
        # Base confidence: higher if suspicious_score is provided
        if suspicious_score is not None:
            base_confidence = 0.5 + (suspicious_score * 0.4)
        else:
            base_confidence = random.uniform(0.6, 0.95)
        
        confidence = min(0.99, base_confidence + random.uniform(-0.1, 0.1))
        
        # Generate mock raw predictions
        raw_predictions = []
        remaining_prob = 1.0 - confidence
        
        for cls in self.class_labels[:3]:
            if cls == label:
                raw_predictions.append({
                    "class": cls,
                    "friendly_name": cls.replace("_", " ").title(),
                    "confidence": confidence
                })
            else:
                prob = remaining_prob * random.uniform(0.3, 0.7)
                raw_predictions.append({
                    "class": cls,
                    "friendly_name": cls.replace("_", " ").title(),
                    "confidence": prob
                })
                remaining_prob -= prob
        
        # Sort by confidence
        raw_predictions.sort(key=lambda x: x["confidence"], reverse=True)
        
        return PredictionResult(
            label=label,
            confidence=confidence,
            provider="MockClassifier",
            model_version="mock_v1",
            raw_predictions=raw_predictions[:3],
            latency_ms=random.uniform(50, 150)
        )


def load_classifier(
    class_labels: List[str], 
    model_path: Optional[Path] = None,
    force_mock: bool = False
) -> BaseClassifier:
    """
    Load the appropriate classifier.
    
    Args:
        class_labels: List of class names
        model_path: Optional path to the model file
        force_mock: If True, always use the mock classifier
        
    Returns:
        A BaseClassifier instance (Real or Mock)
    """
    if force_mock:
        LOGGER.info("Force mock enabled - using MockLesionClassifier")
        return MockLesionClassifier(class_labels)
    
    try:
        return RealLesionClassifier(class_labels, model_path)
    except Exception as exc:
        LOGGER.error(f"Failed to load real classifier: {exc}")
        LOGGER.warning("Falling back to MockLesionClassifier")
        return MockLesionClassifier(class_labels)
