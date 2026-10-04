"""Resolve descriptor-defined qualitative levels as traceable assumptions."""

import re
import unicodedata


def fold(text):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', text.lower())
                            if not unicodedata.combining(c)).split())


def resolve(evidence, spec):
    scale = spec.get('qualitative_scale')
    if not scale:
        return None
    text = fold(evidence)
    # A numeric instruction takes precedence; this resolver does not reinterpret it.
    if re.search(r'\d', text):
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
