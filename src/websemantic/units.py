"""Descriptor-declared, evidence-based unit normalisation."""

import re
import unicodedata


def fold(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if not unicodedata.combining(c))


# General French number words; independent of any scientific backend.
NUMBER_WORDS = {
    'zero': 0, 'un': 1, 'une': 1, 'deux': 2, 'trois': 3, 'quatre': 4,
    'cinq': 5, 'six': 6, 'sept': 7, 'huit': 8, 'neuf': 9, 'dix': 10,
    'onze': 11, 'douze': 12, 'treize': 13, 'quatorze': 14, 'quinze': 15,
    'seize': 16, 'dix-sept': 17, 'dix-huit': 18, 'dix-neuf': 19,
    'vingt': 20, 'trente': 30, 'quarante': 40, 'cinquante': 50, 'soixante': 60,
    'cent': 100,
}


def reject_ambiguous_number(text):
    compact = re.sub(r"\s", "", text)
    # A leading zero is a decimal fraction, e.g. 0,015, not a thousands group.
    if re.fullmatch(r"[+-]?[1-9]\d{0,2},\d{3}", compact):
        raise ValueError("Nombre ambigu : précisez 1500 pour mille cinq cents, ou 1.5 pour un et demi ; ne mélangez pas virgule décimale et séparateur de milliers.")


def numeric_literal(text):
    reject_ambiguous_number(text)
    return float(re.sub(r"\s", "", text).replace(",", "."))


def parse_number(value, kind):
    if type(value) not in (str, int, float):
        raise ValueError('Valeur numérique non reconnue ; précisez un nombre en chiffres.')
    text = fold(str(value).strip()).replace(' ', '-')
    if text in NUMBER_WORDS:
        number = NUMBER_WORDS[text]
        result = number if kind == 'int' else float(number)
        return result, f'Number word normalisation: {value!r} -> {result}.'
    if isinstance(value, str):
        # Check ambiguity before the generic conversion error handler.
        reject_ambiguous_number(value)
    try:
        if kind == 'int':
            # Reject a fractional value rather than truncate a count.
            if type(value) is float and not value.is_integer():
                raise ValueError
            return int(value), None
        return numeric_literal(str(value)), None
    except (ValueError, OverflowError):
        raise ValueError('Valeur numérique non reconnue ; précisez un nombre en chiffres.') from None


def normalize(value, unit, evidence, spec):
    canonical = spec.get('unit')
    conversion = spec.get('evidence_conversion')
    if conversion and conversion.get('trigger_regex') and not re.search(conversion['trigger_regex'], fold(evidence)):
        conversion = None
    if conversion:
        units = conversion['units']
        text = fold(evidence)
        alternatives = '|'.join(re.escape(name) for name in sorted(units, key=len, reverse=True))
        matches = re.findall(r'(?<![\w.,])([+-]?\d(?:[\d \u00a0\u202f]*\d)?(?:[.,]\d+)?)\s*(' + alternatives + r')(?!\w)', text)
        if not matches:
            words = conversion.get('word_numbers', {})
            if words:
                matches = [(str(words[word]), symbol) for word, symbol in re.findall(
                    r'\b(' + '|'.join(map(re.escape, words)) + r')\s*(' + alternatives + r')\b', text)]
        if len(matches) != 1:
            raise ValueError('Fournir une preuve avec une seule valeur et une unité explicitement déclarée.')
        number, symbol = matches[0]
        original = numeric_literal(number)
        rule = units[symbol]
        factor = rule['factor'] if isinstance(rule, dict) else rule
        offset = rule.get('offset', 0) if isinstance(rule, dict) else 0
        converted = original * factor + offset
        source = f'Exact normalisation: {original} {symbol} x {factor} + {offset} -> {canonical}'
        if unit == canonical or unit in spec.get('unit_aliases', []):
            interpreted = value
        elif unit in units:
            unit_rule = units[unit]
            interpreted = value * (unit_rule['factor'] if isinstance(unit_rule, dict) else unit_rule) + (unit_rule.get('offset', 0) if isinstance(unit_rule, dict) else 0)
        else:
            interpreted = None
        if interpreted is not None and interpreted != converted:
            source += f'; Extraction divergence: LLM value {value!r} {unit!r} -> {interpreted!r} {canonical}; evidence {evidence!r} -> {converted!r} {canonical}; exact evidence takes precedence.'
        return converted, canonical, source
    if unit != canonical and unit in spec.get('unit_aliases', []):
        return value, canonical, f'Unit label normalisation: {unit!r} -> {canonical!r}; numeric value unchanged.'
    return value, unit, None
