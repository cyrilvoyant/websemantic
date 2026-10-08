"""Scientific screen must distinguish a correct value from a usable interpretation."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'evaluation/e1'))
import score_e1_v2 as scorer


def example():
    case = {'id':'TEST','domain':'tls','family':'complete','group':'test','decision':'execute',
            'turns':['Tunnel de 2 km. Calcule.'], 'expected_fields':{'inputs.length_m':2000}}
    answer = {'case_id':'TEST','domain':'tls','condition':'B0','rep':1,'model':'test',
              'parsed':{'decision':'execute','values':[{'field':'inputs.length_m','value':2000,
                        'unit':'unit:M','origin':'provided','evidence':'2 km'}]}}
    return case,answer


def test_correct_value_and_unit():
    c,a=example()
    r=scorer.score(c,a,{})
    assert r['scientific_interpretation_valid']==1
    assert r['execution_verified']==0


def test_correct_value_wrong_unit_fails():
    c,a=example();a['parsed']['values'][0]['unit']='unit:GRAY'
    r=scorer.score(c,a,{})
    assert r['n_correct']==1 and r['value_unit_correct']==0
    assert r['scientific_interpretation_valid']==0


@pytest.mark.parametrize('parsed', [[], 'text', 4, None, {'decision':'execute','values':'bad'}])
def test_invalid_root_or_values_does_not_crash(parsed):
    c,a=example();a['parsed']=parsed
    r=scorer.score(c,a,{})
    assert r['format_valid']==0 and r['scientific_interpretation_valid']==0


def test_duplicate_field_not_silently_accepted():
    c,a=example();a['parsed']['values']*=2
    r=scorer.score(c,a,{})
    assert r['duplicate_fields']==1 and r['scientific_interpretation_valid']==0


def test_unaccepted_default_fails():
    c,a=example();a['parsed']['values'][0]['origin']='default'
    assert scorer.score(c,a,{})['scientific_interpretation_valid']==0


def test_numeric_string_is_not_executable_numeric_type():
    c,a=example();a['parsed']['values'][0]['value']='2000'
    r=scorer.score(c,a,{})
    assert r['wrong_numeric_types']==1 and r['scientific_interpretation_valid']==0


def test_unreferenced_execution_is_unscored():
    c,a=example();c['expected_fields']={}
    assert scorer.score(c,a,{})['scientific_interpretation_valid']==''
