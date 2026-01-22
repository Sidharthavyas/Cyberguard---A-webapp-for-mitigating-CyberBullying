"""
Production-ready cyberbullying filter with optimal threshold support.
Implements binary classification (0=safe, 1=bullying) based on learned optimal thresholds.
"""

import os
import torch
import logging
from typing import Dict, List, Optional
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)


class CyberbullyingFilter:
    """Production-ready cyberbullying filter with optimal threshold"""
    
    def __init__(
        self, 
        model_path: str = "Sidhartha2004/finetuned_cyberbullying_muril",
        threshold: Optional[float] = None,
        threshold_file: Optional[str] = None,
        device: str = "cpu"
    ):
        """
        Initialize the filter
        
        Args:
            model_path: Path to fine-tuned model (local or HuggingFace)
            threshold: Optimal threshold for classification (if None, loads from file or env)
            threshold_file: Path to optimal_threshold.txt (optional)
            device: Device for inference ('cpu' or 'cuda')
        """
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        logger.info(f"Initializing CyberbullyingFilter on device: {self.device}")
        
        # Load model and tokenizer
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"✓ Model loaded from: {model_path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
        
        # Load optimal threshold
        self.threshold = self._load_threshold(threshold, threshold_file)
        logger.info(f"✓ Using threshold: {self.threshold}")
    
    def _load_threshold(
        self, 
        threshold: Optional[float], 
        threshold_file: Optional[str]
    ) -> float:
        """
        Load optimal threshold from various sources
        
        Priority: 
        1. Explicit threshold parameter
        2. Threshold file
        3. Environment variable
        4. Default (0.5)
        """
        # 1. Explicit parameter
        if threshold is not None:
            return float(threshold)
        
        # 2. Threshold file
        if threshold_file and os.path.exists(threshold_file):
            try:
                with open(threshold_file, 'r') as f:
                    for line in f:
                        if line.startswith('optimal_threshold='):
                            return float(line.split('=')[1].strip())
            except Exception as e:
                logger.warning(f"Could not load threshold from file: {e}")
        
        # 3. Environment variable
        env_threshold = os.getenv("OPTIMAL_THRESHOLD")
        if env_threshold:
            try:
                return float(env_threshold)
            except ValueError:
                logger.warning(f"Invalid OPTIMAL_THRESHOLD in env: {env_threshold}")
        
        # 4. Default
        logger.warning("No threshold found, using default: 0.5")
        return 0.5
    
    def predict(
        self, 
        text: str, 
        return_probabilities: bool = False
    ) -> Dict:
        """
        Predict if text contains cyberbullying
        
        Args:
            text: Input text to classify
            return_probabilities: If True, return probabilities for both classes
            
        Returns:
            dict with 'label' (0=safe, 1=bullying), 'confidence', and optionally 'probabilities'
        """
        # Tokenize
        inputs = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=128,
            return_tensors='pt'
        ).to(self.device)
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)[0]
        
        # Apply optimal threshold
        safe_prob = probs[0].item()
        bullying_prob = probs[1].item()
        
        # Binary classification based on threshold
        predicted_label = 1 if bullying_prob >= self.threshold else 0
        confidence = bullying_prob if predicted_label == 1 else safe_prob
        
        result = {
            'label': predicted_label,
            'label_name': 'BULLYING' if predicted_label == 1 else 'SAFE',
            'confidence': round(confidence, 4),
            'bullying_probability': round(bullying_prob, 4),
            'safe_probability': round(safe_prob, 4)
        }
        
        if return_probabilities:
            result['probabilities'] = {
                'safe': round(safe_prob, 4),
                'bullying': round(bullying_prob, 4)
            }
        
        return result
    
    def batch_predict(
        self, 
        texts: List[str], 
        batch_size: int = 32
    ) -> List[Dict]:
        """
        Predict multiple texts efficiently
        
        Args:
            texts: List of texts to classify
            batch_size: Batch size for processing
            
        Returns:
            List of prediction dictionaries
        """
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Tokenize batch
            inputs = self.tokenizer(
                batch,
                truncation=True,
                padding='max_length',
                max_length=128,
                return_tensors='pt'
            ).to(self.device)
            
            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
            
            # Process each prediction
            for j, prob in enumerate(probs):
                safe_prob = prob[0].item()
                bullying_prob = prob[1].item()
                predicted_label = 1 if bullying_prob >= self.threshold else 0
                confidence = bullying_prob if predicted_label == 1 else safe_prob
                
                results.append({
                    'text': batch[j],
                    'label': predicted_label,
                    'label_name': 'BULLYING' if predicted_label == 1 else 'SAFE',
                    'confidence': round(confidence, 4),
                    'bullying_probability': round(bullying_prob, 4),
                    'safe_probability': round(safe_prob, 4)
                })
        
        return results
    
    def filter_content(
        self, 
        texts: List[str], 
        action: str = 'flag'
    ) -> Dict:
        """
        Filter a list of texts and take action on bullying content
        
        Args:
            texts: List of texts to filter
            action: 'flag', 'remove', or 'review'
            
        Returns:
            dict with filtered results and statistics
        """
        predictions = self.batch_predict(texts)
        
        safe_texts = []
        flagged_texts = []
        
        for pred in predictions:
            if pred['label'] == 0:
                safe_texts.append(pred)
            else:
                flagged_texts.append(pred)
        
        result = {
            'total': len(texts),
            'safe_count': len(safe_texts),
            'flagged_count': len(flagged_texts),
            'safe_texts': safe_texts if action != 'remove' else None,
            'flagged_texts': flagged_texts,
            'action_taken': action
        }
        
        return result
