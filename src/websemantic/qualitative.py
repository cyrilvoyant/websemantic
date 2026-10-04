"""Resolve descriptor-defined qualitative levels as traceable assumptions."""

import re
import unicodedata


def fold(text):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', text.lower())
                            if not unicodedata.combining(c)).split())


def resolve(evidence, spec, contextual=False):
    text = fold(evidence)
    # A numeric instruction takes precedence; this resolver does not reinterpret it.
    if re.search(r'\d', text):
        return None
    default_choice = text in {'defaut', 'le defaut', 'valeur par defaut', 'la valeur par defaut'} or re.search(r'\b(?:garde|conserve|utilise|prends|retiens)\s+(?:le defaut|la valeur par defaut)\b', text)
    if contextual and default_choice and 'default' in spec:
        if re.search(r"\b(?:pas|sans|refuse)\b|\bn['’]", text) or '?' in text:
            raise ValueError('Confirmez le choix du défaut pour le paramètre concerné.')
        return spec['default'], 'Défaut déclaré choisi en réponse à une question ciblée ; hypothèse à valider.'
    scale = spec.get('qualitative_scale')
    if not scale:
        return None
    matches = []
    for label, level in scale['levels'].items():
        for alias in level['aliases']:
            for match in re.finditer(r'(?<!\w)' + re.escape(fold(alias)) + r'(?!\w)', text):
                matches.append((label, level, match.start(), match.end()))
    # A specific expression ("très forte pente") supersedes its contained synonym.
    matches = [item for item in matches if not any(
        other[2] <= item[2] and other[3] >= item[3]
        and other[3] - other[2] > item[3] - item[2] for other in matches)]
    if not matches and contextual:
        for label, level in scale['levels'].items():
            if text in {fold(alias) for alias in level.get('answer_aliases', [label])}:
                matches.append((label, level, 0, len(text)))
    if not matches:
        return None
    remaining = list(text)
    for _, _, start, end in matches:
        remaining[start:end] = ' ' * (end - start)
    outside_aliases = ''.join(remaining)
    if len({item[0] for item in matches}) != 1 or re.search(r"\b(?:sans|aucun|moins)\b|\bpas\b(?!\s+(?:de\s+temps|temporel|fin|tres\s+fin|intermediaire|large|grossier))|\bn['’]", outside_aliases):
        raise ValueError('Qualification ambiguë ou négative : précisez le niveau souhaité.')
    label, level, _, _ = matches[0]
    # The local policy controls the number even if the extraction supplied another one.
    if 'value' in level:
        number = level['value']
        calculation = str(number)
    else:
        number = scale['reference_upper'] * level['fraction']
        if spec['type'] == 'int':
            if not number.is_integer():
                raise ValueError('Convention entière invalide dans le descripteur.')
            number = int(number)
        calculation = f"{level['fraction']} × {scale['reference_upper']} = {number}"
    source = (f"Convention qualitative : {label} = {calculation}. {scale['authority']} "
              f"{scale['interpretation']}")
    return number, source
