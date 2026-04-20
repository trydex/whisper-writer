import io
import json
import os
import re
import urllib.error
import urllib.request
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from openai import OpenAI

from post_process_rules import rule_based_postprocess
from utils import ConfigManager

_LLM_TIMEOUT_SEC = 5
_THINK_BLOCK_RE = re.compile(r'<think>.*?</think>', re.DOTALL)


def _strip_thinking(content):
    """Extract the final answer from a reasoning model's output.

    Some hybrid-thinking models (Qwen3, DeepSeek-R1) emit reasoning inside
    the content field, separated from the final answer by a `</think>` tag.
    Ollama sometimes drops the opening `<think>` tag, so we can't rely on
    matched pairs - split on the closing tag if present.
    """
    closing = content.rfind('</think>')
    if closing != -1:
        content = content[closing + len('</think>'):]
    content = _THINK_BLOCK_RE.sub('', content)
    return content.strip()

def create_local_model():
    """
    Create a local model using the faster-whisper library.
    """
    ConfigManager.console_print('Creating local model...')
    local_model_options = ConfigManager.get_config_section('model_options')['local']
    compute_type = local_model_options['compute_type']
    model_path = local_model_options.get('model_path')

    device = local_model_options['device']

    try:
        if model_path:
            ConfigManager.console_print(f'Loading model from: {model_path}')
            model = WhisperModel(model_path,
                                 device=device,
                                 compute_type=compute_type,
                                 download_root=None)  # Prevent automatic download
        else:
            model = WhisperModel(local_model_options['model'],
                                 device=device,
                                 compute_type=compute_type)
    except Exception as e:
        ConfigManager.console_print(f'Error initializing WhisperModel: {e}')
        ConfigManager.console_print('Falling back to CPU.')
        model = WhisperModel(model_path or local_model_options['model'],
                             device='cpu',
                             compute_type=compute_type,
                             download_root=None if model_path else None)

    ConfigManager.console_print('Local model created.')
    return model

def transcribe_local(audio_data, local_model=None):
    """
    Transcribe an audio file using a local model.
    """
    if not local_model:
        local_model = create_local_model()
    model_options = ConfigManager.get_config_section('model_options')

    # Convert int16 to float32
    audio_data_float = audio_data.astype(np.float32) / 32768.0

    response = local_model.transcribe(audio=audio_data_float,
                                      language=model_options['common']['language'],
                                      initial_prompt=model_options['common']['initial_prompt'],
                                      condition_on_previous_text=model_options['local']['condition_on_previous_text'],
                                      temperature=model_options['common']['temperature'],
                                      vad_filter=model_options['local']['vad_filter'],)
    return ''.join([segment.text for segment in list(response[0])])

def transcribe_api(audio_data):
    """
    Transcribe an audio file using the OpenAI API.
    """
    model_options = ConfigManager.get_config_section('model_options')
    client = OpenAI(
        api_key=os.getenv('OPENAI_API_KEY') or None,
        base_url=model_options['api']['base_url'] or 'https://api.openai.com/v1'
    )

    # Convert numpy array to WAV file
    byte_io = io.BytesIO()
    sample_rate = ConfigManager.get_config_section('recording_options').get('sample_rate') or 16000
    sf.write(byte_io, audio_data, sample_rate, format='wav')
    byte_io.seek(0)

    response = client.audio.transcriptions.create(
        model=model_options['api']['model'],
        file=('audio.wav', byte_io, 'audio/wav'),
        language=model_options['common']['language'],
        prompt=model_options['common']['initial_prompt'],
        temperature=model_options['common']['temperature'],
    )
    return response.text

def _llm_rewrite(text):
    """Pass transcript through a local LLM. Returns original text on any error."""
    cfg = ConfigManager.get_config_section('post_processing')
    if not text.strip():
        return text

    url = cfg.get('llm_api_url') or 'http://localhost:11434/api/chat'
    payload = {
        'model': cfg.get('llm_model') or 'qwen3:4b',
        'messages': [
            {'role': 'system', 'content': cfg.get('llm_prompt') or ''},
            {'role': 'user', 'content': text},
        ],
        'stream': False,
        'think': False,
        'keep_alive': -1,
        'options': {'temperature': 0.3, 'num_predict': 120},
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=_LLM_TIMEOUT_SEC) as resp:
            body = json.loads(resp.read().decode('utf-8'))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        ConfigManager.console_print(f'LLM post-processing failed, using original: {exc}')
        return text

    rewritten = _strip_thinking(body.get('message', {}).get('content', ''))
    if not rewritten:
        return text
    if len(rewritten) > max(40, len(text) * 3):
        ConfigManager.console_print('LLM output suspiciously long, discarding (likely leaked reasoning).')
        return text
    return rewritten


def post_process_transcription(transcription):
    """
    Apply post-processing to the transcription.
    """
    post_processing = ConfigManager.get_config_section('post_processing')
    if post_processing.get('enabled') is False:
        return transcription

    transcription = transcription.strip()
    engine = (post_processing.get('engine') or 'off').lower()
    if engine == 'rules':
        add_bracket = post_processing.get('rules_add_bracket')
        if add_bracket is None:
            add_bracket = True
        transcription = rule_based_postprocess(transcription, add_bracket=add_bracket)
    elif engine == 'llm':
        transcription = _llm_rewrite(transcription).strip()

    if post_processing['remove_trailing_period'] and transcription.endswith('.'):
        transcription = transcription[:-1]
    if post_processing['add_trailing_space']:
        transcription += ' '
    if post_processing['remove_capitalization']:
        transcription = transcription.lower()

    return transcription

def transcribe_only(audio_data, local_model=None):
    """Raw transcription without any post-processing."""
    if audio_data is None:
        return ''
    if ConfigManager.get_config_value('model_options', 'use_api'):
        return transcribe_api(audio_data)
    return transcribe_local(audio_data, local_model)


def transcribe(audio_data, local_model=None):
    """
    Transcribe audio date using the OpenAI API or a local model, depending on config.
    """
    return post_process_transcription(transcribe_only(audio_data, local_model))

