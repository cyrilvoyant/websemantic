"""Two independently validated scenarios, controlled experiments and qualified CSVs."""

import json
import re
import uuid
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from websemantic.core.validation import Issue, Parameter, ValidationResult, validate
from websemantic.units import fold

IDS = ('scenario_1', 'scenario_2')


def validation(sessions, descriptor):
    issues = []
    refused = False
    if set(sessions) != set(IDS):
        issues.append(Issue('comparison', 'comparison_count', 'Exactement deux identifiants de scénario sont requis.'))
    for label in IDS:
        if label not in sessions:
            issues.append(Issue(label, 'missing', 'Deux scénarios distincts sont requis.'))
            continue
        result = validate(sessions[label].scenario, descriptor)
        refused = refused or result.decision == 'refuse'
        issues.extend(replace(issue, field=f'{label}.{issue.field}') for issue in result.issues)
        if sessions[label].pending_clarification or sessions[label].geographic_pending:
            issues.append(Issue(label, 'clarification', 'Un choix de ce scénario reste à préciser.'))
    for path in descriptor.get('comparison', {}).get('controlled_fields', []):
        group, name = path.split('.')
        records = [getattr(sessions[label].scenario, group).get(name) for label in IDS if label in sessions]
        if len(records) == 2 and all(record and record.value is not None for record in records) and (records[0].value != records[1].value or records[0].unit != records[1].unit):
            issues.append(Issue(path, 'comparison_control', 'La comparaison exige la même valeur dans les deux scénarios.'))
    return ValidationResult('refuse' if refused else 'clarify' if issues else 'execute', tuple(issues))


def apply(parent, request, parsed):
    from websemantic.session import ClarificationNeeded, Session

    if not parent.descriptor.get('comparison', {}).get('enabled'):
        raise ClarificationNeeded('La comparaison n’est pas disponible pour cet environnement.')
    if parsed.get('task') not in parent.descriptor['tasks']['supported'] + ['unsupported']:
        raise ValueError('Tâche comparative non déclarée.')
    if parsed.get('task') == 'unsupported':
        parent.run_requested = False
        parent.pending_clarification = parsed.get('message', 'Comparaison à préciser.')
        raise ClarificationNeeded(parent.pending_clarification)
    chunks = parsed.get('scenario_updates', [])
    if not isinstance(chunks, list) or len(chunks) > 2:
        raise ClarificationNeeded('Précisez exactement deux scénarios ; aucun changement appliqué.')
    if any(not isinstance(chunk, dict) for chunk in chunks):
        raise ValueError('Mises à jour des scénarios non conformes.')
    if any(chunk.get('scenario') not in IDS for chunk in chunks) or len({chunk['scenario'] for chunk in chunks}) != len(chunks):
        raise ClarificationNeeded('Identifiants de scénario absents, inconnus ou dupliqués.')
    candidates = deepcopy(parent.scenarios) if parent.scenarios else {label: Session(parent.descriptor) for label in IDS}
    task = parent.descriptor['tasks']['supported'][0]
    common = parsed.get('updates', [])
    explicitly_updated = {label: {item['field'] for item in common} for label in IDS}
    from websemantic.conversation import validate_questions

    questions = [(question, question.get('scenario', 'common')) for question in validate_questions(parsed.get('questions', []), parent.descriptor)]
    for chunk in chunks:
        for question in validate_questions(chunk.get('questions', []), parent.descriptor):
            scope = question.get('scenario', chunk['scenario'])
            if scope == 'common':
                scope = chunk['scenario']
            questions.append((question, scope))
    if any(scope not in (*IDS, 'common') for _, scope in questions):
        raise ValueError('Portée d’une question inconnue.')
    for label in IDS:
        child = candidates[label]
        chunk = next((chunk for chunk in chunks if chunk['scenario'] == label), {})
        # Common and specific values must not contradict each other silently.
        specific = chunk.get('updates', [])
        specific_paths = {item['field'] for item in specific}
        explicitly_updated[label].update(specific_paths)
        if specific_paths.intersection(item['field'] for item in common):
            raise ClarificationNeeded('Un même paramètre est commun et spécifique. Précisez son affectation.')
        child.apply(request, {'task': task, 'message': parsed.get('message', ''),
                             'updates': common + specific,
                             'questions': []})
        for question, scope in questions:
            if scope in (label, 'common'):
                child.add_questions([question])
        child.history[-1]['questions'] = [question for question, scope in questions if scope in (label, 'common')]
    transfers = parsed.get('shared_from', [])
    if not isinstance(transfers, list):
        raise TypeError('Partage de valeurs non conforme.')
    transferred = set()
    for transfer in transfers:
        source, target, path = transfer['source'], transfer['target'], transfer['field']
        evidence = transfer['evidence']
        if source not in IDS or target not in IDS or source == target or not evidence or evidence not in request:
            raise ClarificationNeeded('L’égalité entre les deux scénarios doit être explicitement demandée.')
        if not re.search(r'\b(?:meme|identique|egal|same|identical)\b', fold(evidence)) or re.search(r'\b(?:pas|sans|not)\b', fold(evidence)):
            raise ClarificationNeeded('Citez une demande affirmative d’égalité entre les deux scénarios.')
        if (target, path) in transferred:
            raise ClarificationNeeded('Partage dupliqué pour un paramètre.')
        if (source, path) in transferred:
            raise ClarificationNeeded('Une égalité circulaire doit être reformulée avec une seule source.')
        transferred.add((target, path))
        group, name = path.split('.')
        if group not in ('inputs', 'experiment') or name not in parent.descriptor[group]:
            raise ValueError('Paramètre partagé inconnu.')
        record = getattr(candidates[source].scenario, group).get(name)
        if not record or record.value is None:
            raise ClarificationNeeded('La valeur à partager doit d’abord être définie dans le scénario source.')
        current = getattr(candidates[target].scenario, group).get(name)
        if path in explicitly_updated[target] and current and current.origin == 'provided' and (current.value != record.value or current.unit != record.unit):
            raise ClarificationNeeded('Une valeur explicite contredit l’égalité demandée entre les scénarios.')
        inherited = Parameter(record.value, record.unit, 'assumption', evidence,
                              f'Égalité explicitement demandée depuis {source}: {evidence}. '
                              f'Origine source={record.origin}; source={record.source or record.evidence}.',
                              accepted=record.origin == 'provided' or record.accepted)
        getattr(candidates[target].scenario, group)[name] = inherited
        candidates[target].run_requested = True
        candidates[target].questions = [item for item in candidates[target].questions if path not in item['fields']]
        candidates[target].pending_clarification = None
        candidates[target].refresh_questions()
    parent.scenarios = candidates
    parent.run_requested = parent.run_requested or any(child.run_requested for child in candidates.values())
    parent.history.append({'user': request, 'assistant': parsed.get('message', ''),
                           'comparison': True, 'updates': common, 'questions': parsed.get('questions', []),
                           'scenario_updates': chunks, 'shared_from': transfers})
    parent.refresh_comparison()


def run(sessions, descriptor, workspace, output_root):
    import pandas as pd
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import RDF

    from websemantic.registry import execute
    from websemantic.semantics import PROV, WS

    if validation(sessions, descriptor).decision != 'execute':
        raise ValueError('Les deux scénarios doivent être complets, validés et comparables avant tout calcul.')
    root = Path(output_root or Path(workspace) / 'runs')
    target = root / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-comparison-' + uuid.uuid4().hex[:8])
    target.mkdir(parents=True)
    paths, medians, manifests = {}, {}, {}
    try:
        for label in IDS:
            paths[label], medians[label] = execute(sessions[label].scenario, descriptor, workspace, target / label)
            manifests[label] = json.loads((paths[label] / 'manifest.json').read_text(encoding='utf-8'))
        tables = manifests[IDS[0]]['outputs']
        if set(tables) != set(manifests[IDS[1]]['outputs']):
            raise ValueError('Les contrats de sortie des deux scénarios ne correspondent pas.')
        qualification = deepcopy(manifests[IDS[0]]['output_qualification'])
        graph = Graph()
        graph.bind('ws', WS)
        graph.bind('prov', PROV)
        activity = URIRef(target.resolve().as_uri() + '#comparison')
        graph.add((activity, RDF.type, PROV.Activity))
        graph.add((activity, RDF.type, WS.ComparisonActivity))
        graph.add((activity, WS.method, Literal('Separate executions; concatenate tables, no pooled statistics.')))
        for label in IDS:
            # Read through the filesystem: URL loading drops the host on Windows UNC paths.
            source = paths[label] / 'semantics.ttl'
            graph.parse(data=source.read_text(encoding='utf-8'), format='turtle',
                        publicID=source.resolve().as_uri())
        for table in tables:
            frames = []
            for label in IDS:
                metadata = manifests[label]['output_qualification']['tables'][table]
                if metadata['columns'] != manifests[IDS[0]]['output_qualification']['tables'][table]['columns']:
                    raise ValueError('Unités ou définitions incompatibles ; comparaison interrompue.')
                frame = pd.read_csv(paths[label] / (table + '.csv'))
                if 'scenario' in frame:
                    raise ValueError('Une colonne scenario existe déjà dans le backend.')
                frame.insert(0, 'scenario', label)
                frames.append(frame)
            combined = pd.concat(frames, ignore_index=True)
            combined.to_csv(target / (table + '.csv'), index=False)
            info = qualification['tables'][table]
            info['rows'] = len(combined)
            info['columns'] = {'scenario': {'unit': None, 'quantity': 'scenario_identifier',
                'meaning': 'scenario_1 ou scenario_2 ; les réalisations restent distinctes par scénario.'}, **info['columns']}
            info['aggregation'] = 'Concaténation par scénario, sans moyenne entre scénarios. ' + info['aggregation']
            output = URIRef((target / (table + '.csv')).resolve().as_uri())
            graph.add((output, RDF.type, PROV.Entity))
            graph.add((output, RDF.type, WS.SimulationOutput))
            graph.add((output, PROV.wasGeneratedBy, activity))
            for name, column in info['columns'].items():
                entity = URIRef(str(output) + '#column-' + name)
                graph.add((output, WS.hasColumn, entity))
                graph.add((entity, WS.meaning, Literal(column['meaning'], lang='fr')))
                if column.get('quantity'):
                    graph.add((entity, WS.quantity, Literal(column['quantity'])))
                if column.get('unit'):
                    graph.add((entity, WS.unitSymbol, Literal(column['unit'])))
            for label in IDS:
                child = URIRef((paths[label] / (table + '.csv')).resolve().as_uri())
                graph.add((child, RDF.type, PROV.Entity))
                graph.add((child, WS.scenarioIdentifier, Literal(label)))
                for original in list(graph.subjects(PROV.atLocation, child)):
                    graph.add((child, PROV.wasDerivedFrom, original))
                    for native_activity in graph.objects(original, PROV.wasGeneratedBy):
                        graph.add((child, PROV.wasGeneratedBy, native_activity))
                graph.add((activity, PROV.used, child))
                graph.add((output, PROV.wasDerivedFrom, child))
        differences = {}
        for indicator in descriptor['comparison']['indicators']:
            a, b = medians[IDS[0]][indicator], medians[IDS[1]][indicator]
            differences[indicator] = {'scenario_1': a, 'scenario_2': b, 'difference_1_minus_2': a-b,
                                     'relative_percent_vs_2': (100*(a-b)/b) if b else None}
        report = {'comparison': True, 'scenario_medians': medians, 'differences': differences,
                  'method': 'Differences between scenario medians; common seeds do not guarantee identical random draws after configuration changes.'}
        manifest = {'mode': 'comparison', 'status': 'complete', 'software': descriptor['software'],
                    'scenarios': {label: asdict(sessions[label].scenario) for label in IDS},
                    'scenario_runs': {label: str(paths[label].resolve()) for label in IDS},
                    'controlled_fields': descriptor['comparison']['controlled_fields'],
                    'outputs': tables, 'output_qualification': qualification,
                    'comparison': report, 'nature': descriptor['nature']}
        (target / 'comparison.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        graph.serialize(target / 'semantics.ttl', format='turtle')
        (target / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    except Exception:
        (target / 'INCOMPLETE.txt').write_text('Comparaison incomplète ; ne pas interpréter ces fichiers comme un résultat validé.', encoding='utf-8')
        raise
    return target, report
