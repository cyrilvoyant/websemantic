"""Counter-examples from Codex's independent review (7 Oct 2026) become regression tests of the E1 scorer."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluation" / "e1"))

import score_e1 as s


def test_sign_preserved():
    assert s.value_in_evidence(-0.01, "S0 = -0,01", "unit:UNITLESS", "s0")


def test_relative_humidity_to_s0():
    assert s.value_in_evidence(-0.02, "humidité 0,98", "unit:UNITLESS", "s0")
    assert s.value_in_evidence(-0.02, "98 % d'humidité relative", "unit:UNITLESS", "s0")


def test_conversion_requires_the_field_unit_token():
    assert not s.value_in_evidence(2000, "2 Gy", "unit:M", "length_m")
    assert s.value_in_evidence(2000, "tunnel de 2 km", "unit:M", "length_m")
    assert not s.value_in_evidence(1.5, "tunnel de 2 km", "unit:UNITLESS", "traffic_level")


def test_other_exact_conversions():
    assert s.value_in_evidence(7.5, "pointes à 7 h 30", "unit:HR", "morning_peak_hour")
    assert s.value_in_evidence(283.15, "10 °C", "unit:K", "t0")
    assert s.value_in_evidence(85000, "850 hPa", "unit:PA", "p0")
    assert s.value_in_evidence(60, "au pas horaire", "unit:MIN", "freq_minutes")
    assert s.value_in_evidence(14, "deux semaines", "unit:DAY", "n_days")
    assert s.value_in_evidence(0.05, "bruit relatif 5 %", "unit:UNITLESS", "noise_sigma")


def test_acceptance_of_defaults():
    assert s.accepts_defaults("Tunnel de 1,5 km, deux tubes, valeurs par défaut, calcule.")
    assert s.accepts_defaults("valeurs par défaut pour le reste, calcule")
    assert s.accepts_defaults("Valeurs par défaut acceptées pour le reste.")
    assert s.accepts_defaults("Pour le reste, prends les valeurs par défaut.")
    assert not s.accepts_defaults("Si je les accepte, prends les valeurs par défaut.")
    assert not s.accepts_defaults("Ne prends pas les valeurs par défaut.")
    assert not s.accepts_defaults("Propose les défauts sans les accepter.")
