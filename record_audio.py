import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import os
import threading
import time
from dotenv import load_dotenv

load_dotenv()

class AudioRecorder:
    def __init__(self):
        self.sample_rate = int(os.getenv('SAMPLE_RATE', 44100))
        self._stop_event = threading.Event()
        self._recording_data = []
        self._recording_thread = None
        self._is_recording = False

    def get_audio(self, filename, duration):
        """Legacy method: Record for a fixed duration (blocks until complete)"""
        print("Recording...")
        recording = sd.rec(int(duration * self.sample_rate), samplerate=self.sample_rate, channels=1, dtype='int16')
        sd.wait()  # Wait until the recording is finished
        write(filename, self.sample_rate, recording)
        print(f"Recording finished. Saved as {filename}.")

    def start_recording(self, filename):
        """Start recording in a background thread. Can be stopped early with stop_recording()."""
        if self._is_recording:
            raise RuntimeError("Recording is already in progress")
        
        self._stop_event.clear()
        self._recording_data = []
        self._is_recording = True
        self._filename = filename
        
        def _record_callback(indata, frames, time_info, status):
            if status:
                print(f"Recording status: {status}")
            if self._stop_event.is_set():
                raise sd.CallbackStop()
            # Copy the input data to avoid overwriting issues
            self._recording_data.append(indata.copy())
        
        def _record_thread():
            try:
                # Use float32 internally for better quality, convert to int16 when saving
                with sd.InputStream(samplerate=self.sample_rate, 
                                  channels=1,
                                  dtype='float32',
                                  callback=_record_callback):
                    while not self._stop_event.is_set():
                        time.sleep(0.1)
            except sd.CallbackStop:
                pass
            except Exception as e:
                print(f"Error in recording thread: {str(e)}")
            finally:
                self._is_recording = False
        
        self._recording_thread = threading.Thread(target=_record_thread, daemon=True)
        self._recording_thread.start()
        print("Recording started (can be stopped early)...")

    def stop_recording(self):
        """Stop the current recording and save the file."""
        if not self._is_recording and not self._recording_data:
            print("No recording in progress to stop.")
            return
        
        print("Stopping recording...")
        self._stop_event.set()
        
        # Wait for recording thread to finish (allow up to 3 seconds)
        if self._recording_thread and self._recording_thread.is_alive():
            self._recording_thread.join(timeout=3)
        
        # Concatenate all recorded chunks
        if self._recording_data:
            try:
                recording = np.concatenate(self._recording_data, axis=0)
                
                # Ensure data is in the right shape (flatten if needed for mono)
                if len(recording.shape) > 1:
                    recording = recording.flatten()
                
                # Convert to int16 if needed (sounddevice might return float32)
                if recording.dtype == np.float32 or recording.dtype == np.float64:
                    # Normalize to -1.0 to 1.0 range, then convert to int16
                    recording = np.clip(recording, -1.0, 1.0)
                    recording = (recording * 32767).astype(np.int16)
                elif recording.dtype != np.int16:
                    recording = recording.astype(np.int16)
                
                # Save the recording
                write(self._filename, self.sample_rate, recording)
                duration = len(recording) / self.sample_rate
                print(f"Recording stopped and saved as {self._filename} (Duration: {duration:.1f} seconds)")
            except Exception as e:
                print(f"Error saving recording: {str(e)}")
                raise
            finally:
                self._recording_data = []
        else:
            print("No audio data recorded.")
        
        self._is_recording = False

    def is_recording(self):
        """Check if recording is currently in progress."""
        return self._is_recording

    def record_with_timeout(self, filename, max_duration):
        """Record for up to max_duration seconds, but can be stopped early."""
        self.start_recording(filename)
        try:
            time.sleep(max_duration)
        except KeyboardInterrupt:
            pass
        finally:
            if self._is_recording:
                self.stop_recording()
