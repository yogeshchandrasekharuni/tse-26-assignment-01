#!/usr/bin/env python3
"""Validate this specification bundle; optional jsonschema gives deeper syntax QA."""
from pathlib import Path
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ['README_HANDOFF.md','SPEC.md','CODEX_PROMPT.md','AGENTS.md','IMPLEMENTATION_PLAN.md','ARCHITECTURE.md','FAST_AGENT_INTEGRATION.md','MR_CATALOG.md','DATA_CONTRACT.md','EVALUATION_PROTOCOL.md','TEST_ACCEPTANCE.md','REPORT_OUTLINE.md','DECISIONS.md','REPRODUCIBILITY_CONTRACT.md']

def read(name):
    return json.loads((ROOT/name).read_text())

def main():
    for n in REQUIRED:
        assert (ROOT/n).is_file() and (ROOT/n).stat().st_size > 1000, n
    jsons = sorted(ROOT.rglob('*.json'))
    for path in jsons:
        json.loads(path.read_text())
    definitions = read('templates/mr_definitions.json')
    assert [d['id'] for d in definitions] == [f'MR{x:02d}' for x in range(1,11)]
    assert {d['family'] for d in definitions} == {'invariance','monotonic','directional'}
    assert all(d['minimum_distinct_bases'] >= 30 for d in definitions)
    seed = read('templates/seed_manifest.json')
    assert len(seed['seed_pairs']) == 3
    assert len({s['source_seed'] for s in seed['seed_pairs']}) == 3
    assert all(s['source_seed'] == s['followup_seed'] for s in seed['seed_pairs'])
    candidates = read('templates/base_candidates.json')['candidates']
    assert len(candidates) == 30 and len({c['base_id'] for c in candidates}) == 30
    for mr in definitions:
        keys = set()
        for c in candidates:
            q = json.loads(json.dumps(c['request']))
            if mr['id'] == 'MR05':
                q['criteria'].update(price_min_cents=20000000,price_max_cents=45000000)
            if mr['id'] == 'MR08' and int(c['base_id'][1:]) <= 10:
                q['criteria'].update(price_min_cents=20000000,price_max_cents=45000000)
            if mr['id'] == 'MR09':
                q['criteria'].update(price_min_cents=None,price_max_cents=None)
            cr = q['criteria']
            assert cr['bedrooms_min'] <= cr['bedrooms_max']
            assert len(cr['zips']) >= 2 and len(cr['zips']) < 12
            for k in ['seed','display']:
                q.pop(k, None)
            keys.add(json.dumps(q,sort_keys=True,separators=(',',':')))
        assert len(keys) == 30, mr['id']
    for path in ROOT.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text()):
            if '://' in target or target.startswith(('#','mailto:')):
                continue
            target=target.split('#')[0]
            assert (path.parent/target).exists(), (path,target)
    # Delivered originals are readable and preserved.
    hashes=read('sources/originals_sha256.json')
    for path, expected in hashes.items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
    assert (ROOT/'sources/originals/Assignment_MR_Housing_final_v2.pdf').read_bytes().startswith(b'%PDF')
    for name in ['housing_trends_agent_architecture.drawio','housing_trends_agent_architecture_no_fills.drawio']:
        xml = ET.parse(ROOT/'sources/originals'/name)
        assert len(xml.getroot().findall('diagram')) == 3
    rows=list(csv.DictReader((ROOT/'fixtures/low_support.csv').open()))
    assert len(rows)==48 and len({r['month'] for r in rows})==24
    assert len({r['record_id'] for r in rows})==48
    manifest=read('fixtures/low_support_manifest.json')
    assert hashlib.sha256((ROOT/'fixtures/low_support.csv').read_bytes()).hexdigest()==manifest['snapshot_sha256']
    assert read('fixtures/example_output.json')['metadata']['mode']=='policy_simulation'
    for prompt in ['orchestrator','price','supply','region','reviewer','composer']:
        assert (ROOT/f'prompts/{prompt}.md').is_file()
    # Full byte inventory is checked if present (it excludes itself).
    if (ROOT/'MANIFEST.sha256.json').exists():
        for path, expected in read('MANIFEST.sha256.json').items():
            assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        print('NOTE: jsonschema unavailable; JSON syntax/structure/hash checks only. Install it or use a prepared environment for full schema QA.')
    else:
        for path in (ROOT/'schemas').glob('*.json'):
            Draft202012Validator.check_schema(json.loads(path.read_text()))
        def validate(schema_path, value):
            Draft202012Validator(read(schema_path),format_checker=FormatChecker()).validate(value)
        validate('schemas/analysis_request.schema.json',read('fixtures/example_request.json'))
        validate('schemas/analysis_output.schema.json',read('fixtures/example_output.json'))
        validate('schemas/mr_definition.schema.json',definitions)
        for c in candidates:
            validate('schemas/analysis_request.schema.json',c['request'])
        for d in read('fixtures/agent_decisions.json')['decisions']:
            validate('schemas/agent_decision.schema.json',d)
        for r in rows:
            r.update({k:int(r[k]) for k in ['bedrooms','sqft','price_cents']})
            validate('schemas/listing.schema.json',r)
        # Verify strict extra-field rejection actually works.
        bad = dict(read('fixtures/example_request.json'), unknown_field=True)
        assert list(Draft202012Validator(read('schemas/analysis_request.schema.json')).iter_errors(bad))
        print('PASS: Draft2020-12 schemas and all supplied schema examples validated; strict-field rejection checked.')
    print(f'PASS: {len(REQUIRED)} main docs, {len(jsons)} JSON files,10MRs/3families,3paired seeds,30distinct candidate requests per MR, fixtures, local links, originals and inventory hashes. No application evaluated.')

if __name__ == '__main__':
    main()
