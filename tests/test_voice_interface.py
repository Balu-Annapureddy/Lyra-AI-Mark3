"""
Voice Interface Test
Tests push-to-talk voice interface with Whisper and pyttsx3
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lyra.interaction.voice_interface import VoiceInterface


def test_tts():
    """Test text-to-speech"""
    print("\n=== Testing TTS ===")
    
    voice = VoiceInterface(model_size="tiny")  # Use tiny model for faster loading
    
    # List available voices
    print("\nAvailable voices:")
    voices = voice.get_available_voices()
    for idx, name in voices:
        print(f"  {idx}: {name}")
    
    # Test TTS
    print("\nTesting TTS...")
    voice.test_tts("Hello, I am Lyra. Voice interface is working.")
    
    print("✅ TTS test complete")
    voice.cleanup()


def test_stt_manual():
    """Test speech-to-text with manual recording"""
    print("\n=== Testing STT (Manual Recording) ===")
    print("This will record for 5 seconds. Speak something!")
    
    voice = VoiceInterface(model_size="tiny")
    
    # Set callback
    def handle_transcription(text: str) -> str:
        print(f"\n✓ Transcribed: {text}")
        return f"I heard: {text}"
    
    voice.set_transcription_callback(handle_transcription)
    
    # Record for 5 seconds
    input("\nPress Enter to start recording (5 seconds)...")
    voice.listen_once(duration=5.0)
    
    print("✅ STT test complete")
    voice.cleanup()


def test_push_to_talk():
    """Test push-to-talk interface"""
    print("\n=== Testing Push-to-Talk ===")
    print("Instructions:")
    print("  1. Type 'r' and press Enter to START recording")
    print("  2. Speak your command")
    print("  3. Type 's' and press Enter to STOP recording")
    print("  4. Type 'q' to quit")
    
    voice = VoiceInterface(model_size="tiny")
    
    # Set callback
    def handle_transcription(text: str) -> str:
        print(f"\n✓ Transcribed: {text}")
        response = f"You said: {text}"
        print(f"✓ Response: {response}")
        return response
    
    voice.set_transcription_callback(handle_transcription)
    
    while True:
        cmd = input("\n[r]ecord / [s]top / [q]uit: ").strip().lower()
        
        if cmd == 'r':
            voice.start_recording()
            print("🎤 Recording... (type 's' to stop)")
        elif cmd == 's':
            voice.stop_recording()
            print("⏹ Stopped recording, processing...")
        elif cmd == 'q':
            break
        else:
            print("Invalid command")
    
    print("✅ Push-to-talk test complete")
    voice.cleanup()


def main():
    """Run voice interface tests"""
    print("=" * 60)
    print("Voice Interface Tests")
    print("=" * 60)
    
    print("\nSelect test:")
    print("  1. TTS only (no microphone needed)")
    print("  2. STT with 5-second recording")
    print("  3. Push-to-talk interface")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    try:
        if choice == '1':
            test_tts()
        elif choice == '2':
            test_stt_manual()
        elif choice == '3':
            test_push_to_talk()
        else:
            print("Invalid choice")
    
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
