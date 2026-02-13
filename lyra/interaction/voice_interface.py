"""
Voice Interface - Phase 2A
Push-to-talk voice interaction (NO wake word, NO background monitoring)
Uses Whisper for local STT and pyttsx3 for TTS
"""

import threading
import queue
import sounddevice as sd
import numpy as np
import whisper
import pyttsx3
from typing import Optional, Callable
from pathlib import Path
import tempfile
import wave
from lyra.core.logger import get_logger
from lyra.core.state_manager import StateManager, LyraState


class VoiceInterface:
    """
    Push-to-talk voice interface
    Simple, deterministic, no wake word detection
    """
    
    def __init__(self, 
                 model_size: str = "base",
                 sample_rate: int = 16000,
                 hotkey: str = "ctrl+space"):
        """
        Initialize voice interface
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            sample_rate: Audio sample rate
            hotkey: Hotkey for push-to-talk (currently informational)
        """
        self.logger = get_logger(__name__)
        self.sample_rate = sample_rate
        self.hotkey = hotkey
        
        # State
        self.state_manager = StateManager()
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.recording_thread: Optional[threading.Thread] = None
        
        # Whisper model (local STT)
        self.logger.info(f"Loading Whisper model: {model_size}")
        try:
            self.whisper_model = whisper.load_model(model_size)
            self.logger.info("Whisper model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load Whisper model: {e}")
            raise
        
        # TTS engine
        self.logger.info("Initializing TTS engine")
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 175)  # Speed
            self.tts_engine.setProperty('volume', 0.9)  # Volume
            self.logger.info("TTS engine initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize TTS: {e}")
            raise
        
        # Callback for processing transcribed text
        self.on_transcription: Optional[Callable[[str], str]] = None
    
    def set_transcription_callback(self, callback: Callable[[str], str]):
        """
        Set callback for processing transcribed text
        
        Args:
            callback: Function that takes transcribed text and returns response
        """
        self.on_transcription = callback
    
    def start_recording(self):
        """Start recording audio (push-to-talk pressed)"""
        if self.is_recording:
            self.logger.warning("Already recording")
            return
        
        self.logger.info("Starting recording...")
        self.is_recording = True
        self.state_manager.set_state(LyraState.LISTENING)
        
        # Clear queue
        while not self.audio_queue.empty():
            self.audio_queue.get()
        
        # Start recording thread
        self.recording_thread = threading.Thread(target=self._record_audio)
        self.recording_thread.start()
    
    def stop_recording(self):
        """Stop recording and process audio (push-to-talk released)"""
        if not self.is_recording:
            self.logger.warning("Not recording")
            return
        
        self.logger.info("Stopping recording...")
        self.is_recording = False
        
        # Wait for recording thread to finish
        if self.recording_thread:
            self.recording_thread.join()
        
        # Process recorded audio
        self._process_audio()
    
    def _record_audio(self):
        """Record audio from microphone"""
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.float32,
                callback=self._audio_callback
            ):
                while self.is_recording:
                    sd.sleep(100)
        except Exception as e:
            self.logger.error(f"Recording error: {e}")
            self.is_recording = False
    
    def _audio_callback(self, indata, frames, time, status):
        """Callback for audio stream"""
        if status:
            self.logger.warning(f"Audio status: {status}")
        
        if self.is_recording:
            self.audio_queue.put(indata.copy())
    
    def _process_audio(self):
        """Process recorded audio with Whisper"""
        self.state_manager.set_state(LyraState.THINKING)
        
        try:
            # Collect audio data
            audio_data = []
            while not self.audio_queue.empty():
                audio_data.append(self.audio_queue.get())
            
            if not audio_data:
                self.logger.warning("No audio data recorded")
                self.state_manager.set_state(LyraState.IDLE)
                return
            
            # Concatenate audio
            audio = np.concatenate(audio_data, axis=0).flatten()
            
            # Save to temporary WAV file
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.sample_rate)
                # Convert float32 to int16
                audio_int16 = (audio * 32767).astype(np.int16)
                wf.writeframes(audio_int16.tobytes())
            
            # Transcribe with Whisper
            self.logger.info("Transcribing audio...")
            result = self.whisper_model.transcribe(
                temp_file.name,
                language="en",
                fp16=False  # Use FP32 for CPU
            )
            
            transcribed_text = result["text"].strip()
            self.logger.info(f"Transcribed: {transcribed_text}")
            
            # Clean up temp file
            Path(temp_file.name).unlink()
            
            # Process transcription
            if transcribed_text and self.on_transcription:
                response = self.on_transcription(transcribed_text)
                if response:
                    self.speak(response)
            
            self.state_manager.set_state(LyraState.IDLE)
        
        except Exception as e:
            self.logger.error(f"Audio processing error: {e}")
            self.state_manager.set_state(LyraState.ERROR)
    
    def speak(self, text: str):
        """
        Speak text using TTS
        
        Args:
            text: Text to speak
        """
        try:
            self.logger.info(f"Speaking: {text}")
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            self.logger.error(f"TTS error: {e}")
    
    def listen_once(self, duration: float = 5.0) -> str:
        """
        Record for a fixed duration and return transcription
        Useful for testing without hotkey
        
        Args:
            duration: Recording duration in seconds
        
        Returns:
            Transcribed text
        """
        self.logger.info(f"Recording for {duration} seconds...")
        self.start_recording()
        
        # Record for specified duration
        import time
        time.sleep(duration)
        
        self.stop_recording()
        
        # Wait for processing
        while self.state_manager.current_state != LyraState.IDLE:
            time.sleep(0.1)
        
        return ""  # Transcription handled by callback
    
    def test_tts(self, text: str = "Hello, I am Lyra. Voice interface is working."):
        """
        Test TTS functionality
        
        Args:
            text: Text to speak
        """
        self.speak(text)
    
    def get_available_voices(self):
        """Get available TTS voices"""
        voices = self.tts_engine.getProperty('voices')
        return [(i, v.name) for i, v in enumerate(voices)]
    
    def set_voice(self, voice_index: int):
        """
        Set TTS voice
        
        Args:
            voice_index: Index of voice to use
        """
        voices = self.tts_engine.getProperty('voices')
        if 0 <= voice_index < len(voices):
            self.tts_engine.setProperty('voice', voices[voice_index].id)
            self.logger.info(f"Voice set to: {voices[voice_index].name}")
        else:
            self.logger.warning(f"Invalid voice index: {voice_index}")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.is_recording:
            self.stop_recording()
        
        if self.tts_engine:
            self.tts_engine.stop()
