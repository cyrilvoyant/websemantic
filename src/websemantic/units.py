"""Descriptor-declared, evidence-based unit normalisation."""

import re
import unicodedata


def fold(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if not unicodedata.combining(c))


def normalize(value, unit, evidence, spec):
    canonical = spec.get('unit')
    conversion = spec.get('evidence_conversion')
    if conversion:
        units = conversion['units']
        text = fold(evidence)
        alternatives = '|'.join(re.escape(name) for name in sorted(units, key=len, reverse=True))
        matches = re.findall(r'(?<![\w.,])([+-]?\d(?:[\d \u00a0\u202f]*\d)?(?:[.,]\d+)?)\s*(' + alternatives + r')\b', text)
        if not matches:
            words = conversion.get('word_numbers', {})
            if words:
                matches = [(str(words[word]), symbol) for word, symbol in re.findall(
                    r'\b(' + '|'.join(map(re.escape, words)) + r')\s*(' + alternatives + r')\b', text)]
        if len(matches) != 1:
            raise ValueError('Fournir une preuve avec une seule valeur et une unité explicitement déclarée.')
        number, symbol = matches[0]
        original = float(re.sub(r'\s', '', number).replace(',', '.'))
        factor = units[symbol]
        return original * factor, canonical, f'Exact normalisation: {original} {symbol} x {factor} -> {canonical}'
    if unit != canonical and unit in spec.get('unit_aliases', []):
        return value, canonical, f'Unit label normalisation: {unit!r} -> {canonical!r}; numeric value unchanged.'
    return value, unit, None
