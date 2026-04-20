import time
import time as _time_mod
import traceback
import numpy as np
import sounddevice as sd
import tempfile
import wave
import webrtcvad
from PyQt5.QtCore import QThread, QMutex, pyqtSignal
from collections import deque
from threading import Event

from transcription import transcribe_only, post_process_transcription
from utils import ConfigManager


class ResultThread(QThread):
    """
    A thread class for handling audio recording, transcription, and result processing.

    This class manages the entire process of:
    1. Recording audio from the microphone
    2. Detecting speech and silence
    3. Saving the recorded audio as numpy array
    4. Transcribing the audio
    5. Emitting the transcription result

    Signals:
        statusSignal: Emits the current status of the thread (e.g., 'recording', 'transcribing', 'idle')
        resultSignal: Emits the transcription result
    """

    statusSignal = pyqtSignal(str)
    resultSignal = pyqtSignal(str)
    levelSignal = pyqtSignal(float)

    def __init__(self, local_model=None):
        """
        Initialize the ResultThread.

        :param local_model: Local transcription model (if applicable)
        """
        super().__init__()
        self.local_model = local_model
        self.is_recording = False
        self.is_running = True
        self.is_cancelled = False
        self.sample_rate = None
        self.mutex = QMutex()
        self._last_level_ts = 0.0
        self._n_bands = 6

    def cancel(self):
        """Cancel recording without transcribing."""
        self.mutex.lock()
        self.is_cancelled = True
        self.is_recording = False
        self.mutex.unlock()

    def _emit_levels(self, samples_i16):
        try:
            if samples_i16.size < 64:
                return
            x = samples_i16.astype(np.float32) / 32768.0
            rms = float(np.sqrt(np.mean(x * x)))
            peak = float(np.max(np.abs(x)))
            level = float(min(1.0, max(0.0, (rms * 0.55 + peak * 0.45) * 14.0)))
            self.levelSignal.emit(level)
        except Exception as exc:
            print(f'[DBG] _emit_levels error: {exc}', flush=True)

    def stop_recording(self):
        """Stop the current recording session."""
        self.mutex.lock()
        self.is_recording = False
        self.mutex.unlock()

    def stop(self):
        """Stop the entire thread execution."""
        self.mutex.lock()
        self.is_running = False
        self.mutex.unlock()
        self.statusSignal.emit('idle')
        self.wait()

    def run(self):
        """Main execution method for the thread."""
        try:
            if not self.is_running:
                return

            self.mutex.lock()
            self.is_recording = True
            self.mutex.unlock()

            self.statusSignal.emit('recording')
            ConfigManager.console_print('Recording...')
            audio_data = self._record_audio()

            if not self.is_running:
                return

            if self.is_cancelled:
                ConfigManager.console_print('Recording cancelled.')
                self.statusSignal.emit('idle')
                return

            if audio_data is None:
                self.statusSignal.emit('idle')
                return

            self.statusSignal.emit('transcribing')
            ConfigManager.console_print('Transcribing...')

            # Time the transcription process
            start_time = time.time()
            raw = transcribe_only(audio_data, self.local_model)
            pp_cfg = ConfigManager.get_config_section('post_processing')
            if pp_cfg.get('enabled') is not False and (pp_cfg.get('engine') or '').lower() == 'llm':
                self.statusSignal.emit('post_processing')
            result = post_process_transcription(raw)
            end_time = time.time()

            transcription_time = end_time - start_time
            ConfigManager.console_print(f'Transcription completed in {transcription_time:.2f} seconds. Post-processed line: {result}')

            if not self.is_running:
                return

            self.statusSignal.emit('idle')
            self.resultSignal.emit(result)

        except Exception as e:
            print(f'[DBG] ResultThread.run exception: {e}', flush=True)
            traceback.print_exc()
        except BaseException as e:
            print(f'[DBG] ResultThread.run BASE exception: {type(e).__name__}: {e}', flush=True)
            import sys
            sys.stdout.flush()
            raise
            self.statusSignal.emit('error')
            self.resultSignal.emit('')
        finally:
            self.stop_recording()

    def _record_audio(self):
        """
        Record audio from the microphone and save it to a temporary file.

        :return: numpy array of audio data, or None if the recording is too short
        """
        print('[DBG] _record_audio: start', flush=True)
        recording_options = ConfigManager.get_config_section('recording_options')
        self.sample_rate = recording_options.get('sample_rate') or 16000
        frame_duration_ms = 30  # 30ms frame duration for WebRTC VAD
        frame_size = int(self.sample_rate * (frame_duration_ms / 1000.0))
        silence_duration_ms = recording_options.get('silence_duration') or 900
        silence_frames = int(silence_duration_ms / frame_duration_ms)

        # 150ms delay before starting VAD to avoid mistaking the sound of key pressing for voice
        initial_frames_to_skip = int(0.15 * self.sample_rate / frame_size)

        # Create VAD only for recording modes that use it
        recording_mode = recording_options.get('recording_mode') or 'continuous'
        vad = None
        if recording_mode in ('voice_activity_detection', 'continuous'):
            vad = webrtcvad.Vad(2)  # VAD aggressiveness: 0 to 3, 3 being the most aggressive
            speech_detected = False
            silent_frame_count = 0

        audio_buffer = deque(maxlen=frame_size)
        recording = []

        data_ready = Event()
        callback_errors = []

        def audio_callback(indata, frames, time, status):
            try:
                if status:
                    ConfigManager.console_print(f"Audio callback status: {status}")
                audio_buffer.extend(indata[:, 0])
                data_ready.set()
                now = _time_mod.time()
                if now - self._last_level_ts >= 0.04:
                    self._last_level_ts = now
                    try:
                        self._emit_levels(indata[:, 0])
                    except Exception as lvl_exc:
                        callback_errors.append(f'level: {lvl_exc}')
            except Exception as cb_exc:
                callback_errors.append(str(cb_exc))

        print(f'[DBG] _record_audio: opening InputStream sr={self.sample_rate} frame={frame_size}', flush=True)
        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='int16',
                            blocksize=frame_size, device=recording_options.get('sound_device'),
                            callback=audio_callback):
            print('[DBG] _record_audio: InputStream opened, entering loop', flush=True)
            frame_count = 0
            while self.is_running and self.is_recording:
                data_ready.wait()
                data_ready.clear()

                if len(audio_buffer) < frame_size:
                    continue

                # Save frame
                frame = np.array(list(audio_buffer), dtype=np.int16)
                audio_buffer.clear()
                recording.extend(frame)

                # Avoid trying to detect voice in initial frames
                if initial_frames_to_skip > 0:
                    initial_frames_to_skip -= 1
                    continue

                if vad:
                    if vad.is_speech(frame.tobytes(), self.sample_rate):
                        silent_frame_count = 0
                        if not speech_detected:
                            ConfigManager.console_print("Speech detected.")
                            speech_detected = True
                    else:
                        silent_frame_count += 1

                    if speech_detected and silent_frame_count > silence_frames:
                        break

                frame_count += 1
                if frame_count % 100 == 0:
                    print(f'[DBG] _record_audio: {frame_count} frames ({frame_count * frame_duration_ms / 1000:.1f}s)', flush=True)

        print(f'[DBG] _record_audio: loop exited frames={frame_count} cb_errors={len(callback_errors)}', flush=True)
        if callback_errors:
            print(f'[DBG] audio_callback errors: {callback_errors[:3]}', flush=True)
        audio_data = np.array(recording, dtype=np.int16)
        duration = len(audio_data) / self.sample_rate

        ConfigManager.console_print(f'Recording finished. Size: {audio_data.size} samples, Duration: {duration:.2f} seconds')

        min_duration_ms = recording_options.get('min_duration') or 100

        if (duration * 1000) < min_duration_ms:
            ConfigManager.console_print(f'Discarded due to being too short.')
            return None

        return audio_data
