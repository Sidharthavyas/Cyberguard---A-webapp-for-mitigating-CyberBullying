"""
ML inference pipeline for multilingual toxicity detection.
Uses ensemble of two models running locally on CPU (free tier).
Enhanced with intelligent ensemble logic and Gemini tiebreaker.
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
    """Ensemble toxicity detection using two local models with enhanced logic."""
    
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
    
    def _ensemble_decision(
        self, 
        primary_label: int, primary_conf: float, primary_bully_prob: float,
        secondary_label: int, secondary_conf: float, secondary_bully_prob: float,
        models_agree: bool, confidence_gap: float
    ) -> Tuple[int, float, float, str]:
        """
        Enhanced ensemble decision logic using weighted voting.
        
        Strategy:
        1. If both models agree with high confidence -> trust them
        2. If models disagree -> use weighted voting based on confidence
        3. If one model is very confident -> trust it more
        
        No language-specific hardcoding - works for all 40k+ multilingual dataset.
        
        Returns:
            Tuple of (final_label, final_confidence, final_bully_prob, source)
        """
        # Case 1: Both models agree
        if models_agree:
            # Use the higher confidence
            if primary_conf >= secondary_conf:
                return primary_label, primary_conf, primary_bully_prob, "local_ensemble"
            else:
                return secondary_label, secondary_conf, secondary_bully_prob, "local_ensemble"
        
        # Case 2: Models disagree - Use weighted voting
        # Weight by confidence and bullying probability
        primary_weight = primary_conf * (1 + primary_bully_prob)
        secondary_weight = secondary_conf * (1 + secondary_bully_prob)
        
        # If one model is significantly more confident, trust it
        confidence_ratio = max(primary_conf, secondary_conf) / (min(primary_conf, secondary_conf) + 0.01)
        
        if confidence_ratio > 1.5:  # One model is 50% more confident
            if primary_conf > secondary_conf:
                return primary_label, primary_conf, primary_bully_prob, "local_ensemble_weighted"
            else:
                return secondary_label, secondary_conf, secondary_bully_prob, "local_ensemble_weighted"
        
        # Otherwise, use weighted average of bullying probabilities
        total_weight = primary_weight + secondary_weight
        weighted_bully_prob = (
            (primary_bully_prob * primary_weight + secondary_bully_prob * secondary_weight) 
            / total_weight
        )
        
        # Apply threshold to weighted probability
        threshold = float(os.getenv("OPTIMAL_THRESHOLD", "0.5"))
        final_label = 1 if weighted_bully_prob >= threshold else 0
        
        # Confidence is the average of both confidences
        final_confidence = (primary_conf + secondary_conf) / 2
        
        return final_label, final_confidence, weighted_bully_prob, "local_ensemble_weighted"
    
    def _should_trigger_gemini(
        self,
        final_confidence: float,
        models_agree: bool,
        confidence_gap: float,
        primary_bully_prob: float,
        secondary_bully_prob: float
    ) -> bool:
        """
        Determine if Gemini fallback should be triggered.
        
        Triggers Gemini when:
        1. Models disagree on classification
        2. Low confidence from ensemble (<0.7)
        3. High confidence gap between models (>0.3)
        4. Borderline case (probabilities near threshold)
        
        Language-agnostic logic - no hardcoded rules.
        
        Args:
            final_confidence: Final ensemble confidence
            models_agree: Whether models agree on label
            confidence_gap: Absolute difference in bullying probabilities
            primary_bully_prob: Primary model bullying probability
            secondary_bully_prob: Secondary model bullying probability
            
        Returns:
            True if Gemini should be triggered, False otherwise
        """
        # Get configurable thresholds
        min_confidence = float(os.getenv("GEMINI_MIN_CONFIDENCE", "0.7"))
        max_confidence_gap = float(os.getenv("GEMINI_MAX_GAP", "0.3"))
        threshold = float(os.getenv("OPTIMAL_THRESHOLD", "0.5"))
        borderline_margin = float(os.getenv("GEMINI_BORDERLINE_MARGIN", "0.15"))
        
        # Trigger conditions
        low_confidence = final_confidence < min_confidence
        high_gap = confidence_gap > max_confidence_gap
        disagreement = not models_agree
        
        # Check if either probability is near the threshold (borderline case)
        is_borderline = (
            abs(primary_bully_prob - threshold) < borderline_margin or
            abs(secondary_bully_prob - threshold) < borderline_margin
        )
        
        # Trigger if any condition is met
        should_trigger = disagreement or low_confidence or high_gap or is_borderline
        
        if should_trigger:
            logger.debug(
                f"Gemini trigger analysis - "
                f"Disagreement: {disagreement}, "
                f"Low confidence: {low_confidence}, "
                f"High gap: {high_gap}, "
                f"Borderline: {is_borderline}"
            )
        
        return should_trigger
    
    def analyze(self, text: str) -> Dict:
        """
        Analyze text for toxicity using enhanced ensemble ML models and Gemini fallback.
        Uses binary classification: 0=safe, 1=bullying
        
        Enhanced ensemble logic:
        - Weighted voting based on model confidence
        - Agreement analysis between models
        - Smart Gemini fallback for edge cases
        - No hardcoded language-specific rules (works for all 40+ languages)
        
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
        
        # Calculate model agreement
        models_agree = (primary_label == secondary_label)
        confidence_gap = abs(primary_bully_prob - secondary_bully_prob)
        
        # Enhanced ensemble decision logic
        final_label, final_confidence, final_bully_prob, source = self._ensemble_decision(
            primary_label, primary_conf, primary_bully_prob,
            secondary_label, secondary_conf, secondary_bully_prob,
            models_agree, confidence_gap
        )
        
        # GEMINI FALLBACK LOGIC - Only for uncertain or disagreement cases
        should_use_gemini = self._should_trigger_gemini(
            final_confidence, models_agree, confidence_gap, 
            primary_bully_prob, secondary_bully_prob
        )
        
        if should_use_gemini and self.gemini.initialized:
            logger.info(
                f"Triggering Gemini fallback - "
                f"Confidence: {final_confidence:.2f}, "
                f"Agreement: {models_agree}, "
                f"Gap: {confidence_gap:.2f}"
            )
            gemini_result = self.gemini.analyze(text)
            
            if gemini_result:
                # Gemini returns 1-5, convert to binary (1-2=safe, 3-5=bullying)
                gemini_level = gemini_result['abuse_level']
                gemini_conf = gemini_result['confidence']
                gemini_label = 1 if gemini_level >= 3 else 0
                
                # Use Gemini as tiebreaker or confidence booster
                if gemini_conf > 0.75:  # Only trust high-confidence Gemini results
                    # If models disagree, use Gemini as tiebreaker
                    if not models_agree:
                        final_label = gemini_label
                        final_confidence = gemini_conf
                        final_bully_prob = gemini_conf if gemini_label == 1 else (1 - gemini_conf)
                        source = "gemini_tiebreaker"
                        logger.info(f"Gemini tiebreaker: Label {gemini_label} ({gemini_conf:.2f})")
                    # If models agree but low confidence, boost confidence
                    elif final_confidence < 0.7 and gemini_label == final_label:
                        # Average the confidences for a more reliable score
                        final_confidence = (final_confidence + gemini_conf) / 2
                        source = "gemini_boosted"
                        logger.info(f"Gemini confidence boost: {final_confidence:.2f}")
        
        logger.info(
            f"Analysis complete ({source}) - Language: {language}, "
            f"Primary: L{primary_label}({primary_conf:.2f}), "
            f"Secondary: L{secondary_label}({secondary_conf:.2f}), "
            f"Final: L{final_label}({final_confidence:.2f}), "
            f"Agreement: {models_agree}"
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
            "models_agree": models_agree,
            "confidence_gap": confidence_gap,
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
