BAD_WORDS = ['дурак', 'идиот', 'дебил', 'тупой', 'кретин', 'олух',
    'редиска', 'гад', 'тварь', 'бездарность', 'безрукий', 'бездарный', 'бездарная', 'бездарное']

def contains_bad_words(text):
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word in text_lower:
            return True
    return False