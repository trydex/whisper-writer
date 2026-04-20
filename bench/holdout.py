"""Holdout corpus — phrases NOT used when designing rule-based system.
Tests generalization of rules on unfamiliar phrases.
"""

HOLDOUT = [
    # Unfamiliar questions
    ('не видел моих ключей', 'question_friendly', {'ends_question': True, 'preserve_pronouns': ['моих']}),
    ('ты уже проснулся', 'question_friendly', {'ends_question': True, 'preserve_pronouns': ['ты']}),
    ('взял зонтик', 'question_neutral', {'ends_question': True}),
    ('тебе помочь', 'question_friendly', {'ends_question': True, 'preserve_pronouns': ['тебе']}),
    ('у вас есть молоко', 'question_neutral', {'ends_question': True, 'preserve_pronouns': ['вас']}),

    # Unfamiliar greetings / positive
    ('рад тебя видеть', 'positive', {'friendly_ok': True, 'preserve_pronouns': ['тебя']}),
    ('ты мне как родной', 'positive', {'friendly_ok': True, 'preserve_pronouns': ['ты', 'мне']}),
    ('моя звёздочка', 'positive', {'friendly_ok': True}),

    # Funny (new words)
    ('я валяюсь от смеха', 'funny', {'friendly_ok': True, 'preserve_pronouns': ['я']}),
    ('бабка зажгла на танцполе', 'funny', {'friendly_ok': True}),

    # Work
    ('согласуйте техзадание до пятницы', 'work', {'no_brackets': True}),
    ('нужно подписать три акта', 'work', {'no_brackets': True}),
    ('созвон в понедельник в десять', 'work', {'no_brackets': True}),
    ('отправь файл в общий чат', 'work', {'no_brackets': True}),
    ('деплой откатился назад', 'work', {'no_brackets': True}),

    # Negative / tired (new)
    ('дождь опять весь день льёт', 'negative', {'no_brackets': True}),
    ('снова голова болит', 'negative', {'no_brackets': True}),
    ('ничего не успеваю', 'negative', {'no_brackets': True}),
    ('вчера совсем не спал', 'negative', {'no_brackets': True}),

    # Neutral statements
    ('пошёл в магазин', 'neutral', {}),
    ('сижу работаю', 'neutral', {}),
    ('завтра будет дождь', 'neutral', {}),
    ('кот уронил чашку', 'neutral', {}),

    # Exclamations
    ('ну ты молодец', 'exclaim', {'friendly_ok': True, 'preserve_pronouns': ['ты']}),
    ('да ладно серьёзно', 'exclaim', {}),
    ('вот это поворот', 'exclaim', {}),

    # Mixed / ambiguous — tough cases
    ('позвоню когда освобожусь', 'neutral', {}),
    ('не знаю что выбрать', 'neutral', {}),
    ('давай сегодня в кино', 'friendly', {'friendly_ok': True}),
    ('хочу спать уже', 'neutral', {}),
]
