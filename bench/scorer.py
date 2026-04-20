"""Automatic quality scorer for post-processed transcripts.

Each rule returns (passed: bool, weight: int, description: str).
Final score = sum(weight if passed else 0) / sum(weight) * 100.
"""

import re

EMOJI_RE = re.compile(
    '['
    '\U0001F600-\U0001F64F'
    '\U0001F300-\U0001F5FF'
    '\U0001F680-\U0001F6FF'
    '\U0001F700-\U0001F7FF'
    '\U0001F900-\U0001F9FF'
    '\U0001FA00-\U0001FAFF'
    '\u2600-\u27BF'
    ']+'
)

LEAK_PATTERNS = (
    'хорошо,', 'хорошо.', 'давай разбер', 'мне нужно', 'сначала посмотр',
    'проверю', 'нужно проверить', 'итак,', 'итого:', 'правило:', 'out:',
    '<think', '</think', 'here is', 'here\'s',
)


def _starts_uppercase(text):
    return bool(text) and text[0].isupper()


def _strip_ws(text):
    return text.strip().rstrip(' \t\n\r')


def score_output(text_in, text_out, expected):
    """Score a single post-processing result. Returns (score, rule_results)."""
    out = _strip_ws(text_out or '')
    in_norm = text_in.strip().lower()
    out_low = out.lower()
    results = []

    def add(passed, weight, desc):
        results.append((passed, weight, desc))

    # Rule 1: output must not be empty or trivially short
    add(len(out) >= max(1, len(text_in) // 3), 5, 'output_nonempty')

    # Rule 2: length ratio — catches reasoning leaks and truncation
    ratio = len(out) / max(1, len(text_in))
    add(0.6 <= ratio <= 2.2, 10, f'length_ratio={ratio:.2f}')

    # Rule 3: no trailing period (possibly before brackets)
    bad_tail = re.search(r'\.\s*\)*\s*$', out) is not None
    add(not bad_tail, 15, 'no_trailing_period')

    # Rule 4: no emojis at all
    add(not EMOJI_RE.search(out), 10, 'no_emoji')

    # Rule 5: no ")." or ")?" or ")!" — bracket must be the very last char if present
    bad_bracket_position = re.search(r'\)[.?!,]+', out) is not None
    add(not bad_bracket_position, 8, 'no_bracket_mid_punct')

    # Rule 6: no bracket after ? or ! — ") not after ?!"
    bad_bracket_after_punct = re.search(r'[?!]\s*\)', out) is not None
    add(not bad_bracket_after_punct, 8, 'no_bracket_after_qmark')

    # Rule 7: no leaked reasoning keywords at start
    leaked = any(out_low.startswith(p) for p in LEAK_PATTERNS)
    add(not leaked, 15, 'no_reasoning_leak')

    # Rule 8: pronoun preservation
    for pron in expected.get('preserve_pronouns', []):
        add(pron in out_low, 8, f'preserve_pronoun:{pron}')

    # Rule 9: question mark present if expected
    if expected.get('ends_question'):
        has_q = '?' in out and out.rstrip(' )').endswith('?')
        add(has_q, 10, 'ends_with_question_mark')

    # Rule 10: exclamation mark if expected
    if expected.get('ends_exclaim'):
        has_e = '!' in out
        add(has_e, 5, 'has_exclamation')

    # Rule 11: no brackets when no_brackets expected (work/negative)
    if expected.get('no_brackets'):
        has_bracket = ')' in out
        add(not has_bracket, 12, 'no_brackets_in_work_or_negative')

    # Rule 12: double bracket on really funny moments
    if expected.get('expect_double_bracket'):
        has_dd = '))' in out
        add(has_dd, 5, 'has_double_bracket_on_funny')

    # Rule 13: starts with uppercase (soft)
    add(_starts_uppercase(out), 4, 'starts_uppercase')

    total_w = sum(w for _, w, _ in results)
    earned = sum(w for p, w, _ in results if p)
    score = (earned / total_w * 100) if total_w > 0 else 0
    return score, results


def summary_row(results):
    passed = [(p, w, d) for p, w, d in results if not p]
    return '; '.join(d for _, _, d in passed) if passed else 'all ok'
