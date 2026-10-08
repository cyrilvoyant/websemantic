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


def test_descriptor_declared_alias_preserves_scientific_value():
    c,a=example();a['parsed']['values'][0]['unit']='m'
    r=scorer.score(c,a,{})
    assert r['unit_canonical_exact']==0 and r['unit_correct']==1
    assert r['scientific_interpretation_valid']==1


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


@pytest.mark.parametrize('value,quote,unit,field', [
    (3218.688,'2 miles','unit:M','length_m'), (0.6096,'deux pieds','unit:M','length_m'),
    (85000,'850 mbar','unit:PA','p0'), (.5,'50 cm/s','unit:M-PER-SEC','v'),
    (.05,'diamètre 0,1 µm','unit:MicroM','mu')])
def test_additional_exact_conversions(value,quote,unit,field):
    assert scorer.evidence_value(value,quote,unit,field)


def test_mile_conversion_does_not_count_as_unsupported():
    c,a=example();c['turns']=['Tunnel de 2 miles. Calcule.'];c['expected_fields']['inputs.length_m']=3218.688
    a['parsed']['values'][0].update(value=3218.688,evidence='2 miles')
    assert scorer.score(c,a,{})['scientific_interpretation_valid']==1


def test_false_conversion_stays_unsupported():
    assert not scorer.evidence_value(2000,'2 miles','unit:M','length_m')


def test_admissible_alternative_is_scored():
    c,a=example();c['decision']='clarify';c['admissible']=['execute']
    assert scorer.score(c,a,{})['scientific_interpretation_valid']==1


def test_comparison_verdict_does_not_credit_unchecked_config():
    c,a=example();c['expected_fields']={};c['expected_comparison']={'Prostate':{'verdict':'trade-off'}}
    a['parsed']['comparisons']=[{'target':'Prostate','verdict':'tradeoff'}]
    r=scorer.score(c,a,{})
    assert r['comparison_verdict_valid']==1 and r['scientific_interpretation_valid']==''


def test_undefined_kpi_requires_indeterminate_verdict():
    case={'expected_comparison':{'Lung':{'verdict':'not decidable: undefined'}}}
    assert scorer.comparison_score(case,{'comparisons':[{'target':'Lung','verdict':'tradeoff'}]})[0]==0
    assert scorer.comparison_score(case,{'comparisons':[{'target':'Lung','verdict':'indeterminate'}]})[0]==1


def test_integral_count_must_be_json_integer():
    c,a=example();c['expected_fields']={'inputs.n_tubes':2};c['turns']=['deux tubes']
    a['parsed']['values']=[{'field':'inputs.n_tubes','value':2.,'unit':'unit:NUM','origin':'provided','evidence':'deux tubes'}]
    assert scorer.score(c,a,{})['type_or_bound_errors']==1


def test_variant_metadata_is_not_an_answer():
    c,a=example();c['variant']={'to':'length_m=99'}
    assert scorer.score(c,a,{})['scientific_interpretation_valid']==1

def test_comparison_respects_declared_left_right():
    case={'expected_comparison':{'Prostate':{'verdict':'A dominates','tcp_ntcp_percent':{'A':[90,5],'B':[80,10]}}}}
    assert scorer.comparison_score(case,{'comparisons':[{'target':'Prostate','left':'B','right':'A','verdict':'left_dominates'}]})[0]==0
    assert scorer.comparison_score(case,{'comparisons':[{'target':'Prostate','left':'B','right':'A','verdict':'right_dominates'}]})[0]==1


def test_malformed_comparison_target_is_failure():
    case={'expected_comparison':{'Prostate':{'verdict':'trade-off'}}}
    assert scorer.comparison_score(case,{'comparisons':[{'target':['Prostate'],'verdict':'tradeoff'}]})[0]==0
