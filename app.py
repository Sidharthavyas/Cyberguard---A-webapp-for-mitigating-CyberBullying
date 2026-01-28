"""
CyberGuard - Gradio App for Hugging Face Spaces
Multilingual cyberbullying detection using fine-tuned MuRIL model
"""

import gradio as gr
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.models import get_detector

# Set environment variables for HF Spaces
os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', '')

# Initialize detector (loads models)
print("🔄 Loading ML models...")
detector = get_detector()
print("✅ Models loaded successfully!")

def analyze_text(text):
    """Analyze text for cyberbullying."""
    if not text or len(text.strip()) == 0:
        return "⚠️ Please enter some text to analyze."
    
    try:
        result = detector.analyze(text)
        
        # Format output with color coding
        is_bullying = result['label'] == 1
        label_emoji = "🔴" if is_bullying else "✅"
        label_text = "BULLYING DETECTED" if is_bullying else "SAFE CONTENT"
        confidence = result['confidence'] * 100
        
        # Color code based on severity
        if is_bullying and confidence > 90:
            severity = "🚨 HIGH CONFIDENCE"
            color = "red"
        elif is_bullying and confidence > 70:
            severity = "⚠️ MEDIUM CONFIDENCE"
            color = "orange"
        elif is_bullying:
            severity = "⚡ LOW CONFIDENCE"
            color = "yellow"
        else:
            severity = "✨ SAFE"
            color = "green"
        
        # Source info
        source_emoji = {
            "local_ensemble": "🤖",
            "muril_primary": "🧠",
            "gemini_fallback": "🌟"
        }.get(result.get('source', 'muril_primary'), "🤖")
        
        # Build detailed response
        output = f"""
# {label_emoji} {label_text}

### {severity} - {confidence:.2f}%

---

### 📊 Analysis Details

| Property | Value |
|----------|-------|
| **Language Detected** | {result['language'].upper()} |
| **Classification** | {result['label_name']} |
| **Confidence Score** | {confidence:.2f}% |
| **Bullying Probability** | {result['bullying_probability']*100:.2f}% |
| **Analysis Source** | {source_emoji} {result.get('source', 'muril_primary').replace('_', ' ').title()} |

---

### 🔬 Model Performance

**Your Fine-tuned MuRIL Model:**
- ✅ Accuracy: **99.87%**
- ✅ F1 Score: **99.88%**
- ✅ Precision: **99.93%**
- ✅ Recall: **99.84%**

This model was fine-tuned on a comprehensive cyberbullying dataset and achieves state-of-the-art results across multiple languages including English, Hindi, Telugu, and more.

---

### 🛡️ What This Means

"""
        
        if is_bullying:
            output += """
**⚠️ This content has been flagged as potentially harmful.**

Recommended actions:
1. 🔍 Review the content carefully
2. ⚠️ Consider flagging for human review
3. 🗑️ May warrant deletion if confidence > 90%
4. 📝 Document the incident

**Note:** This is an automated system. Final moderation decisions should involve human judgment.
"""
        else:
            output += """
**✅ This content appears safe and non-harmful.**

The text does not contain detectable cyberbullying, hate speech, or harassment patterns.
"""
        
        return output
        
    except Exception as e:
        return f"❌ **Error during analysis:** {str(e)}\n\nPlease try again or contact support."

# Example texts for demonstration
examples = [
    ["Hey! How are you doing today?"],
    ["This is amazing work, keep it up!"],
    ["You're absolutely worthless and nobody likes you"],
    ["I hate you and wish you were never born"],
    ["मैं तुमसे नफरत करता हूं"],  # Hindi: I hate you
    ["तुम बेकार हो"],  # Hindi: You are useless
    ["నువ్వు మూర్ఖుడివి"],  # Telugu: You are a fool
    ["You should just disappear forever, loser"],
    ["Great job everyone, well done!"],
    ["Can't wait to see you tomorrow!"]
]

# Create Gradio interface
with gr.Blocks(theme=gr.themes.Soft(), css="""
    .gradio-container {font-family: 'Inter', sans-serif;}
    h1 {text-align: center; color: #FF6B6B;}
    .examples {border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px;}
""") as demo:
    
    gr.Markdown("""
    # 🛡️ CyberGuard
    ### Multilingual Cyberbullying Detection System
    
    Powered by **fine-tuned MuRIL model** with **99.87% accuracy** + **Gemini AI** fallback
    
    ---
    
    #### 🌍 Supported Languages
    English • Hindi • Telugu • Tamil • Malayalam • Marathi • Bengali • Gujarati • Kannada • Urdu • and more...
    
    #### 🎯 Model Performance
    - **Accuracy:** 99.87%
    - **F1 Score:** 99.88%
    - **Precision:** 99.93%
    - **Recall:** 99.84%
    
    #### 🔬 Technology Stack
    - Primary: `Sidhartha2004/finetuned_cyberbullying_muril` (MuRIL-based)
    - Fallback: Google Gemini 2.5 Flash
    - Framework: Transformers (HuggingFace)
    
    ---
    """)
    
    with gr.Row():
        with gr.Column(scale=2):
            input_text = gr.Textbox(
                label="📝 Enter text to analyze",
                placeholder="Type or paste any text here to check for cyberbullying...",
                lines=5,
                max_lines=10
            )
            
            analyze_btn = gr.Button(
                "🔍 Analyze for Cyberbullying",
                variant="primary",
                size="lg"
            )
            
            gr.Markdown("### 💡 Try these examples:")
            gr.Examples(
                examples=examples,
                inputs=input_text,
                label="Click any example to test",
                examples_per_page=5
            )
    
    with gr.Row():
        output_md = gr.Markdown(label="Analysis Result")
    
    # Button click handler
    analyze_btn.click(
        fn=analyze_text,
        inputs=input_text,
        outputs=output_md
    )
    
    # Also allow Enter key
    input_text.submit(
        fn=analyze_text,
        inputs=input_text,
        outputs=output_md
    )
    
    gr.Markdown("""
    ---
    
    ### ℹ️ About CyberGuard
    
    CyberGuard is an advanced cyberbullying detection system that uses state-of-the-art machine learning models to identify harmful content across multiple languages. The system combines:
    
    1. **Fine-tuned MuRIL Model** - Trained specifically on cyberbullying patterns with 99.87% accuracy
    2. **Gemini AI Fallback** - Provides additional validation for edge cases
    3. **Multilingual Support** - Works seamlessly across 10+ Indian and international languages
    
    #### 🎓 Model Training
    
    The primary model was fine-tuned using:
    - **Base Model:** Google's MuRIL (Multilingual Representations for Indian Languages)
    - **Training Data:** Comprehensive cyberbullying dataset
    - **Training:** 2 epochs with AdamW optimizer
    - **Optimization:** Cosine learning rate schedule with warmup
    - **Hardware:** Mixed precision training on modern GPUs
    
    #### 📊 Evaluation Metrics
    
    | Metric | Score |
    |--------|-------|
    | Accuracy | 99.87% |
    | F1 Score | 99.88% |
    | Precision | 99.93% |
    | Recall | 99.84% |
    | Specificity | 99.91% |
    | ROC AUC | 100.00% |
    
    #### 🔒 Privacy & Safety
    
    - No data is stored or logged
    - All processing happens in real-time
    - Your text is analyzed and immediately discarded
    - Open-source and transparent
    
    #### 🌟 Use Cases
    
    - Social media content moderation
    - Comment section filtering  - Chat application safety
    - Educational platform monitoring
    - Online community protection
    
    ---
    
    **Built with ❤️ for a safer internet**
    
    📧 Questions? Open an issue on GitHub  
    ⭐ Like this? Star the repository!
    
    [GitHub](https://github.com/Sidhartha2004/cyberguard) • [Model Card](https://huggingface.co/Sidhartha2004/finetuned_cyberbullying_muril) • [Documentation](https://github.com/Sidhartha2004/cyberguard/blob/main/README.md)
    """)

# Launch the app
if __name__ == "__main__":
    demo.launch()
