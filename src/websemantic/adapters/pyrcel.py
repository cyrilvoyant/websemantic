"""Read-only pyrcel 2.0.0 adapter: constant updraft, one lognormal mode."""
import hashlib
import importlib.metadata
import json
import os
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from websemantic.core.validation import validate
from websemantic.semantics import export_semantics

COMMIT = "977e9094644ec4a17d658d657094651928591c89"
SOURCE_HASHES = {'pyrcel/aerosol.py': 'd7fc5c1d055a5d6868aae53430a7d1c0797ff4c8f73caff387aef5900fcfc9c4', 'pyrcel/console_report.py': '2f64b98e0bda566582e46a6938c142d1aed361f9f3503f17864b5f153a98bf6e', 'pyrcel/constants.py': '7d75523d46874bb1faeaff3191f7effe27dc8e6e7866976dd72dc7b6d5df52d8', 'pyrcel/distributions.py': '712f41b5e72f54c3cb243d6e7708f8cb014c9f897f97a322ffac1ba832f1eb2e', 'pyrcel/ensemble.py': '856d97c73873061dfeae77c69db5da23d3b15019864808a9180ec6dd66e2641c', 'pyrcel/equilibrate.py': 'c85e21765e25589279d438f405b92bffabeac9115b290bfb76a3f3037cc0ffe7', 'pyrcel/integrator.py': 'd08876ea45151dd0fc2119aec2d4964dc0028087a904da4d7d006723b3e85992', 'pyrcel/model.py': '6c4cf795c682e4acb4b6531b4cd1fc3bf6b0689df9d046625862f0b8ef1ad5f0', 'pyrcel/model_output.py': '7214480542a6248ee914cd0e5709fd5223faf65f022bee3d6eea147ec0f64a3d', 'pyrcel/output.py': 'd7e543ed4d73fd853421f7106b0503dd3991c93a90082adfb180d2935514c472', 'pyrcel/parcel_aux.py': '07d56e3854d16acf309666d1444136fb1c52d5652d29442482a2047eadc91735', 'pyrcel/thermo.py': '779d453484e25b708afda3517f9d8f1303dd40c5ee1ead77c9ac01119cdccd80', 'pyrcel/updraft.py': 'f299171a7da17bbf206fe82b8a15a137e84265c2268b5489d32570e0f5a499ba', 'pyrcel/util.py': '7a1e64350e830870a5582822d2c93518cf18638e723fdc3333299855760db352', 'pyrcel/_types.py': '8e72187aa2c824f7adc4c784dcad676fc082b0487a422809a4619236eeb4561a', 'pyrcel/__init__.py': 'e4a30cbc78b63ef61c5a32f852a27362096c60a97f82c075b290a85acf050639', 'pyrcel/activation/_arg2000.py': 'e107a9c8ac418b09a9e6717bf14d108280ed02c2fc0ac159403cfb45d15f2ead', 'pyrcel/activation/_common.py': '383585cd6c00f2a9a7b940e3b7fa539132aba0981ac67db5f8ad061ec374514c', 'pyrcel/activation/_mbn2014.py': 'dd96adaa9c0282324b072dcf9f51dcac72507c75c0bb85d3cb7ee3f7a9f1a79d', 'pyrcel/activation/_scheme.py': 'f3976646eba72b0b81c4538be92c92fed60c39e4ec7a05bab6e204b9174254c7', 'pyrcel/activation/__init__.py': '9dd0d8a8e2246f6cc8e7aba01bc493c2cad47c9144752908f9a1e251a207cfd2', 'pyrcel/legacy/activation.py': 'f1e283f36d95ae373f705245f46d9beffebaed071a2e4e5ea8af1b81c8b4145d', 'pyrcel/legacy/postprocess.py': '4b763e13f904cd5c0662fbd43dc52e77acbedee61a6aaf9e7d19962216653dbc', 'pyrcel/legacy/thermo.py': '94e21fd06e573ebbadcf7e0ff5b2831f4e06b08f8e02ae185aeaae89e2c61a32', 'pyrcel/legacy/vis.py': '932c8ded03dcf9daeea05a6f9a5c8021841204d92afa32e1dcf85042e9b58a0d', 'pyrcel/legacy/__init__.py': '21ec0430ebb1bfdeef5e73bdf1f4227c23d83bc4d460b94a4f658f23bd45d34a', 'pyrcel/scripts/run_parcel.py': 'd8a45a5f535f469cd8ec6d9bfbc645bd3d28bc1dfc0cdc1f4496a1ccd5d40f4d', 'pyrcel/scripts/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'pyrcel/test/generate_data.py': '5fcb1e9f4840c56e4834bbdfa8b3bf25dcd1fe09990f5e24998f3fa3a86165a7', 'pyrcel/test/pm_test.py': 'f0733f17aadccb1620e7c453c46647f9588c39bd7d2f5e79c165ad6671934ad8', 'pyrcel/test/test_thermo.py': '3f6f0bcb7ccec593246c5578fde57c3bcacc63729b3b1bc859da453c2f3b54d3', 'pyrcel/test/__init__.py': 'aedf1b7eccb3cfb02226205f82309a1290079ce31ed5204325781ee2bf368fc7'}


def verify_source(backend):
    """Verify every Python module in the reviewed package, without requiring Git."""
    actual = {str(p.relative_to(backend)).replace("\\", "/") for p in (backend / "pyrcel").rglob("*.py")}
    if actual != set(SOURCE_HASHES):
        raise ValueError("Modules pyrcel inattendus ou manquants; relancez Installer.")
    for name, expected in SOURCE_HASHES.items():
        digest = hashlib.sha256((backend / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if digest != expected:
            raise ValueError("Code pyrcel modifié : " + name)
    return {"method": "sha256_lf", "commit": COMMIT, "files": SOURCE_HASHES}


def run(scenario, descriptor, workspace, output_root=None):
    gate = validate(scenario, descriptor)
    if gate.decision != "execute":
        raise ValueError("Paramètres incomplets ou hypothèses non acceptées : " + "; ".join(i.field + ": " + i.code for i in gate.issues))
    if descriptor["software"]["commit"] != COMMIT:
        raise ValueError("Révision pyrcel incorrecte.")
    params = {k: v.value for k, v in scenario.inputs.items()}
    experiment = {k: v.value for k, v in scenario.experiment.items()}
    if experiment["output_dt"] > experiment["t_end"] or experiment["t_end"] / experiment["output_dt"] > 100000:
        raise ValueError("Pas de sortie incompatible avec la durée ou expérience trop volumineuse.")
    workspace = Path(workspace)
    backend = workspace / "external/pyrcel"
    if not backend.is_dir():
        backend = workspace / "work/candidates/pyrcel"
    verification = verify_source(backend)
    # Must configure before importing JAX; refuse a previously initialised incompatible runtime.
    os.environ["JAX_ENABLE_X64"] = "true"
    os.environ["JAX_PLATFORMS"] = "cpu"
    try:
        import jax
        importlib.import_module("diffrax")  # required solver; checked before source import
    except ImportError as exc:
        raise ValueError("Composants pyrcel manquants; lancez Installer.cmd pour installer le profil atmosphérique.") from exc
    jax.config.update("jax_enable_x64", True)
    if any(device.platform != "cpu" for device in jax.devices()):
        raise ValueError("Ce profil nécessite JAX CPU.")
    sys.path.insert(0, str(backend))
    try:
        import pyrcel as pm
        if Path(pm.__file__).resolve() != (backend / "pyrcel/__init__.py").resolve():
            raise ValueError("Un autre module pyrcel est déjà chargé; ouvrez une nouvelle session.")
        import numpy as np
        aerosol = pm.AerosolSpecies("mode1", pm.Lognorm(mu=params["mu"], sigma=params["sigma"], N=params["N"]), kappa=params["kappa"], bins=params["bins"])
        model = pm.ParcelModel([aerosol], V=params["V"], T0=params["T0"], P0=params["P0"], S0=params["S0"], accom=params["accom"], console=False)
        output = model.run(experiment["t_end"], output_dt=experiment["output_dt"], terminate=experiment["terminate"] == "yes", terminate_depth=experiment["terminate_depth"])
    except ImportError as exc:
        raise ValueError("Composants pyrcel manquants; lancez Installer.cmd pour installer le profil atmosphérique.") from exc
    finally:
        sys.path.remove(str(backend))
    if not np.isfinite(output.state).all() or not np.isfinite(output.time).all():
        raise ValueError("Sortie pyrcel non finie; résultat refusé.")
    if len(output.time) < 2 or np.any(np.diff(output.time) <= 0):
        raise ValueError("Support temporel invalide.")
    frame, aerosol_frames = output.to_pandas()
    frame = frame.reset_index()
    frame.rename(columns={frame.columns[0]: "time_s"}, inplace=True)
    if not np.array_equal(frame["time_s"].to_numpy(), output.time):
        raise ValueError("Le support temporel natif n’a pas été conservé.")
    metrics = {"maximum_supersaturation_percent": float(output.summary["S_max"]) * 100, "activated_number_cm3": float(output.Nd) / 1e6, "activated_fraction": float(output.nd_frac), "actual_end_time_s": float(output.time[-1])}
    if not all(np.isfinite(v) for v in metrics.values()):
        raise ValueError("Indicateurs pyrcel non finis.")
    target = (Path(output_root) if output_root else workspace / "runs") / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    target.mkdir(parents=True)
    frame.to_csv(target / "trajectory.csv", index=False)
    wet = aerosol_frames["mode1"].reset_index()
    wet.rename(columns={wet.columns[0]: "time_s"}, inplace=True)
    wet.to_csv(target / "wet_radii.csv", index=False)
    import pandas as pd
    pd.DataFrame([metrics]).to_csv(target / "kpis.csv", index=False)
    qualification = {"trajectory": {"units": {"time_s": "s", "z": "m", "P": "Pa", "T": "K", "wv": "kg/kg", "wc": "kg/kg", "wi": "kg/kg", "S": "1"}, "temporal_support": "Exact native timestamps; nominal output_dt; final interval may be irregular"}, "wet_radii": {"time_unit": "s", "all_radius_columns_unit": "m", "definition": "Wet particle radius per size bin; not dry diameter"}, "kpis": {"maximum_supersaturation_percent": {"unit": "%", "definition": "Native solver peak locator; may differ from sampled CSV maximum"}, "activated_number_cm3": {"unit": "cm^-3", "definition": "Native hard-activation count at actual final output time"}, "activated_fraction": {"unit": "1", "definition": "Native activation fraction at actual final time"}, "actual_end_time_s": {"unit": "s", "definition": "Actual end; t_end is a maximum"}}}
    qualification['tables'] = {
        'trajectory': {'file': 'trajectory.csv', 'aggregation': 'Pas natif exact, dernier intervalle potentiellement irrégulier.',
            'columns': {name: {'unit': unit, 'meaning': name + ' : sortie native de la parcelle idéale.'} for name, unit in qualification['trajectory']['units'].items()}},
        'wet_radii': {'file': 'wet_radii.csv', 'aggregation': 'Rayons humides par classe aux instants natifs.',
            'columns': {name: {'unit': 's' if name == 'time_s' else 'm', 'meaning': 'Temps natif' if name == 'time_s' else 'Rayon humide, pas diamètre sec'} for name in wet.columns}},
        'kpis': {'file': 'kpis.csv', 'aggregation': 'Indicateurs natifs ; activation à la fin effective.',
            'columns': {name: {'unit': spec['unit'], 'meaning': spec['definition']} for name, spec in qualification['kpis'].items()}}
    }
    export_semantics(scenario, qualification, target, descriptor)
    versions = {name: importlib.metadata.version(name) for name in ("jax", "jaxlib", "diffrax", "equinox", "optimistix", "numpy", "pandas", "scipy")}
    manifest = {"software": descriptor["software"], "source_verification": verification, "scenario": asdict(scenario), "nature": descriptor["nature"], "validity_notes": descriptor["validity_notes"], "output_qualification": qualification, "execution": {"python": sys.version, "versions": versions, "jax_backend": "cpu", "jax_enable_x64": bool(jax.config.jax_enable_x64), "requested_maximum_duration_s": experiment["t_end"], "actual_duration_s": metrics["actual_end_time_s"]}}
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8")
    (target / "scenario.json").write_text(json.dumps(asdict(scenario), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf8")
    return target, metrics
