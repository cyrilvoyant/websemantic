from pathlib import Path

import yaml
from rdflib import Literal

from websemantic.semantics import PROV, WS, vocabulary
from websemantic.units import normalize


def test_pyrcel_converted_outputs_remain_distinct():
    d = yaml.safe_load(Path("descriptors/pyrcel/descriptor.yaml").read_text(encoding="utf-8"))
    g = vocabulary(d)
    assert d["inputs"]["N"]["unit"] == "unit:PER-CentiM3"
    assert (WS.PYR_Smax_percent, PROV.wasDerivedFrom, WS.PYR_Smax) in g
    assert (WS.PYR_Nd_cm3, WS.conversionFactor, Literal(1e-6)) in g


def test_lql_category_unit_labels_normalize_without_changing_value():
    d = yaml.safe_load(Path("descriptors/lqlequiv/descriptor.yaml").read_text(encoding="utf-8"))
    value, unit, trace = normalize("Rectum", "unit:UNITLESS", "Rectum", d["inputs"]["organ"])
    assert value == "Rectum" and unit is None and trace
    assert d["experiment"]["scenario_scope"]["default"] == "fictitious"
