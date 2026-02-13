"""
Simple TTS Test - No Whisper Loading
Tests only the text-to-speech functionality
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pyttsx3


def test_tts_simple():
    """Test TTS without loading Whisper"""
    print("\n=== Testing TTS (Simple) ===")
    
    try:
        # Initialize TTS engine
        print("Initializing TTS engine...")
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        engine.setProperty('volume', 0.9)
        
        # List voices
        print("\nAvailable voices:")
        voices = engine.getProperty('voices')
        for i, voice in enumerate(voices):
            print(f"  {i}: {voice.name}")
        
        # Test speech
        print("\nTesting speech output...")
        text = "Hello, I am Lyra. Voice interface is working. Phase 2A infrastructure complete."
        print(f"Speaking: {text}")
        
        engine.say(text)
        engine.runAndWait()
        
        print("\n✅ TTS test PASSED")
        print("Voice interface TTS is functional!")
        
    except Exception as e:
        print(f"\n❌ TTS test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_tts_simple()
