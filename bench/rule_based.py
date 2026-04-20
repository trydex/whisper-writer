"""Rule-based post-processor — classical NLP alternative to LLM.

Strategy:
1. Normalize whitespace, strip trailing period.
2. Detect question (leading interrogative word, or inversion, or verb+2nd-person end).
3. Detect exclamation (specific emotion markers).
4. Detect tone — friendly / work / negative / neutral — via keyword lists.
5. Decide on final punctuation (?, !, or nothing).
6. Decide on closing brackets based on tone.
7. Capitalize first letter.
"""

import re
import time

QUESTION_STARTERS = (
    'что', 'когда', 'где', 'куда', 'откуда', 'почему', 'зачем', 'как',
    'сколько', 'который', 'какой', 'какая', 'какое', 'какие',
    'чего', 'чему', 'чем', 'кто', 'кого', 'кому', 'кем',
    'разве', 'неужели', 'ли',
)

# Questions often start with "ты / вы / мы" + verb (inversion) in colloquial speech
PRONOUN_QUESTION_HINTS = (
    'ты сегодня', 'ты завтра', 'ты тут', 'ты там', 'ты будешь', 'ты идёшь', 'ты придёшь',
    'вы будете', 'вы едете',
    'он придёт', 'она придёт',
)

EXCLAMATION_WORDS = (
    'круто', 'офигеть', 'охренеть', 'обалдеть', 'ничоси', 'вау', 'супер', 'офигенно',
    'классно', 'потрясающе', 'невероятно', 'ура',
)

NEGATIVE_WORDS = (
    'устал', 'устала', 'устали', 'бесит', 'раздражает', 'плохо', 'ужасно', 'отвратительно',
    'сломал', 'сломался', 'сломалась', 'сломано', 'не работает', 'опять не', 'блин',
    'капец', 'жесть', 'кошмар', 'ненавижу', 'достало', 'задолбал', 'надоело',
    'грустно', 'паршиво', 'херово',
)

WORK_MARKERS = (
    'встреча', 'переговорк', 'отчёт', 'отчет', 'документы', 'документ',
    'перезвони', 'позвони', 'созвон', 'митинг', 'митап', 'дедлайн',
    'контракт', 'договор', 'акт', 'счёт', 'счет', 'накладн',
    'адрес', 'офис', 'проспект', 'улица', 'переулок',
)

GREETINGS = (
    'привет', 'здарова', 'здаров', 'хай', 'доброе утро', 'добрый день',
    'добрый вечер', 'доброй ночи', 'алло',
)

THANKS_WORDS = ('спасибо', 'благодарю', 'спс', 'сенькс', 'благодарочка')

LOVE_WORDS = ('обожаю', 'люблю', 'нравится', 'крутой', 'крутая', 'крутое', 'клёвый',
              'классный', 'классная', 'отличный', 'лапочка', 'лучший', 'лучшая')

FUNNY_MARKERS = ('смешно', 'ору', 'ржу', 'лол', 'ахах', 'хаха', 'угораю', 'ржачно', 'прикол')

ACK_SHORT = ('да', 'ага', 'ок', 'угу', 'окей', 'угуу', 'ммм', 'нет', 'не')

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


def _contains_any(text, keywords):
    return any(kw in text for kw in keywords)


def _word_starts(text, starters):
    first = text.split(' ', 1)[0]
    return first in starters


def _detect_question(text):
    t = text.lower().strip()
    if _word_starts(t, QUESTION_STARTERS):
        # "как же это круто" looks like question but is exclamation.
        # If it also contains exclamation words → prefer exclamation.
        if _contains_any(t, EXCLAMATION_WORDS):
            return False
        return True
    # Two-word openers like "во сколько", "до скольки"
    words = t.split()
    if len(words) >= 2 and words[1] in QUESTION_STARTERS:
        return True
    # Inversion-style hints
    if any(t.startswith(h) for h in PRONOUN_QUESTION_HINTS):
        return True
    # Multi-part sentence — only trigger if FIRST clause starts with a question word
    first_clause = re.split(r'[,.]|\s и\s|\s но\s|\s а\s', t, maxsplit=1)[0].strip()
    first_words = first_clause.split()[:2]
    if first_words and first_words[0] in QUESTION_STARTERS:
        return True
    if len(first_words) >= 2 and first_words[1] in QUESTION_STARTERS:
        return True
    # Simple 2nd-person verb ends (ёшь/ешь/ишь)
    last_word = t.replace('?', '').split()[-1] if t else ''
    if last_word.endswith(('ёшь', 'ешь', 'ишь', 'аешь', 'уешь')) and not _contains_any(t, WORK_MARKERS):
        if 'ты ' in t or t.split()[0] in ('ты',) or any(h in t for h in PRONOUN_QUESTION_HINTS):
            return True
    return False


def _detect_exclaim(text):
    t = text.lower()
    if _contains_any(t, EXCLAMATION_WORDS):
        return True
    return False


def _tone(text):
    """Return one of: 'greeting', 'thanks', 'love', 'funny', 'negative', 'work', 'neutral', 'ack'."""
    t = text.lower()
    if _contains_any(t, NEGATIVE_WORDS):
        return 'negative'
    if _contains_any(t, FUNNY_MARKERS):
        return 'funny'
    if _contains_any(t, WORK_MARKERS):
        return 'work'
    if _contains_any(t, THANKS_WORDS):
        return 'thanks'
    if _contains_any(t, LOVE_WORDS):
        return 'love'
    if any(t.startswith(g) for g in GREETINGS):
        return 'greeting'
    # short acknowledgments
    if len(t.split()) <= 2 and any(w in t.split() for w in ACK_SHORT):
        return 'ack'
    return 'neutral'


def _capitalize_first(text):
    if not text:
        return text
    return text[0].upper() + text[1:]


def _cleanup_whitespace(text):
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def rule_based_postprocess(text):
    """Apply rule-based post-processing. Fast, deterministic."""
    out = _cleanup_whitespace(text)
    if not out:
        return out
    out = EMOJI_RE.sub('', out)
    # Strip existing trailing punctuation we'll decide anew
    out = out.rstrip('.!?) ').rstrip()

    is_q = _detect_question(out)
    is_e = _detect_exclaim(out)
    tone = _tone(out)

    # Decide ending punctuation
    if is_q:
        ending = '?'
        brackets = ''  # no brackets after ?
    elif is_e:
        ending = '!'
        brackets = ''
    else:
        ending = ''
        brackets = ''
        if tone == 'funny':
            brackets = '))'
        elif tone in ('thanks', 'love'):
            brackets = '))'
        elif tone in ('greeting', 'ack'):
            brackets = ')'
        elif tone in ('work', 'negative', 'neutral'):
            brackets = ''

    # Capitalize first letter
    out = _capitalize_first(out)
    # Assemble
    if ending:
        out = out + ending
    if brackets:
        out = out + brackets
    return out


if __name__ == '__main__':
    import json
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    sys.path.insert(0, str(__file__).rsplit('\\', 1)[0])
    from corpus import CORPUS
    from scorer import score_output, summary_row

    results = []
    total_t = 0.0
    total_score = 0.0
    for text, category, expected in CORPUS:
        t0 = time.perf_counter()
        out = rule_based_postprocess(text)
        dt = time.perf_counter() - t0
        score, rule_results = score_output(text, out, expected)
        total_t += dt
        total_score += score
        results.append({
            'input': text,
            'category': category,
            'output': out,
            'score': round(score, 1),
            'issues': summary_row(rule_results),
            'latency_ms': round(dt * 1000, 3),
        })
        print(f'[{dt*1000:6.2f}ms score={score:5.1f}] {text:50s} -> {out!r}', flush=True)

    n = len(CORPUS)
    avg = total_score / n
    print(f'\n== SUMMARY rule_based ==')
    print(f'avg_score={avg:.1f} / 100')
    print(f'total_time={total_t*1000:.2f}ms over {n} phrases, avg {total_t*1000/n:.3f}ms/phrase')

    with open('C:/Tools/whisper-writer/bench/result_rule_based.json', 'w', encoding='utf-8') as f:
        json.dump({
            'label': 'rule_based',
            'model': 'rule_based',
            'avg_score': round(avg, 1),
            'avg_latency_s': round(total_t / n, 5),
            'total_time_s': round(total_t, 4),
            'n': n,
            'results': results,
        }, f, ensure_ascii=False, indent=2)
