"""Development pilot: native numerical controls and bounded semantic probes."""
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from websemantic.adapters import lql, pyrcel, tls
from websemantic.core.validation import Parameter, Scenario
from websemantic.gemini import extract, load_private_key
from websemantic.registry import load_descriptor
from websemantic.session import ClarificationNeeded, Session

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work/first-pilot-20261006"
OUT.mkdir(parents=True, exist_ok=True)


def metric(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    assert a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
    rmsd = float(np.sqrt(np.mean((a-b)**2)))
    denom = float(np.sqrt(np.mean(b**2)))
    return {"n": a.size, "rmsd": rmsd, "nrmsd": rmsd / denom if denom else None}


def fixture(model):
    doc = json.loads((ROOT / f"examples/{model}-complete.json").read_text(encoding="utf-8"))
    return Scenario(doc["request"], doc["task"], **{g: {k: Parameter(**v) for k,v in doc[g].items()} for g in ("inputs", "experiment")})


def change(s, group, values):
    return replace(s, **{group: {**getattr(s, group), **{k: replace(getattr(s,group)[k], value=v) for k,v in values.items()}}})


def controls():
    results=[]
    for model in ("tls", "lql", "pyrcel"):
        d=load_descriptor(ROOT,model);s=fixture(model)
        if model=="tls":s=change(s,"experiment",{"n_days":7,"freq_minutes":60,"n_runs":3})
        if model=="pyrcel":
            s=change(s,"inputs",{"bins":10});s=change(s,"experiment",{"t_end":30,"output_dt":5,"terminate":"no"})
        for i in range(3):
            c=change(s,"inputs",{("traffic_level" if model=="tls" else "dose_per_fraction" if model=="lql" else "V"):([0.5,1,1.5] if model=="tls" else [2,3,4] if model=="lql" else [0.5,1,2])[i]})
            target, _ = {"tls":tls,"lql":lql,"pyrcel":pyrcel}[model].run(c,d,ROOT,OUT/model)
            inp={k:v.value for k,v in c.inputs.items()};exp={k:v.value for k,v in c.experiment.items()}
            if model=="tls":
                spec=importlib.util.spec_from_file_location("pilot_native_tls",ROOT/"external/tunnel-load-simulator/src/tunnel_load_simulator/simulator.py")
                mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
                native=mod.run_monte_carlo(mod.TunnelConfig(**inp),pd.Timestamp(exp["start_date"]),exp["n_days"],exp["freq_minutes"],exp["n_runs"],exp["base_seed"])
                actual = pd.read_csv(target/"representative.csv")
                assert np.array_equal(pd.to_datetime(actual["timestamp"]),pd.to_datetime(native["representative"]["timestamp"]))
                pairs={k:(actual[k],native["representative"][k]) for k in ("power_kw","energy_kwh")}
                native["representative"].to_csv(target/"native_reference.csv",index=False)
            elif model=="lql":
                mod=lql._backend(ROOT,d);lib=mod.load_library();course=mod.Course(inp["dose_per_fraction"],inp["n_fractions"],inp["gap_days"])
                native=mod.compute(lib.organ(inp["organ"]),lib.tumour_site(inp["tumour_site"]),mod.Prescription((course,),inp["reference_dose"],inp["bifractionated"]=="yes"),options=mod.Options())
                frame=pd.read_csv(target/"indicators.csv")
                pairs={k:([frame[k][0]],[getattr(native,k)]) for k in ("eqd_oar_total","eqd_tumour_total")}
                (target/"native_reference.json").write_text(json.dumps({k:float(v[1][0]) for k,v in pairs.items()}),encoding="utf-8")
            else:
                import pyrcel as pm
                aerosol=pm.AerosolSpecies("mode1",pm.Lognorm(inp["mu"],inp["sigma"],inp["N"]),inp["kappa"],bins=inp["bins"])
                native=pm.ParcelModel([aerosol],V=inp["V"],T0=inp["T0"],P0=inp["P0"],S0=inp["S0"],accom=inp["accom"],console=False).run(exp["t_end"],output_dt=exp["output_dt"],terminate=False)
                frame,_=native.to_pandas();actual=pd.read_csv(target/"trajectory.csv")
                assert np.array_equal(actual.time_s.to_numpy(),native.time)
                pairs={k:(actual[k],frame[k]) for k in ("T","S")};frame.to_csv(target/"native_reference.csv")
            results.append({"model":model,"case":i+1,"metrics":{k:metric(*pair) for k,pair in pairs.items()},"run":str(target.relative_to(ROOT))})
            print(model,i+1,"reference compared",flush=True)
    return results


def probes():
    load_private_key(ROOT)
    cases=[("tls","Un tunnel de moins de deux kilomètres avec beaucoup de trafic : calcule."),
           ("tls","Estime la consommation du tunnel du Vieux-Port de Marseille, il est assez gros et avec un peu de trafic."),
           ("lql","Compare un hypofractionnement modéré au schéma conventionnel pour la prostate et le rectum."),
           ("pyrcel","Simule une parcelle avec une forte ascendance dans un air très pollué.")]
    results=[]
    for model,request in cases:
        d=load_descriptor(ROOT,model);session=Session(d)
        try:
            parsed, usage=extract(request,d,[],state=None)
            (OUT/f"probe-{len(results)+1}.json").write_text(json.dumps({"request":request,"response":parsed,"usage":usage},ensure_ascii=False,indent=2),encoding="utf-8")
            session.apply(request,parsed)
            gate=session.result()
            records={f"{g}.{k}":{"value":v.value,"origin":v.origin,"accepted":v.accepted,"source":v.source} for g in ("inputs","experiment") for k,v in getattr(session.scenario,g).items()}
            results.append({"model":model,"request":request,"decision":gate.decision,"expected":"clarify","decision_correct":gate.decision=="clarify","needs_web":parsed.get("needs_web"),"records":records,"questions":parsed.get("questions",[]),"issues":[i.code for i in gate.issues]})
        except ClarificationNeeded as exc:
            results.append({"model":model,"request":request,"decision":"clarify","expected":"clarify","decision_correct":True,"reason":str(exc),"layer":"local conversation guard","needs_web":parsed.get("needs_web")})
        except (ValueError, TypeError, RuntimeError) as exc:
            results.append({"model":model,"request":request,"error":str(exc),"decision_correct":False})
        print(model,"probe",len(results),flush=True)
    return results


if __name__=="__main__":
    report={"scope":"Development pilot; no held-out evidence, no ontology ablation, no multi-provider comparison", "numerical":controls(),"semantic":probes()}
    (OUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print("Saved",OUT/"report.json")
