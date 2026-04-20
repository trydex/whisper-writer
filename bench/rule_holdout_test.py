"""Evaluate rule-based on HOLDOUT corpus (never seen during rule design)."""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(__file__).rsplit('\\', 1)[0])

from holdout import HOLDOUT
from scorer import score_output, summary_row
from rule_based import rule_based_postprocess

total_t = 0.0
total_score = 0.0
for text, category, expected in HOLDOUT:
    t0 = time.perf_counter()
    out = rule_based_postprocess(text)
    dt = time.perf_counter() - t0
    score, rule_results = score_output(text, out, expected)
    total_t += dt
    total_score += score
    print(f'[{dt*1000:6.2f}ms score={score:5.1f}] {text:50s} -> {out!r}', flush=True)
    if score < 90:
        print(f'   issues: {summary_row(rule_results)}', flush=True)

n = len(HOLDOUT)
print(f'\n== HOLDOUT rule_based ==')
print(f'avg_score={total_score/n:.1f} / 100  total_time={total_t*1000:.2f}ms')
