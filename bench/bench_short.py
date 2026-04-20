"""Benchmark a model with the SHORT prompt variant."""
import json, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(__file__).rsplit('\\', 1)[0])

from runner import bench
from short_prompt import SHORT_PROMPT

model = sys.argv[1] if len(sys.argv) > 1 else 'qwen3:4b-instruct-2507-q4_K_M'
label = sys.argv[2] if len(sys.argv) > 2 else 'short_prompt'
corpus_name = sys.argv[3] if len(sys.argv) > 3 else 'main'
summary = bench(model, SHORT_PROMPT, label=label, corpus_name=corpus_name)
out_path = f'C:/Tools/whisper-writer/bench/result_{model.replace(":","_").replace("/","_")}_{label}_{corpus_name}.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
