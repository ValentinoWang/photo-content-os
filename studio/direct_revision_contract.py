"""Additive R277 request and projection contracts."""

LINE = {'type': 'object', 'required': ['text'], 'additionalProperties': False,
        'properties': {'text': {'type': 'string', 'minLength': 1, 'maxLength': 200},
                       'boxId': {'type': 'string'}, 'action': {'enum': ['main', 'dim', 'del', 'short']},
                       'issue': {'enum': ['space', 'color', 'sync']}, 'own': {'const': True}},
        'oneOf': [{'required': ['boxId', 'action']}, {'required': ['issue']}, {'required': ['own']}]}
REQUEST = {'type': 'object', 'required': ['lines'], 'properties': {
    'lines': {'type': 'array', 'minItems': 1, 'maxItems': 200, 'items': LINE}},
    'description': 'Each line is nonblank. Combined text length is 1–200 Unicode characters. boxId must identify a current visible box.'}
VERIFY = {'type': ['object', 'null'], 'required': ['status', 'items'], 'properties': {
    'status': {'enum': ['running', 'done', 'failed']}, 'failureCode': {'const': 'verify_failed'},
    'items': {'type': 'array', 'items': {'type': 'object', 'required': ['index', 'result', 'reason'], 'properties': {
        'index': {'type': 'integer', 'minimum': 0}, 'result': {'enum': ['done', 'missed']}, 'reason': {'type': 'string'}}}}}}
LOOK = {'type': 'object', 'required': ['status', 'failureCode', 'findings'], 'properties': {
    'status': {'enum': ['none', 'running', 'done', 'failed']}, 'failureCode': {'enum': [None, 'look_failed']},
    'findings': {'type': 'array', 'maxItems': 5, 'items': {'type': 'object', 'required': ['boxId', 'kind', 'text', 'suggest'],
        'properties': {'boxId': {'type': ['string', 'null']}, 'kind': {'type': 'string'}, 'text': {'type': 'string'},
                       'suggest': {'enum': ['main', 'dim', 'del', 'short']}}}}}}
SHOT_PROPERTIES = {
    'currentVersion': {'type': 'integer', 'minimum': 0, 'description': 'Zero before the first written version. A version whose rendering failed retains its code without a poster.'},
    'versions': {'type': 'array', 'items': {'type': 'object', 'required': ['version', 'baseVersion', 'createdAt', 'posterRevision', 'codeChars', 'request', 'verify'],
        'properties': {'version': {'type': 'integer', 'minimum': 1}, 'createdAt': {'type': 'string'},
                       'baseVersion': {'type': ['integer', 'null'], 'minimum': 1,
                                       'description': 'Current version before revision or narration rerender. Null for the first version or unavailable pre-field provenance.'},
                       'posterRevision': {'type': 'integer'}, 'codeChars': {'type': 'integer'},
                       'request': {'anyOf': [REQUEST, {'type': 'null'}]}, 'verify': VERIFY}}},
    'boxes': {'type': 'array', 'items': {'type': 'object', 'required': ['id', 'name', 'x', 'y', 'w', 'h'],
        'properties': {'id': {'type': 'string'}, 'name': {'type': 'string'},
                       **{key: {'type': 'number'} for key in ('x', 'y', 'w', 'h')}}}},
    'look': LOOK, 'sample': {'type': 'boolean'},
}


def routes():
    base = '/api/projects/{projectId}/direct/jobs/{jobId}/shots/{shotId}/'
    specs = []
    for method, suffix, operation in [('POST', 'revise', 'reviseDirectShot'), ('POST', 'current', 'selectDirectShotVersion'),
                                      ('POST', 'look', 'lookDirectShot'), ('PUT', 'sample', 'saveDirectSample'),
                                      ('DELETE', 'sample', 'removeDirectSample')]:
        specs.append(dict(method=method, path=base + suffix, operation_id=operation, summary=operation, write=True))
    for path, operation in [('revision-log', 'getDirectRevisionLog'), ('samples', 'getDirectSamples')]:
        specs.append(dict(method='GET', path='/api/direct/' + path, operation_id=operation, summary=operation))
    for action in ('adopt', 'reject'):
        operation = action + 'DirectRuleProposal'
        specs.append(dict(method='POST', path='/api/direct/rules/proposals/{proposalId}/' + action,
                          operation_id=operation, summary=operation, write=True))
    return tuple(specs)


def operation_contract(operation, spec):
    name = spec['operation_id']
    if name == 'reviseDirectShot':
        operation['requestBody']['content']['application/json']['schema'] = REQUEST
    elif name == 'selectDirectShotVersion':
        operation['requestBody']['content']['application/json']['schema'] = {
            'type': 'object', 'required': ['version'], 'properties': {'version': {'type': 'integer', 'minimum': 1}}}
    elif name in {'lookDirectShot', 'saveDirectSample', 'removeDirectSample', 'adoptDirectRuleProposal', 'rejectDirectRuleProposal'}:
        operation['requestBody']['required'] = False
    if name in {'getDirectPoster', 'getDirectShotCode'}:
        operation.setdefault('parameters', []).append({'name': 'version', 'in': 'query', 'required': False,
            'schema': {'type': 'integer', 'minimum': 1}, 'description': 'Read a retained version, independent of the current selection.'})
    if name == 'getDirectSamples':
        operation['parameters'] = [{'name': 'poster', 'in': 'query', 'required': False, 'schema': {'type': 'string'},
                                    'description': 'Sample ID. When present returns the copied image/jpeg instead of the list.'}]
        operation['responses']['200']['content']['image/jpeg'] = {'schema': {'type': 'string', 'format': 'binary'}}
    if str(spec['path']).startswith('/api/direct/'):
        key = 'categories' if name == 'getDirectRevisionLog' else 'samples' if name == 'getDirectSamples' else 'proposal'
        properties = {key: {'type': 'object' if key == 'proposal' else 'array'}}
        if key == 'categories':
            properties['rulesRevision'] = {'type': 'integer'}
        operation['responses']['200']['content']['application/json']['schema'] = {
            'type': 'object', 'required': ['ok', *properties], 'properties': {'ok': {'const': True}, **properties}}
        operation['responses']['403'] = {'description': 'Same-origin or CSRF check failed'}
        operation['responses']['404'] = {'description': 'Sample or proposal not found'}
        operation['responses']['409'] = {'description': 'Proposal is not pending'}
