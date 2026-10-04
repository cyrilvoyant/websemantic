"""Locally controlled conversation actions proposed by the interpreter."""

import re

from websemantic.units import fold

ACTIONS = {"propose", "accept", "details", "explain", "suggest", "quit"}


def requested_actions(parsed):
    actions = parsed.get("actions", [])
    if not isinstance(actions, list) or any(action not in ACTIONS for action in actions):
        raise ValueError("Action conversationnelle non reconnue.")
    return set(actions)


def explicit_consent(request, evidence):
    if not isinstance(evidence, str) or not evidence or evidence not in request:
        return False
    text = fold(request)
    if "?" in text or re.search(r"\bne\b.*?\bpas\b|\bn['’].*?\bpas\b|\b(?:sans|refuse)\b", text):
        return False
    if re.fullmatch(r"\s*(?:prends|utilise|accepte)\s+le\s+reste\s+par\s+defaut\s*[.!]?\s*", fold(evidence)):
        return True
    return bool(re.fullmatch(
        r"\s*(?:j['’]accepte|je valide|accepte|valide|prends|utilise)\s+"
        r"(?:(?:toutes?|tous)\s+)?(?:les|ces|des)\s+"
        r"(?:hypotheses(?: proposees)?|parametres(?: proposes)?|valeurs(?: proposees| par defaut| moyennes| du profil)?)"
        r"(?:\s*(?:[,;]|et|puis)\s*(?:lance le calcul|calcule|simule))?\s*[.!]?\s*", fold(evidence)))
