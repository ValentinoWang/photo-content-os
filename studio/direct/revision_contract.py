"""Additive R277 request and projection contracts."""

if __package__:
    from ..constants import (
        LINE,
        REQUEST,
        VERIFY,
        LOOK,
        SHOT_PROPERTIES,
    )
else:
    try:
        from studio.constants import (
            LINE,
            REQUEST,
            VERIFY,
            LOOK,
            SHOT_PROPERTIES,
        )
    except ImportError:
        from constants import (
            LINE,
            REQUEST,
            VERIFY,
            LOOK,
            SHOT_PROPERTIES,
        )


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
