"""Rule-based post-processor for Russian voice transcripts -> messenger style.

Deterministic, sub-millisecond. Designed as a zero-latency alternative to LLM
post-processing. Covers the common cases: question marks, exclamations,
friendly brackets ("))" / ")"), preserves pronouns, strips trailing periods,
capitalizes first letter.
"""

import re

QUESTION_STARTERS = (
    'что', 'когда', 'где', 'куда', 'откуда', 'почему', 'зачем', 'как',
    'сколько', 'который', 'какой', 'какая', 'какое', 'какие',
    'чего', 'чему', 'чем', 'кто', 'кого', 'кому', 'кем',
    'разве', 'неужели', 'ли',
)

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
    'техзадание', 'тз', 'деплой', 'релиз', 'таск', 'тикет',
)

GREETINGS = (
    'привет', 'здарова', 'здаров', 'хай', 'доброе утро', 'добрый день',
    'добрый вечер', 'доброй ночи', 'алло',
)

THANKS_WORDS = ('спасибо', 'благодарю', 'спс', 'сенькс', 'благодарочка')

LOVE_WORDS = ('обожаю', 'люблю', 'нравится', 'крутой', 'крутая', 'крутое', 'клёвый',
              'классный', 'классная', 'отличный', 'лапочка', 'лучший', 'лучшая', 'родной',
              'звёздочка', 'молодец')

FUNNY_MARKERS = ('смешно', 'ору', 'ржу', 'лол', 'ахах', 'хаха', 'угораю', 'ржачно', 'прикол',
                 'валяюсь от смеха')

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
        if _contains_any(t, EXCLAMATION_WORDS):
            return False
        return True
    words = t.split()
    if len(words) >= 2 and words[1] in QUESTION_STARTERS:
        return True
    if any(t.startswith(h) for h in PRONOUN_QUESTION_HINTS):
        return True
    first_clause = re.split(r'[,.]|\s и\s|\s но\s|\s а\s', t, maxsplit=1)[0].strip()
    first_words = first_clause.split()[:2]
    if first_words and first_words[0] in QUESTION_STARTERS:
        return True
    if len(first_words) >= 2 and first_words[1] in QUESTION_STARTERS:
        return True
    last_word = t.replace('?', '').split()[-1] if t else ''
    if last_word.endswith(('ёшь', 'ешь', 'ишь', 'аешь', 'уешь')) and not _contains_any(t, WORK_MARKERS):
        if 'ты ' in t or t.split()[0] in ('ты',) or any(h in t for h in PRONOUN_QUESTION_HINTS):
            return True
    return False


def _detect_exclaim(text):
    return _contains_any(text.lower(), EXCLAMATION_WORDS)


def _tone(text):
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
    if len(t.split()) <= 2 and any(w in t.split() for w in ACK_SHORT):
        return 'ack'
    return 'neutral'


def _capitalize_first(text):
    if not text:
        return text
    return text[0].upper() + text[1:]


def rule_based_postprocess(text):
    """Apply rule-based post-processing. Fast, deterministic."""
    out = re.sub(r'\s+', ' ', text).strip()
    if not out:
        return out
    out = EMOJI_RE.sub('', out)
    out = out.rstrip('.!?) ').rstrip()

    is_q = _detect_question(out)
    is_e = _detect_exclaim(out)
    tone = _tone(out)

    if is_q:
        ending = '?'
        brackets = ''
    elif is_e:
        ending = '!'
        brackets = ''
    else:
        ending = ''
        brackets = ')'

    out = _capitalize_first(out)
    if ending:
        out = out + ending
    if brackets:
        out = out + brackets
    return out
