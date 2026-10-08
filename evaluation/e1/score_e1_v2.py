"""Versioned first-turn scientific interpretation screen. Never credits execution.

Canonical units or declared aliases are required; a limited set of evidence-backed
conversions is checked explicitly. Unsupported reference scopes remain unscored. Original
scores and running collectors are unchanged. CLI: reserve-path output-directory.
"""
import argparse
import csv
import hashlib
import json
import math
import re
from functools import lru_cache
from pathlib import Path

import score_e1 as legacy
import yaml

VERSION = '2.2-scientific-first-turn'

field_units = lru_cache(maxsize=3)(legacy.field_units)
default_values = lru_cache(maxsize=3)(legacy.defaults)


@lru_cache(maxsize=3)
def accepted_units(domain):
    descriptor = yaml.safe_load((legacy.REPO/'descriptors'/domain/'descriptor.yaml').read_text(encoding='utf-8'))
    return {legacy.norm(name): [spec.get('unit'), *spec.get('unit_aliases', [])]
            for group in ('inputs', 'experiment') for name, spec in descriptor.get(group, {}).items()}


@lru_cache(maxsize=3)
def field_specs(domain):
    descriptor = yaml.safe_load((legacy.REPO/'descriptors'/domain/'descriptor.yaml').read_text(encoding='utf-8'))
    return {legacy.norm(name): spec for group in ('inputs', 'experiment')
            for name, spec in descriptor.get(group, {}).items()}


def evidence_value(value, evidence, unit, field):
    if legacy.value_in_evidence(value, evidence, unit, field):
        return True
    text, numbers = legacy.quoted_numbers(evidence)
    conversions = {'unit:M': [(1609.344, r'\bmiles?\b'), (0.3048, r'\bfeet\b|\bfoot\b|\bpieds?\b|\bft\b')],
                   'unit:PA': [(100, r'\bmbar\b|millibars?')],
                   'unit:M-PER-SEC': [(0.01, r'\bcm\s*/\s*s\b')]}
    if type(value) not in (int, float) or not math.isfinite(value):
        return False
    for factor, token in conversions.get(unit, []):
        if re.search(token, text) and any(legacy.same(value, number * factor) for number in numbers):
            return True
    if field == 'mu' and re.search(r'diam[eè]tre|diameter', text):
        return any(legacy.same(value, number / 2) for number in numbers) and bool(re.search(r'µm|μm|um|microm', text))
    return False


def comparison_score(case, parsed):
    expected = case.get('expected_comparison')
    if not expected:
        return '', 0
    records = parsed.get('comparisons', []) if isinstance(parsed, dict) else []
    if not isinstance(records, list):
        return 0, len(expected)
    targets = [r.get('target') for r in records if isinstance(r, dict)]
    if len(targets) != len(records) or any(not isinstance(t, str) for t in targets) or len(targets) != len(set(targets)):
        return 0, len(expected)
    supplied = {r.get('target'): r for r in records if isinstance(r, dict)}
    matched = 0
    for target, gold in expected.items():
        record = supplied.get(target, {})
        verdict = str(record.get('verdict', '')).lower()
        wanted = gold['verdict']
        if wanted == 'trade-off':
            matched += verdict in ('tradeoff', 'trade-off', 'compromis')
        elif wanted.startswith('not decidable'):
            matched += verdict in ('indeterminate', 'not decidable', 'indéterminé')
        elif wanted.endswith(' dominates'):
            winner = wanted.removesuffix(' dominates')
            labels = list(gold['tcp_ntcp_percent'])
            if 'left' in record or 'right' in record:
                labels = [record.get('left'), record.get('right')]
            matched += record.get('dominant_schedule') == winner or (len(labels) == 2 and winner in labels and
                         verdict == ('left_dominates' if labels[0] == winner else 'right_dominates'))
    return int(matched == len(expected) and set(supplied) == set(expected)), len(expected)


def score(case, answer, defaults):
    units = field_units(case['domain'])
    aliases = accepted_units(case['domain'])
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
    # Correct exact conversions in the versioned screen without changing the legacy scorer.
    unsupported = row['unsupported']
    for name, record in supplied.items():
        evidence = str(record.get('evidence') or '').strip().lower()
        value = record['value']
        if (str(record.get('origin', '')).lower() in ('provided', 'converted') and name not in legacy.OPERATIONAL
                and evidence and evidence in case['turns'][0].lower() and type(value) in (int, float)
                and not legacy.value_in_evidence(value, evidence, units.get(name), name)
                and evidence_value(value, evidence, units.get(name), name)):
            unsupported -= 1
    row['unsupported'] = max(0, unsupported)
    row['hallucination'] = int(row['unsupported'] + row['silent_default'] + row['silent_qualifier_acceptance'] > 0)
    expected = legacy.expected(case)
    unit_canonical = sum(name in supplied and supplied[name].get('unit') == units.get(name) for name in expected)
    unit_correct = sum(name in supplied and supplied[name].get('unit') in aliases.get(name, []) for name in expected)
    joint = sum(name in supplied and legacy.same(supplied[name]['value'], value)
                and supplied[name].get('unit') in aliases.get(name, []) for name, value in expected.items())
    wrong_types = sum(isinstance(value, (int, float)) and not isinstance(value, bool)
                      and name in supplied and (not isinstance(supplied[name]['value'], (int, float))
                                              or isinstance(supplied[name]['value'], bool))
                      for name, value in expected.items())
    specs = field_specs(case['domain'])
    type_or_bound_errors = 0
    unknown_fields = sum(name not in specs and name not in legacy.LABELS and name not in legacy.OPERATIONAL for name in supplied)
    for name, record in supplied.items():
        spec = specs.get(name)
        if spec is None:
            continue
        value = record['value']; kind = spec.get('type')
        typed = ((kind == 'int' and type(value) is int) or (kind == 'float' and type(value) in (int, float))
                 or (kind in ('category', 'date') and isinstance(value, str)))
        if not typed or (type(value) in (int, float) and not math.isfinite(value)):
            type_or_bound_errors += 1
            continue
        if kind == 'category' and value not in spec.get('values', []):
            type_or_bound_errors += 1
        if type(value) in (int, float):
            bounds = spec.get('bounds', {})
            type_or_bound_errors += int(any((key == 'min' and value < limit) or (key == 'max' and value > limit)
                or (key == 'min_exclusive' and value <= limit) or (key == 'max_exclusive' and value >= limit)
                for key, limit in bounds.items() if key in ('min', 'max', 'min_exclusive', 'max_exclusive')))
    scoped = row['decision_ok'] != '' and not (row['decision'] == 'execute' and not expected)
    success = ''
    if scoped:
        success = int(valid and not duplicates and row['decision_ok'] == 1 and not row['hallucination']
                      and not type_or_bound_errors and not unknown_fields)
        if row['decision'] == 'execute':
            success = int(success and joint == len(expected) and not wrong_types)
        if case.get('family') == 'qualifier':
            success = int(success and row['qualifier_convention_ok'] == 1)
    request = case['turns'][0]
    identity = hashlib.sha256((case['domain'] + '\n' + request.strip()).encode()).hexdigest()
    comparison_valid, comparison_targets = comparison_score(case, parsed)
    return row | {'scorer_version': VERSION, 'format_valid': int(valid), 'duplicate_fields': duplicates,
                  'unit_correct': unit_correct, 'unit_canonical_exact': unit_canonical,
                  'value_unit_correct': joint, 'wrong_numeric_types': wrong_types,
                  'scientific_interpretation_valid': success, 'scope_unscored': int(not scoped),
                  'type_or_bound_errors': type_or_bound_errors, 'unknown_fields': unknown_fields,
                  'comparison_verdict_valid': comparison_valid, 'comparison_targets_expected': comparison_targets,
                  'first_turn_sha256': identity, 'execution_verified': 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('reserve', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--reference-root', type=Path)
    parser.add_argument('--folders', nargs='+')
    args = parser.parse_args()
    reserve, output = args.reserve, args.output
    reference_root = args.reference_root or next((p for p in [reserve.parent/'semantic-sim-layer', reserve.parent/'source']
                           if (p/'descriptors').is_dir()), None)
    if reference_root is None:
        raise ValueError('Frozen descriptor directory missing beside the reserve; do not score against mutable sources')
    legacy.REPO = reference_root
    field_units.cache_clear()
    default_values.cache_clear()
    accepted_units.cache_clear()
    field_specs.cache_clear()
    output.mkdir(parents=True, exist_ok=True)
    legacy.RESERVE = reserve
    cases = {}
    for domain in ('tls', 'lqlequiv', 'pyrcel'):
        for corpus in ('pilot', 'qualifiers', 'extension'):
            path = reserve/domain/(corpus+'.jsonl')
            if path.exists():
                for line in path.read_text(encoding='utf-8').splitlines():
                    if line.strip():
                        case=json.loads(line); cases[case['id']]=case
    rows=[]; skipped=[]
    paths = [p for folder in args.folders for p in (reserve/'runs/e1'/folder).rglob('*.json')] if args.folders else list((reserve/'runs/e1').rglob('*.json'))
    for path in sorted(paths):
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
