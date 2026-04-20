"""Test corpus for evaluating post-processing of Russian voice transcripts.

Each entry: (input_text, category, expected_rules).
"""

CORPUS = [
    # Questions
    ('ты сегодня придёшь', 'question_friendly', {'ends_question': True, 'preserve_pronouns': ['ты']}),
    ('когда ты освободишься', 'question_friendly', {'ends_question': True, 'preserve_pronouns': ['ты']}),
    ('во сколько встреча завтра', 'question_neutral', {'ends_question': True}),
    ('что делаешь', 'question_friendly', {'ends_question': True}),
    ('как дела', 'question_friendly', {'ends_question': True}),
    ('почему так долго', 'question_neutral', {'ends_question': True}),
    ('где мы встретимся', 'question_neutral', {'ends_question': True, 'preserve_pronouns': ['мы']}),
    ('сколько это стоит', 'question_neutral', {'ends_question': True}),

    # Greetings and friendly openers
    ('привет', 'greeting', {'friendly_ok': True}),
    ('привет как дела', 'greeting', {'friendly_ok': True, 'ends_question': True}),
    ('здарова братан', 'greeting', {'friendly_ok': True}),
    ('доброе утро', 'greeting', {'friendly_ok': True}),

    # Thanks and positive
    ('спасибо тебе большое', 'thanks', {'friendly_ok': True, 'preserve_pronouns': ['тебе']}),
    ('благодарю', 'thanks', {'friendly_ok': True}),
    ('обожаю эту песню', 'positive', {'friendly_ok': True}),
    ('ты лучший', 'positive', {'friendly_ok': True, 'preserve_pronouns': ['ты']}),
    ('у меня день рождения в субботу', 'positive', {'friendly_ok': True, 'preserve_pronouns': ['меня']}),

    # Funny
    ('это было реально смешно', 'funny', {'friendly_ok': True, 'expect_double_bracket': True}),
    ('ору не могу', 'funny', {'friendly_ok': True, 'expect_double_bracket': True}),
    ('блин ты меня сломал', 'funny', {'friendly_ok': True, 'preserve_pronouns': ['ты', 'меня']}),

    # Work / neutral info
    ('встреча в 15 00 в переговорке', 'work', {'no_brackets': True}),
    ('сегодня надо сдать отчёт до шести вечера', 'work', {'no_brackets': True}),
    ('адрес такой невский проспект двадцать пять', 'work', {'no_brackets': True}),
    ('перезвони мне в три часа', 'work', {'no_brackets': True, 'preserve_pronouns': ['мне']}),
    ('документы уже готовы', 'work', {'no_brackets': True}),

    # Negative / complaints / tired
    ('ну блин я устал за эту неделю', 'negative', {'no_brackets': True, 'preserve_pronouns': ['я']}),
    ('опять ничего не работает', 'negative', {'no_brackets': True}),
    ('бесит эта погода', 'negative', {'no_brackets': True}),
    ('всё плохо я сломался', 'negative', {'no_brackets': True, 'preserve_pronouns': ['я']}),

    # Short acknowledgments
    ('ок договорились', 'ack', {'friendly_ok': True}),
    ('понял принял', 'ack', {}),
    ('хорошо', 'ack', {}),
    ('да', 'ack', {}),

    # Exclamations
    ('как же это круто', 'exclaim', {'ends_exclaim': True}),
    ('офигеть', 'exclaim', {}),
    ('не могу поверить что они выиграли', 'exclaim', {}),

    # Multi-sentence / longer
    ('слушай я тут подумал можем сегодня вечером сходить в кино', 'friendly_long',
        {'friendly_ok': True, 'preserve_pronouns': ['я']}),
    ('отправил тебе документы проверь пожалуйста когда будет время', 'friendly_long',
        {'friendly_ok': True, 'preserve_pronouns': ['тебе']}),
    ('сегодня был очень длинный день но всё получилось', 'friendly_long',
        {'friendly_ok': True}),

    # Edge cases — transcription errors / short snippets
    ('ага', 'ack', {}),
    ('ммм', 'noise', {}),
]
