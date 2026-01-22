"""
Test script for binary classification filtering logic.
Tests the cyberbullying filter with sample texts.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cyberbullying_filter import CyberbullyingFilter


def test_filter():
    """Test the cyberbullying filter with various examples"""
    
    print("=" * 60)
    print("CYBERBULLYING FILTER TEST")
    print("=" * 60)
    
    # Initialize filter
    print("\n🔧 Initializing filter...")
    try:
        filter_instance = CyberbullyingFilter(
            model_path="Sidhartha2004/finetuned_cyberbullying_muril",
            threshold=float(os.getenv("OPTIMAL_THRESHOLD", "0.5")),
            device="cpu"
        )
        print("✅ Filter initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize filter: {e}")
        return
    
    # Test cases
    test_cases = [
        # Safe texts
        ("namaste kaise ho", "SAFE"),
        ("good morning everyone", "SAFE"),
        ("happy birthday", "SAFE"),
        ("thank you so much", "SAFE"),
        ("how are you doing", "SAFE"),
        
        # Bullying texts
        ("tu gadha hai saale", "BULLYING"),
        ("madarchod nikal yahan se", "BULLYING"),
        ("behenchod kya kar raha hai", "BULLYING"),
        ("chutiya insaan", "BULLYING"),
        ("you are stupid idiot", "BULLYING"),
    ]
    
    print(f"\n📊 Testing {len(test_cases)} samples...")
    print("-" * 60)
    
    correct = 0
    total = len(test_cases)
    
    for text, expected_label in test_cases:
        result = filter_instance.predict(text, return_probabilities=True)
        
        actual_label = result['label_name']
        is_correct = actual_label == expected_label
        correct += int(is_correct)
        
        # Color coding
        status = "✅" if is_correct else "❌"
        
        print(f"\n{status} Text: \"{text}\"")
        print(f"   Expected: {expected_label}")
        print(f"   Predicted: {actual_label} (label={result['label']})")
        print(f"   Confidence: {result['confidence']:.2%}")
        print(f"   Bullying Risk: {result['bullying_probability']:.2%}")
        print(f"   Probabilities: Safe={result['probabilities']['safe']:.2%}, "
              f"Bullying={result['probabilities']['bullying']:.2%}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📈 RESULTS: {correct}/{total} correct ({correct/total:.1%} accuracy)")
    print("=" * 60)
    
    # Batch test
    print("\n🔄 Testing batch prediction...")
    batch_texts = [t[0] for t in test_cases[:5]]
    batch_results = filter_instance.batch_predict(batch_texts)
    
    print(f"✅ Batch processed {len(batch_results)} texts")
    for res in batch_results[:3]:
        print(f"   - {res['label_name']}: \"{res['text'][:40]}...\"")
    
    # Content filtering
    print("\n🔍 Testing content filtering...")
    all_texts = [t[0] for t in test_cases]
    filtered = filter_instance.filter_content(all_texts, action='flag')
    
    print(f"   Total: {filtered['total']}")
    print(f"   Safe: {filtered['safe_count']}")
    print(f"   Flagged: {filtered['flagged_count']}")
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    test_filter()
