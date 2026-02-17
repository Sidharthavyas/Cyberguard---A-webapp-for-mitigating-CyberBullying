"""
ML inference pipeline for multilingual cyberbullying detection.
Uses a single finetuned MuRIL model — no ensemble, no Gemini.
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import logging
from typing import Dict
from langdetect import detect, LangDetectException
import os

logger = logging.getLogger(__name__)


class ToxicityDetector:
    """Cyberbullying detection using finetuned MuRIL model."""
    
    def __init__(self):
        self.device = "cpu"  # FREE TIER: CPU-only inference
        logger.info(f"Using device: {self.device}")
        
        # Load finetuned MuRIL model
        MODEL_NAME = "Sidhartha2004/finetuned_cyberbullying_muril"
        logger.info(f"Loading model: {MODEL_NAME}")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                MODEL_NAME
            ).to(self.device)
            self.model.eval()
            logger.info("✓ Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
        
        logger.info("Model ready for inference")
    
    def detect_language(self, text: str) -> str:
        """Detect language of input text."""
        try:
            return detect(text)
        except LangDetectException:
            logger.warning("Could not detect language, defaulting to 'unknown'")
            return "unknown"
    
    def _inference(self, text: str) -> tuple:
        """
        Run inference on finetuned MuRIL model.
        
        Model config: id2label = {0: "Safe", 1: "Bullying"}
        
        Args:
            text: Input text (should be cleaned — no @mentions/URLs)
            
        Returns:
            Tuple of (label, confidence, bullying_probability)
        """
        try:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=128,
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
            
            safe_prob = probs[0][0].item()
            bullying_prob = probs[0][1].item()
            
            # Apply configurable threshold
            threshold = float(os.getenv("OPTIMAL_THRESHOLD", "0.5"))
            predicted_label = 1 if bullying_prob >= threshold else 0
            confidence = bullying_prob if predicted_label == 1 else safe_prob
            
            return predicted_label, confidence, bullying_prob
            
        except Exception as e:
            logger.error(f"Model inference error: {e}")
            return 0, 0.0, 0.0
    
    def analyze(self, text: str) -> Dict:
        """
        Analyze text for cyberbullying using finetuned MuRIL.
        Binary classification: 0=safe, 1=bullying
        
        Args:
            text: Input text to analyze (pre-cleaned by moderation engine)
            
        Returns:
            Dictionary with analysis results
        """
        # Detect language
        language = self.detect_language(text)
        
        # Run model inference
        label, confidence, bullying_prob = self._inference(text)
        
        logger.info(
            f"Analysis — Language: {language}, "
            f"Label: {'BULLYING' if label == 1 else 'SAFE'}, "
            f"Confidence: {confidence:.2f}, "
            f"Bullying prob: {bullying_prob:.2f}"
        )
        
        return {
            "language": language,
            "label": label,                    # 0=safe, 1=bullying
            "label_name": "BULLYING" if label == 1 else "SAFE",
            "confidence": confidence,
            "bullying_probability": bullying_prob,
            # Keep these keys for backward compatibility with moderation.py
            "primary_label": label,
            "primary_confidence": confidence,
            "secondary_label": label,          # Same as primary (no secondary)
            "secondary_confidence": confidence,
            "models_agree": True,              # Only one model
            "confidence_gap": 0.0,
            "source": "finetuned_muril"
        }


# Global singleton instance (lazy loading)
detector = None


def get_detector() -> ToxicityDetector:
    """Get or create the global detector instance."""
    global detector
    if detector is None:
        logger.info("Initializing toxicity detector...")
        detector = ToxicityDetector()
    return detector
