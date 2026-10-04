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
            if re.search(r'(?<!\w)' + re.escape(fold(alias)) + r'(?!\w)', text):
                matches.append((label, level))
                break
    if not matches:
        return None
    if len(matches) != 1 or re.search(r"\b(?:pas|sans|aucun|moins)\b|\bn['’]", text):
        raise ValueError('Qualification ambiguë ou négative : précisez le niveau souhaité.')
    label, level = matches[0]
    # The local policy controls the number even if the extraction supplied another one.
    number = scale['reference_upper'] * level['fraction']
    source = (f"Convention qualitative : {label} = {level['fraction']} × "
              f"{scale['reference_upper']} = {number}. {scale['authority']} "
              f"{scale['interpretation']}")
    return number, source
