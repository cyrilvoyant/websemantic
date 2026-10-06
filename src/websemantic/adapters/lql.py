"""Read-only LQL-Equiv execution for one explicitly fictitious course."""

import csv
import hashlib
import importlib.util
import json
import math
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from websemantic.core.validation import validate
from websemantic.semantics import export_semantics

EXPECTED_COMMIT = "dfc9a338205b8864b8e3470c4ae245b019e88844"
# Filled from the pinned backend; line endings do not change numerical sources.
EXPECTED_FILES = {'__init__.py': '2685b5a34b0da98c8329928f1de533ec6619178c2e2e89e92d48e231ad7a9d82', 'data/__init__.py': 'c849ce7dc4c2cd921e57faf5ffa453f8772eeed07367af69f1f9d7288f1741dd', 'data/tissues.json': '63283344abdc8147da7e112e0a5d728d1dc0bc565ad9950e9e5adccd08027f61', 'model.py': '3e0638c077e2fd9a04fedf7520a8e0c008f88d61b6e28974abd9533d681e0800', 'schedule.py': '7cffecd6e82acf536521aab1c1f58ae997a6754d43185ae6d317752c057f7dfa', 'tissues.py': '9ef2ff4d9a93b040697e5199d6902ce0ca9888474591de56126accf826a05c15'}


def _backend(workspace, descriptor):
    if descriptor["software"]["commit"] != EXPECTED_COMMIT:
        raise ValueError("Révision LQL-Equiv incompatible avec cet adaptateur.")
    root = Path(workspace) / "external/LQL-Equiv-web/src/lqlequiv"
    for relative, expected in EXPECTED_FILES.items():
        digest = hashlib.sha256((root / relative).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if digest != expected:
            raise ValueError(f"Empreinte LQL-Equiv incorrecte : {relative}.")
    # The library uses importlib.resources on lqlequiv.data. Reject an unrelated
    # installed package instead of silently executing it.
    existing = sys.modules.get("lqlequiv")
    if existing is not None:
        if Path(existing.__file__).resolve() != (root / "__init__.py").resolve():
            raise ValueError("Un autre module lqlequiv est déjà chargé ; redémarrez Python.")
        return existing
    spec = importlib.util.spec_from_file_location(
        "lqlequiv", root / "__init__.py", submodule_search_locations=[str(root)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        for key in list(sys.modules):
            if key == "lqlequiv" or key.startswith("lqlequiv."):
                del sys.modules[key]
        raise
    return module


def run(scenario, descriptor, workspace, output_root=None):
    """Return native qualified indicators; never recommend a clinical dose."""
    gate = validate(scenario, descriptor)
    if gate.decision != "execute":
        raise ValueError("Scénario incomplet, non accepté ou hors du profil LQL fictif.")
    config = {name: item.value for name, item in scenario.inputs.items()}
    if scenario.experiment.get("scenario_scope").value != "fictitious":
        raise ValueError("Le profil accepte uniquement des scénarios fictifs de recherche.")
    module = _backend(workspace, descriptor)
    library = module.load_library()
    organ = library.organ(config["organ"])
    tumour = library.tumour_site(config["tumour_site"])
    course = module.Course(config["dose_per_fraction"], config["n_fractions"], config["gap_days"])
    prescription = module.Prescription(
        courses=(course,), reference_dose=config["reference_dose"],
        bifractionated=config["bifractionated"] == "yes",
    )
    result = module.compute(organ, tumour, prescription, options=module.Options())
    native = result.courses[0]
    oar_ok = result.oar_total_valid and not native.oar_saturated
    tumour_ok = result.tumour_total_valid and not native.tumour_saturated
    values = {
        "physical_dose_gy": course.total_dose,
        "bed_oar": native.bed_oar if result.oar_total_valid else None,
        "bed_tumour": native.bed_tumour if result.tumour_total_valid else None,
        "eqd_oar_total": result.eqd_oar_total if oar_ok else None,
        "eqd_tumour_total": result.eqd_tumour_total if tumour_ok else None,
        "ntcp_percent": result.ntcp_percent if oar_ok else None,
        "tcp_percent": result.tcp_percent if tumour_ok else None,
        "cancer_risk": result.cancer_risk if oar_ok else None,
        "overall_days_oar": native.overall_days_oar,
        "overall_days_tumour": native.overall_days_tumour,
    }
    if any(value is not None and not math.isfinite(value) for value in values.values()):
        raise ValueError("Sortie LQL-Equiv non finie ; résultat refusé.")
    flags = {
        "oar_total_valid": result.oar_total_valid, "tumour_total_valid": result.tumour_total_valid,
        "oar_saturated": native.oar_saturated, "tumour_saturated": native.tumour_saturated,
    }
    target = (Path(output_root) if output_root else Path(workspace) / "runs") / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    )
    target.mkdir(parents=True)
    row = {**values, **flags}
    with (target / "indicators.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    qualification = {"tables": {"indicators": {
        "file": "indicators.csv", "aggregation": "Un calcul déterministe, un seul cursus fictif.",
        "columns": {name: {"unit": spec.get("display_unit"), "meaning": spec["definition"]}
                    for name, spec in descriptor["outputs"].items()},
    }}}
    manifest = {
        "software": descriptor["software"], "scenario": asdict(scenario),
        "nature": descriptor["nature"], "validity_notes": descriptor["validity_notes"],
        "source_verification": {"method": "sha256_lf", "commit": EXPECTED_COMMIT,
                                "files": EXPECTED_FILES},
        "backend_options": asdict(result.options), "tissues": {"organ": asdict(organ), "tumour": asdict(tumour)},
        "flags": flags, "output_qualification": qualification,
        "null_policy": "EQD et probabilités dépendantes supprimées si invalides ou à la borne ; coefficient absent = null.",
    }
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2,
                                                      allow_nan=False), encoding="utf-8")
    (target / "scenario.json").write_text(json.dumps(asdict(scenario), ensure_ascii=False, indent=2), encoding="utf-8")
    export_semantics(scenario, qualification, target, descriptor)
    return target, values
