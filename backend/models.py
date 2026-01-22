"""
ML inference pipeline for multilingual toxicity detection.
Uses ensemble of two models running locally on CPU (free tier).
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import logging
from typing import Tuple, Dict
from langdetect import detect, LangDetectException

import os
import google.generativeai as genai
from typing import Tuple, Dict, Optional

logger = logging.getLogger(__name__)


class GeminiModerator:
    """Fallback moderator using Google's Gemini Flash."""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = "gemini-2.5-flash"  # Updated to 2026 model
        self.initialized = False
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                self.initialized = True
                logger.info(f"✓ Gemini Moderator initialized with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        else:
            logger.warning("GEMINI_API_KEY not found. Fallback moderation disabled.")
    
    def analyze(self, text: str) -> Optional[Dict]:
        """
        Analyze text using Gemini API.
        
        Returns:
            Dict with 'abuse_level' (1-5) and 'confidence' (0.0-1.0)
            or None if API call fails.
        """
        if not self.initialized:
            return None
            
        try:
            prompt = f"""
            Analyze the toxicity of the following text on a scale of 1 to 5.
            
            1: Safe, non-toxic, friendly, or neutral.
            2: Low risk, mild criticism, sarcasm without malice.
            3: Flagged, potentially offensive, rude, heated argument.
            4: High risk, hate speech, severe insults, harassment.
            5: Severe, dangerous content, explicit threats, extreme hate speech.
            
            Text: "{text}"
            
            Return ONLY a JSON object with two fields: "level" (integer 1-5) and "confidence" (float 0.0-1.0).
            """
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Simple parsing of the JSON-like response
            # Using clean string manipulation to avoid JSON parse errors from LLM extra text
            import json
            import re
            
            # Find JSON pattern
            match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if match:
                json_str = match.group(0)
                data = json.loads(json_str)
                return {
                    "abuse_level": int(data.get("level", 1)),
                    "confidence": float(data.get("confidence", 0.0))
                }
            else:
                logger.warning(f"Could not parse Gemini response: {result_text}")
                return None
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None


class ToxicityDetector:
    """Ensemble toxicity detection using two local models."""
    
    def __init__(self):
        self.device = "cpu"  # FREE TIER: CPU-only inference
        logger.info(f"Using device: {self.device}")
        
        # Initialize Gemini for fallback
        self.gemini = GeminiModerator()
        
        # Primary model: Fine-tuned MuRIL for Indian languages
        logger.info("Loading primary model: Sidhartha2004/finetuned_cyberbullying_muril")
        try:
            self.primary_tokenizer = AutoTokenizer.from_pretrained(
                "Sidhartha2004/finetuned_cyberbullying_muril"
            )
            self.primary_model = AutoModelForSequenceClassification.from_pretrained(
                "Sidhartha2004/finetuned_cyberbullying_muril"
            ).to(self.device)
            self.primary_model.eval()
            logger.info("✓ Primary model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load primary model: {e}")
            raise
        
        # Secondary model: Toxic-BERT for English
        logger.info("Loading secondary model: unitary/toxic-bert")
        try:
            self.secondary_tokenizer = AutoTokenizer.from_pretrained(
                "unitary/toxic-bert"
            )
            self.secondary_model = AutoModelForSequenceClassification.from_pretrained(
                "unitary/toxic-bert"
            ).to(self.device)
            self.secondary_model.eval()
            logger.info("✓ Secondary model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load secondary model: {e}")
            raise
        
        logger.info("All models loaded and ready for inference")
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of input text.
        
        Args:
            text: Input text
            
        Returns:
            ISO language code (e.g., 'en', 'hi', 'te')
        """
        try:
            lang = detect(text)
            return lang
        except LangDetectException:
            logger.warning("Could not detect language, defaulting to 'unknown'")
            return "unknown"
    
    def _primary_inference(self, text: str) -> Tuple[int, float, float]:
        """
        Run inference on primary model (MuRIL) with optimal threshold.
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (label, confidence, bullying_probability)
            - label: 0=safe, 1=bullying
            - confidence: probability of predicted class
            - bullying_probability: raw probability of bullying class
        """
        try:
            inputs = self.primary_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=128,  # Optimal for MuRIL
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.primary_model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
            
            # Get probabilities for both classes
            safe_prob = probs[0][0].item()
            bullying_prob = probs[0][1].item()
            
            # Apply optimal threshold (default 0.5, configurable via env)
            threshold = float(os.getenv("OPTIMAL_THRESHOLD", "0.5"))
            predicted_label = 1 if bullying_prob >= threshold else 0
            confidence = bullying_prob if predicted_label == 1 else safe_prob
            
            return predicted_label, confidence, bullying_prob
            
        except Exception as e:
            logger.error(f"Primary model inference error: {e}")
            return 0, 0.0, 0.0
    
    def _secondary_inference(self, text: str) -> Tuple[int, float, float]:
        """
        Run inference on secondary model (Toxic-BERT) with optimal threshold.
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (label, confidence, bullying_probability)
            - label: 0=safe, 1=bullying
            - confidence: probability of predicted class
            - bullying_probability: raw probability of bullying class
        """
        try:
            inputs = self.secondary_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=128,
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.secondary_model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
            
            # Get probabilities for both classes
            safe_prob = probs[0][0].item()
            bullying_prob = probs[0][1].item()
            
            # Apply optimal threshold
            threshold = float(os.getenv("OPTIMAL_THRESHOLD", "0.5"))
            predicted_label = 1 if bullying_prob >= threshold else 0
            confidence = bullying_prob if predicted_label == 1 else safe_prob
            
            return predicted_label, confidence, bullying_prob
            
        except Exception as e:
            logger.error(f"Secondary model inference error: {e}")
            return 0, 0.0, 0.0
    
    def analyze(self, text: str) -> Dict:
        """
        Analyze text for toxicity using ensemble ML models and Gemini fallback.
        Uses binary classification: 0=safe, 1=bullying
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary with analysis results including binary label
        """
        # Detect language
        language = self.detect_language(text)
        
        # Run both local ML models
        primary_label, primary_conf, primary_bully_prob = self._primary_inference(text)
        secondary_label, secondary_conf, secondary_bully_prob = self._secondary_inference(text)
        
        # Ensemble: Take maximum label (if either says bullying, flag as bullying)
        final_label = max(primary_label, secondary_label)
        
        # Use confidence from the model that gave higher bullying probability
        if primary_bully_prob >= secondary_bully_prob:
            final_confidence = primary_conf
            final_bully_prob = primary_bully_prob
        else:
            final_confidence = secondary_conf
            final_bully_prob = secondary_bully_prob
            
        source = "local_ensemble"
        
        # GEMINI FALLBACK LOGIC
        # If low confidence OR if models disagree on classification
        is_uncertain = final_confidence < 0.7
        disagreement = primary_label != secondary_label
        
        if (is_uncertain or disagreement) and self.gemini.initialized:
            logger.info(f"Triggering Gemini fallback (Confidence: {final_confidence:.2f}, Disagreement: {disagreement})")
            gemini_result = self.gemini.analyze(text)
            
            if gemini_result:
                # Gemini returns 1-5, convert to binary (1-2=safe, 3-5=bullying)
                gemini_level = gemini_result['abuse_level']
                gemini_conf = gemini_result['confidence']
                gemini_label = 1 if gemini_level >= 3 else 0
                
                # If Gemini is confident, use its result
                if gemini_conf > 0.8:
                    final_label = gemini_label
                    final_confidence = gemini_conf
                    final_bully_prob = gemini_conf if gemini_label == 1 else (1 - gemini_conf)
                    source = "gemini_fallback"
                    logger.info(f"Gemini override applied: Label {gemini_label} ({gemini_conf:.2f})")
        
        logger.info(
            f"Analysis complete ({source}) - Language: {language}, "
            f"Primary: L{primary_label}({primary_conf:.2f}), "
            f"Secondary: L{secondary_label}({secondary_conf:.2f}), "
            f"Final: L{final_label}({final_confidence:.2f})"
        )
        
        return {
            "language": language,
            "label": final_label,  # 0=safe, 1=bullying
            "label_name": "BULLYING" if final_label == 1 else "SAFE",
            "confidence": final_confidence,
            "bullying_probability": final_bully_prob,
            "primary_label": primary_label,
            "primary_confidence": primary_conf,
            "secondary_label": secondary_label,
            "secondary_confidence": secondary_conf,
            "source": source
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
