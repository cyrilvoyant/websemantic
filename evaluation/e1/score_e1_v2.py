"""Versioned first-turn scientific interpretation screen. Never credits execution.

Canonical units are required: differently encoded units are unverified here, not
declared physically wrong. Unsupported reference scopes remain unscored. Original
scores and running collectors are unchanged. CLI: reserve-path output-directory.
"""
import csv
import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path

import score_e1 as legacy

VERSION = '2.0-first-turn-canonical-units'

field_units = lru_cache(maxsize=3)(legacy.field_units)
default_values = lru_cache(maxsize=3)(legacy.defaults)


def score(case, answer, defaults):
    units = field_units(case['domain'])
    legacy.UNITS_BY_DOMAIN[case['domain']] = units
    parsed = answer.get('parsed')
    valid = isinstance(parsed, dict) and parsed.get('decision') in ('execute', 'clarify', 'refuse')
    values = parsed.get('values', []) if isinstance(parsed, dict) else []
    valid = valid and isinstance(values, list) and all(isinstance(v, dict) and 'field' in v and 'value' in v for v in values)
    safe = dict(answer, parsed=parsed if valid else {})
    row = legacy.score(case, safe, defaults)
    counts = {}
    for v in values if isinstance(values, list) else []:
        if isinstance(v, dict):
            name = legacy.norm(v.get('field', ''))
            counts[name] = counts.get(name, 0) + 1
    duplicates = sum(n > 1 for n in counts.values())
    supplied = {legacy.norm(v['field']): v for v in values if isinstance(v, dict) and 'field' in v and 'value' in v} if isinstance(values, list) else {}
    expected = legacy.expected(case)
    unit_correct = sum(name in supplied and supplied[name].get('unit') == units.get(name) for name in expected)
    joint = sum(name in supplied and legacy.same(supplied[name]['value'], value)
                and supplied[name].get('unit') == units.get(name) for name, value in expected.items())
    wrong_types = sum(isinstance(value, (int, float)) and not isinstance(value, bool)
                      and name in supplied and (not isinstance(supplied[name]['value'], (int, float))
                                              or isinstance(supplied[name]['value'], bool))
                      for name, value in expected.items())
    scoped = row['decision_ok'] != '' and not (row['decision'] == 'execute' and not expected)
    success = ''
    if scoped:
        success = int(valid and not duplicates and row['decision_ok'] == 1 and not row['hallucination'])
        if row['decision'] == 'execute':
            success = int(success and joint == len(expected) and not wrong_types)
        if case.get('family') == 'qualifier':
            success = int(success and row['qualifier_convention_ok'] == 1)
    request = case['turns'][0]
    identity = hashlib.sha256((case['domain'] + '\n' + request.strip()).encode()).hexdigest()
    return row | {'scorer_version': VERSION, 'format_valid': int(valid), 'duplicate_fields': duplicates,
                  'unit_correct': unit_correct, 'value_unit_correct': joint, 'wrong_numeric_types': wrong_types,
                  'scientific_interpretation_valid': success, 'scope_unscored': int(not scoped),
                  'first_turn_sha256': identity, 'execution_verified': 0}


def main():
    reserve, output = map(Path, sys.argv[1:3])
    reference_root = next((p for p in [reserve.parent/'semantic-sim-layer', reserve.parent/'source']
                           if (p/'descriptors').is_dir()), None)
    if reference_root is None:
        raise ValueError('Frozen descriptor directory missing beside the reserve; do not score against mutable sources')
    legacy.REPO = reference_root
    field_units.cache_clear()
    default_values.cache_clear()
    output.mkdir(parents=True, exist_ok=True)
    legacy.RESERVE = reserve
    cases = {}
    for domain in ('tls', 'lqlequiv', 'pyrcel'):
        for corpus in ('pilot', 'qualifiers'):
            path = reserve/domain/(corpus+'.jsonl')
            if path.exists():
                for line in path.read_text(encoding='utf-8').splitlines():
                    if line.strip():
                        case=json.loads(line); cases[case['id']]=case
    rows=[]; skipped=[]
    for path in sorted((reserve/'runs/e1').rglob('*.json')):
        answer=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(answer, dict) or answer.get('case_id') not in cases:
            skipped.append(str(path.relative_to(reserve))); continue
        case=cases[answer['case_id']]
        row=score(case,answer,default_values(case['domain']))
        row['answer_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        row['answer_path']=str(path.relative_to(reserve))
        rows.append(row)
    if rows:
        with (output/'scores-v2.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    report={'version':VERSION,'responses_scored':len(rows),'unscored_scope':sum(r['scope_unscored'] for r in rows),
            'format_invalid':sum(not r['format_valid'] for r in rows),'duplicates':sum(bool(r['duplicate_fields']) for r in rows),
            'valid_screen':sum(r['scientific_interpretation_valid']==1 for r in rows),
            'unique_first_turns':len({r['first_turn_sha256'] for r in rows}),
            'skipped_files':skipped,'scope':'First-turn interpretation screen; no autonomous execution or full source-truth verification',
            'frozen_reference_root': str(reference_root),
            'source_sha256': {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in [Path(__file__), Path(legacy.__file__), *[legacy.REPO/'descriptors'/d/'descriptor.yaml' for d in ('tls','lqlequiv','pyrcel')]]}}
    (output/'summary-v2.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
