"""Verify rule-based engine works through post_process_transcription."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'C:/Tools/whisper-writer/src')

from utils import ConfigManager
ConfigManager.initialize()
# Force engine to rules for this test.
ConfigManager._instance.config['post_processing']['engine'] = 'rules'
ConfigManager._instance.config['post_processing']['llm_enabled'] = False

from transcription import post_process_transcription

tests = [
    'ты сегодня придёшь',
    'спасибо тебе большое',
    'встреча в 15 00 в переговорке',
    'блин я устал за эту неделю',
    'что делаешь',
    'это было реально смешно',
]
for t in tests:
    out = post_process_transcription(t)
    print(f'IN:  {t!r}\nOUT: {out!r}\n')
