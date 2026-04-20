"""Benchmark runner — evaluate a model + prompt combination against CORPUS."""

import json
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(__file__).rsplit('\\', 1)[0])

from corpus import CORPUS
from holdout import HOLDOUT
from scorer import score_output, summary_row

OLLAMA_URL = 'http://localhost:11434/api/chat'


def call_ollama(model, system_prompt, user_text, num_predict=120, think=False, timeout=60):
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_text},
        ],
        'stream': False,
        'keep_alive': -1,
        'options': {'temperature': 0.3, 'num_predict': num_predict},
    }
    if think is not None:
        payload['think'] = think
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.loads(r.read().decode('utf-8'))
    dt = time.time() - t0
    content = body.get('message', {}).get('content', '')
    # strip hybrid thinking leftovers
    if '</think>' in content:
        content = content.rsplit('</think>', 1)[-1]
    return content.strip(), dt, body.get('eval_count', 0), body.get('prompt_eval_count', 0)


def warmup(model, system_prompt):
    """Send a trivial request to ensure model + KV-cache is hot."""
    try:
        call_ollama(model, system_prompt, 'привет', num_predict=20, timeout=120)
    except Exception as exc:
        print(f'[warmup failed] {exc}', flush=True)


def bench(model, system_prompt, label=None, warm=True, corpus_name='main'):
    label = label or model
    corpus = HOLDOUT if corpus_name == 'holdout' else CORPUS
    print(f'\n{"=" * 70}\nMODEL: {label} | CORPUS: {corpus_name}\n{"=" * 70}', flush=True)

    if warm:
        t0 = time.time()
        warmup(model, system_prompt)
        print(f'[warmup: {time.time()-t0:.2f}s]', flush=True)

    results = []
    total_t = 0.0
    total_score = 0.0
    for text, category, expected in corpus:
        try:
            out, dt, eval_n, prompt_n = call_ollama(model, system_prompt, text)
        except Exception as exc:
            out, dt, eval_n, prompt_n = '', 0.0, 0, 0
            print(f'[ERROR] {text!r}: {exc}', flush=True)
        score, rule_results = score_output(text, out, expected)
        total_t += dt
        total_score += score
        results.append({
            'input': text,
            'category': category,
            'output': out,
            'score': round(score, 1),
            'issues': summary_row(rule_results),
            'latency_s': round(dt, 2),
            'eval_tokens': eval_n,
            'prompt_tokens': prompt_n,
        })
        print(f'[{dt:5.2f}s score={score:5.1f}] {text:50s} -> {out!r}', flush=True)

    n = len(corpus)
    avg_score = total_score / n
    avg_latency = total_t / n
    print(f'\n== SUMMARY {label} ({corpus_name}) ==', flush=True)
    print(f'avg_score={avg_score:.1f} / 100', flush=True)
    print(f'avg_latency={avg_latency:.2f}s', flush=True)
    print(f'total_time={total_t:.1f}s over {n} phrases', flush=True)

    return {
        'label': label,
        'model': model,
        'corpus': corpus_name,
        'avg_score': round(avg_score, 1),
        'avg_latency_s': round(avg_latency, 2),
        'total_time_s': round(total_t, 1),
        'n': n,
        'results': results,
    }


if __name__ == '__main__':
    import yaml
    schema = yaml.safe_load(open('C:/Tools/whisper-writer/src/config_schema.yaml', encoding='utf-8'))
    default_prompt = schema['post_processing']['llm_prompt']['value']
    model = sys.argv[1] if len(sys.argv) > 1 else 'qwen3:4b-instruct-2507-q4_K_M'
    label = sys.argv[2] if len(sys.argv) > 2 else None
    corpus_name = sys.argv[3] if len(sys.argv) > 3 else 'main'
    summary = bench(model, default_prompt, label=label, corpus_name=corpus_name)
    out_path = f'C:/Tools/whisper-writer/bench/result_{model.replace(":","_").replace("/","_")}_{corpus_name}.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
