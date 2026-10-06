import json, sys, time, importlib.metadata, platform, subprocess
from pathlib import Path
import numpy as np
kind=sys.argv[1]
base=Path(__file__).resolve().parent
output=base/'reports'/kind
output.mkdir(parents=True,exist_ok=True)
if kind=='pyrcel':
    sys.path.insert(0,str(base/'pyrcel'))
    import pyrcel as pm
    def run():
        species=pm.AerosolSpecies('sulfate',pm.Lognorm(mu=0.05,sigma=2.0,N=1000.0),kappa=0.54,bins=10)
        model=pm.ParcelModel([species],V=1.0,T0=283.0,S0=-0.02,P0=85000.0,console=False)
        result=model.run(30.0,output_dt=5.0,terminate=False)
        frame,_=result.to_pandas()
        return result.state,frame
else:
    sys.path.insert(0,str(base/'ecape-parcel-py'/'src'))
    from ecape_parcel.calc import calc_ecape_parcel
    from metpy.units import units
    import pandas as pd
    z=np.arange(0.,14001.,250.)
    pressure=100000*np.exp(-z/8000)*units.Pa
    temperature=(303.15-0.007*z)*units.K
    dewpoint=(296.15-0.008*z)*units.K
    u=(5.+z/1000)*units('m/s');v=(2.+z/2000)*units('m/s')
    def run():
        result=calc_ecape_parcel(pressure,z*units.m,temperature,dewpoint,u,v,True,entrainment_switch=False,pseudoadiabatic_switch=True,cape_type='surface_based')
        arrays=[a.magnitude for a in result]
        frame=pd.DataFrame(dict(zip(['pressure','height','temperature','qv','qt'],arrays)))
        return np.column_stack(arrays),frame
started=time.perf_counter()
a,frame=run()
b,_=run()
assert np.isfinite(a).all() and a.shape==b.shape
error=float(np.max(np.abs(a-b)))
assert error<=1e-9
frame.to_csv(output/'trajectory.csv',index=False)
repository=base/('pyrcel' if kind=='pyrcel' else 'ecape-parcel-py')
report=dict(kind='synthetic_candidate_smoke',candidate=kind,python=sys.version,platform=platform.platform(),source_revision=subprocess.check_output(['git','-C',str(repository),'rev-parse','HEAD'],text=True).strip(),rows=len(frame),columns=list(frame),shape=list(a.shape),elapsed_seconds=time.perf_counter()-started,max_repeat_difference=error,finite=True,versions={p.metadata['Name']:p.version for p in importlib.metadata.distributions()},scope='One synthetic case repeated twice; not cross-platform validation or an LLM benchmark')
(output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ('candidate','rows','elapsed_seconds','max_repeat_difference','finite')}))
