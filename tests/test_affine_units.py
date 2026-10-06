from websemantic.units import normalize


def test_celsius_evidence_overrides_wrong_extraction():
    spec={'unit':'unit:K','evidence_conversion':{'units':{'°c':{'factor':1,'offset':273.15},'k':1}}}
    value,unit,source=normalize(280,'unit:K','température 10 °C',spec)
    assert value==283.15 and unit=='unit:K'
    assert 'Extraction divergence' in source

def test_pressure_conversion():
    spec={'unit':'unit:PA','evidence_conversion':{'units':{'hpa':100,'pa':1}}}
    assert normalize(850,'hpa','pression 850 hPa',spec)[:2]==(85000,'unit:PA')


def test_relative_humidity_is_affine_but_supersaturation_is_not():
    from pathlib import Path

    import yaml
    spec=yaml.safe_load((Path(__file__).resolve().parents[1]/'descriptors/pyrcel/descriptor.yaml').read_text(encoding='utf-8'))['inputs']['S0']
    value,unit,_=normalize(-0.02,'unit:UNITLESS',"98 % d'humidité relative",spec)
    assert abs(value+0.02)<1e-15 and unit=='unit:UNITLESS'
    assert normalize(1,'%', 'sursaturation 1 %',spec)[:2]==(1,'%')
