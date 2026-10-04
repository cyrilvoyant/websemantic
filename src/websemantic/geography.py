"""Source retrieval and proposed geographical context; never field calibration."""

import json
import re
import unicodedata
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from math import isfinite

from websemantic.conversation import validate_questions
from websemantic.core.validation import Parameter
from websemantic.gemini import GeminiError, api_key


def location(request, descriptor):
    places = descriptor.get('geography', {}).get('places', {})
    text = ''.join(c for c in unicodedata.normalize('NFD', request.lower()) if not unicodedata.combining(c))
    found = [name for name in places if re.search(r'\b' + re.escape(name) + r'\b', text)]
    if len(found) > 1:
        raise ValueError('Précisez un seul lieu pour ce scénario ; les contextes ne seront pas fusionnés.')
    return found[0] if found else None


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def fetch_source(item):
    topic, url = item
    record = {'topic': topic, 'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat()}
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'WebSemantic-research/0.1'})
        with urllib.request.urlopen(request, timeout=12) as response:
            content_type = response.headers.get_content_type()
            if content_type not in ('text/html', 'text/plain', 'application/json', 'application/xhtml+xml'):
                raise ValueError
            body = response.read(350000).decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
            record['url'] = response.url
        if topic == 'geography':
            facts = json.loads(body)
            record['facts'] = facts
            body = json.dumps(facts, ensure_ascii=False)
        else:
            parser = PageText()
            parser.feed(body)
            body = re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()
        if len(body) < 40:
            raise ValueError
        record.update(status='consulted', text=body[:18000])
    except (OSError, ValueError):
        record.update(status='unavailable', text='')
    return record


def research(place, model, descriptor):
    config = descriptor['geography']
    entry = config['places'][place]
    city = entry['city']
    items = entry['sources']
    with ThreadPoolExecutor(max_workers=4) as pool:
        sources = list(pool.map(fetch_source, items))
    usable = [source for source in sources if source['status'] == 'consulted']
    if not usable:
        raise GeminiError('Sources géographiques inaccessibles. Aucun profil de ville ajouté ; réessayez ou fournissez vos hypothèses.')
    schema = {'type': 'object', 'properties': {
        'summary': {'type': 'string'},
        'topics': {'type': 'array', 'items': {'type': 'object', 'properties': {
            'topic': {'type': 'string', 'enum': config['topics']},
            'explanation': {'type': 'string'},
        }, 'required': ['topic', 'explanation']}},
        'proposals': {'type': 'array', 'items': {'type': 'object', 'properties': {
            'field': {'type': 'string', 'enum': config['fields']},
            'value': {'type': 'string'}, 'rationale': {'type': 'string'},
            'sources': {'type': 'array', 'items': {'type': 'integer'}},
        }, 'required': ['field', 'value', 'rationale', 'sources']}},
    }, 'required': ['summary', 'topics', 'proposals']}
    fields = [f'{group}.{name}' for group in ('inputs', 'experiment') for name in descriptor[group]]
    schema['properties']['questions'] = {'type': 'array', 'items': {'type': 'object', 'properties': {
        'question': {'type': 'string'}, 'fields': {'type': 'array', 'items': {'type': 'string', 'enum': fields}},
        'blocking': {'type': 'boolean'}}, 'required': ['question', 'fields', 'blocking']}}
    schema['required'].append('questions')
    prompt = (
        config['guidance'].replace('{city}', city)
        + '\nPARAMETRES ET UNITES:\n' + json.dumps({name: descriptor['inputs'][name] for name in config['fields']}, ensure_ascii=False)
        + '\nSOURCES:\n' + json.dumps([{'index': i, **source} for i, source in enumerate(sources)], ensure_ascii=False)
    )
    payload = {'model': model, 'input': prompt, 'response_format': {'type': 'text', 'mime_type': 'application/json', 'schema': schema}}
    req = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/interactions',
                                 data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key()})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = json.load(response)
        text = raw.get('output_text') or ''.join(item.get('text', '') for item in raw.get('outputs', []) if item.get('type') == 'text')
        if not text:
            text = ''.join(item.get('text', '') for step in raw.get('steps', []) if step.get('type') == 'model_output' for item in step.get('content', []) if item.get('type') == 'text')
        report = json.loads(text)
        if not isinstance(report, dict):
            raise TypeError
    except urllib.error.HTTPError as exc:
        raise GeminiError(f'Analyse géographique Gemini HTTP {exc.code}. Aucun profil ajouté.') from None
    except (OSError, ValueError, TypeError):
        raise GeminiError('Analyse géographique indisponible ou non conforme. Aucun profil ajouté.') from None
    # Preserve citations/status/date, not entire copyrighted retrieved pages.
    report['sources'] = [{key: value for key, value in source.items() if key != 'text'} for source in sources]
    report['city'] = city
    report['method'] = 'Direct retrieval of selected public sources, then Gemini analysis; not unrestricted web search or live tunnel measurements.'
    return report


def apply_report(session, request, report):
    """Validate all proposals before mutation. Explicit user values take precedence."""
    config = session.descriptor['geography']
    questions = validate_questions(report.get('questions', []), session.descriptor)
    updates = {}
    sources = report['sources']
    if {topic['topic'] for topic in report['topics']} != set(config['topics']) or not isinstance(report['summary'], str):
        raise ValueError('Synthèse géographique incomplète ; aucun profil ajouté.')
    for proposal in report['proposals']:
        name = proposal['field']
        if name not in config['fields'] or name in updates:
            raise ValueError('Proposition géographique inconnue ou dupliquée ; aucun profil ajouté.')
        indices = proposal['sources']
        if not indices or any(type(i) is not int or i < 0 or i >= len(sources) or sources[i]['status'] != 'consulted' for i in indices):
            raise ValueError('Source géographique absente ou non consultée ; aucun profil ajouté.')
        value = proposal['value']
        if session.descriptor['inputs'][name]['type'] == 'category':
            if value not in session.descriptor['inputs'][name]['values']:
                raise ValueError('Catégorie contextuelle non reconnue.')
        else:
            spec = session.descriptor['inputs'][name]
            if spec['type'] == 'int':
                value = int(value)
            elif spec['type'] == 'float':
                value = float(value.replace(',', '.'))
            else:
                raise ValueError('Type de proposition contextuelle non pris en charge.')
            bounds = {**spec.get('bounds', {}), **config.get('constraints', {}).get(name, {})}
            if not isfinite(value) or any(
                (value < bounds['min'] if key == 'min' else value <= bounds['min_exclusive'] if key == 'min_exclusive'
                 else value > bounds['max'] if key == 'max' else value >= bounds['max_exclusive'])
                for key in bounds if key in ('min', 'min_exclusive', 'max', 'max_exclusive')
            ):
                raise ValueError('Valeur géographique invalide ; aucun profil ajouté.')
        justification = proposal['rationale']
        if not isinstance(justification, str) or not justification.strip():
            raise ValueError('Hypothèse géographique sans justification.')
        source = f"{report['city']} — hypothèse non calibrée. {justification} " + ' ; '.join(sources[i]['url'] + ' (consulté ' + sources[i]['retrieved_at'] + ')' for i in indices)
        updates[name] = Parameter(value, session.descriptor['inputs'][name].get('unit'), 'assumption', source=source)
    if set(updates) != set(config['fields']):
        raise ValueError('Profil géographique incomplet ; aucun profil ajouté.')
    session.propose_profile()
    for name, parameter in updates.items():
        current = session.scenario.inputs.get(name)
        if current is None or current.origin != 'provided':
            session.scenario.inputs[name] = parameter
    session.geographic_context = report
    session.geographic_pending = False
    session.pending_clarification = None
    session.add_questions(questions)
    session.history.append({'user': request, 'assistant': report['summary'], 'geographic_context': report})


def show_report(session):
    from websemantic.semantics import describe

    report = session.geographic_context
    print(session.descriptor.get('presentation', {}).get('short_name', 'WebSemantic') + ' >', report['summary'])
    for source in report['sources']:
        facts = source.get('facts', {})
        if facts.get('population') is not None:
            print(f"{report['city']} : {facts['population']} habitants (API géographique publique ; millésime non fourni dans cette réponse).")
    print(f"{'Contexte':12} | Explication")
    for topic in report['topics']:
        print(f"{topic['topic']:12} | {topic['explanation']}")
    print(f"{'Hypothèse':28} | {'Valeur':12} | {'Unité':18} | État")
    for name in session.descriptor['geography']['display_fields']:
        record = session.scenario.inputs[name]
        label, unit, _ = describe(name, session.descriptor)
        status = 'fourni' if record.origin == 'provided' else ('validé' if record.accepted else 'à valider')
        print(f'{label:28} | {record.value!s:12} | {unit:18} | {status}')
    for note in session.descriptor['geography'].get('notes', []):
        print(note)
    for i, source in enumerate(report['sources']):
        status = 'consulté' if source['status'] == 'consulted' else 'inaccessible'
        print(f"[{i}] {source['url']} — {status}, {source['retrieved_at'][:10]}")
    for question in session.questions:
        print('Pour préciser :', question['question'])
