"""Style selection, persisted draft and low-resolution shot clip contracts."""

COLUMN_FIELDS = ('visual', 'subtitle', 'camera', 'audio')
SHORT_FIELDS = {
    'motionSummary': {'type': ['string', 'null'], 'maxLength': 30},
    'bannedShort': {'type': ['array', 'null'], 'minItems': 1, 'maxItems': 8,
                    'items': {'type': 'string', 'minLength': 1, 'maxLength': 12}},
    'source': {'oneOf': [
        {'type': 'null'},
        {'type': 'object', 'required': ['kind', 'id', 'name', 'instruction'], 'additionalProperties': False,
         'properties': {'kind': {'const': 'library'},
                        **{key: {'type': 'string'} for key in ('id', 'name', 'instruction')}}},
        {'type': 'object', 'required': ['kind', 'projectId', 'title', 'instruction'],
         'oneOf': [{'required': ['jobId']}, {'required': ['draftId']}],
         'properties': {'kind': {'enum': ['inherited', 'adjusted', 'drafted']},
                        **{key: {'type': 'string'} for key in ('projectId', 'jobId', 'draftId', 'title', 'instruction')}}}]},
}
SHOT_INPUT = {'type': 'object', 'required': ['shotId', 'dialogue'], 'properties': {
    'shotId': {'type': 'string', 'pattern': '^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$'},
    'dialogue': {'type': 'string', 'minLength': 1, 'maxLength': 2000},
    **{key: {'type': 'string', 'maxLength': 2000, 'description': 'Trimmed; blank means absent.'} for key in COLUMN_FIELDS}}}
STYLE_BASE = {'oneOf': [
    {'type': 'object', 'required': ['kind', 'projectId', ident], 'additionalProperties': False,
     'properties': {'kind': {'const': kind}, 'projectId': {'type': 'string'}, ident: {'type': 'string'}}}
    for kind, ident in [('job', 'jobId'), ('draft', 'draftId')]] + [
        {'type': 'object', 'required': ['kind', 'id'], 'additionalProperties': False,
         'properties': {'kind': {'const': 'library'}, 'id': {'type': 'string'}}}]}


def routes():
    base = '/api/projects/{projectId}/direct/style-drafts'
    return (
        dict(method='GET', path='/api/direct/styles', operation_id='getDirectStyles', summary='List distinct completed designs across projects'),
        dict(method='GET', path='/api/direct/styles/library/{id}/poster.jpg', operation_id='getDirectLibraryPoster',
             summary='Read a library style poster', response_media='image/jpeg', byte_ranges=True),
        dict(method='GET', path='/api/direct/styles/library/{id}/clip.mp4', operation_id='getDirectLibraryClip',
             summary='Read a library style clip', response_media='video/mp4', byte_ranges=True),
        dict(method='POST', path=base, operation_id='createDirectStyleDraft', summary='Generate a persisted style sample', write=True),
        dict(method='GET', path=base + '/{draftId}', operation_id='getDirectStyleDraft', summary='Read a style sample'),
        dict(method='POST', path=base + '/{draftId}/revise', operation_id='reviseDirectStyleDraft', summary='Revise a style sample', write=True),
        dict(method='GET', path=base + '/{draftId}/poster.jpg', operation_id='getDirectStyleDraftPoster', summary='Read the sample keyframe', response_media='image/jpeg'),
        dict(method='GET', path=base + '/{draftId}/clip.mp4', operation_id='getDirectStyleDraftClip', summary='Read the sample clip', response_media='video/mp4', byte_ranges=True),
        dict(method='GET', path='/api/projects/{projectId}/direct/jobs/{jobId}/shots/{shotId}/clip.mp4',
             operation_id='getDirectShotClip', summary='Read the current shot clip', response_media='video/mp4', byte_ranges=True),
    )


def draft_schema(job):
    shot = job['properties']['shots']['items']['properties']
    properties = {
        'draftId': {'type': 'string'}, 'status': {'enum': ['designing', 'writing', 'ready', 'failed']},
        'text': {'type': 'string'}, 'dialogue': {'type': 'string'},
        'shot': {'type': 'object', 'required': ['shotId', 'dialogue', *COLUMN_FIELDS], 'properties': {
            key: shot[key] for key in ('shotId', 'dialogue', *COLUMN_FIELDS)}},
        'design': job['properties']['design'],
        'sample': {'type': 'object', 'required': ['posterRevision', 'codeChars', 'checks'], 'properties': {
            key: shot[key] for key in ('posterRevision', 'codeChars', 'checks')}},
        'failureCode': {'type': ['string', 'null']}, 'startedAt': {'type': 'string'},
        'revisions': {'type': 'array', 'items': {'type': 'object', 'required': ['instruction', 'at'], 'properties': {
            'instruction': {'type': 'string', 'minLength': 1, 'maxLength': 1000}, 'at': {'type': 'string'}}}},
    }
    return {'type': 'object', 'required': list(properties), 'properties': properties, 'additionalProperties': False}


def operation_contract(operation, spec):
    name = spec['operation_id']
    if name == 'createDirectJob':
        schema = operation['requestBody']['content']['application/json']['schema']
        schema['properties']['styleBase'] = STYLE_BASE
        schema['properties']['storyboard']['properties']['shots']['items'] = SHOT_INPUT
        schema['anyOf'] = [{'required': ['styleBase']}, {'required': ['style'], 'properties': {'style': {'pattern': r'\S'}}}]
        operation['description'] = 'Without styleBase a nonblank style is required (style_required). styleBase accepts job, draft or library sources. Missing sources: 404 style_base_not_found; unready drafts: 409 draft_not_ready. Unchanged sources skip design generation. Library shots and revisions receive the recipe visual grammar and sample code.'
    if name in ('createDirectStyleDraft', 'getDirectStyleDraft', 'reviseDirectStyleDraft'):
        response = operation['responses']['200']
        response['content']['application/json']['schema'] = {
            'type': 'object', 'required': ['ok', 'draft'], 'properties': {
                'ok': {'const': True}, 'draft': {'$ref': '#/components/schemas/DirectStyleDraft'}}}
        if name != 'getDirectStyleDraft':
            operation['responses']['202'] = operation['responses'].pop('200')
            schema = ({'type': 'object', 'required': ['text', 'shot'], 'properties': {
                'text': {'type': 'string', 'minLength': 1, 'maxLength': 4000}, 'shot': SHOT_INPUT}}
                if name == 'createDirectStyleDraft' else
                {'type': 'object', 'required': ['instruction'], 'properties': {
                    'instruction': {'type': 'string', 'minLength': 1, 'maxLength': 1000}}})
            operation['requestBody']['content']['application/json']['schema'] = schema
            operation['description'] = 'Loopback, same-origin and CSRF protected. Trimmed text must be nonblank. Busy drafts return 409 draft_busy.'
    if name == 'getDirectStyles':
        from studio.api_contract import _direct_job_schema
        properties = {'projectId': {'type': 'string'}, 'jobId': {'type': 'string'}, 'title': {'type': 'string'},
                      'createdAt': {'type': 'string'}, 'posterUrl': {'type': ['string', 'null']},
                      'design': {'type': 'object', 'required': ['palette', 'typeScale', 'motionRules', 'banned', 'motionSummary', 'bannedShort'],
                                 'properties': {k: v for k, v in _direct_job_schema()['properties']['design']['properties'].items() if k not in ('status', 'source')}}}
        library_properties = {'id': {'type': 'string'}, 'name': {'type': 'string'}, 'design': properties['design'],
                              'posterUrl': {'type': 'string'}, 'clipUrl': {'type': 'string'}}
        operation['responses']['200']['content']['application/json']['schema'] = {
            'type': 'object', 'required': ['ok', 'styles', 'library'], 'properties': {'ok': {'const': True},
                'styles': {'type': 'array', 'items': {'type': 'object', 'required': list(properties), 'properties': properties}},
                'library': {'type': 'array', 'items': {'type': 'object', 'required': list(library_properties), 'properties': library_properties}}}}
    if name in ('getDirectLibraryPoster', 'getDirectLibraryClip'):
        operation['responses']['404'] = {'description': 'Unknown or invalid library style: style_base_not_found'}
    if name.startswith(('getDirectStyleDraft', 'createDirectStyleDraft', 'reviseDirectStyleDraft')) or name == 'getDirectShotClip':
        for code, description in [('403', 'Same-origin or CSRF check failed'), ('404', 'Project, draft or current frames not found'), ('409', 'Draft is busy or not ready')]:
            operation['responses'][code] = {'description': description}
    if name in ('getDirectShotClip', 'getDirectStyleDraftPoster', 'getDirectStyleDraftClip'):
        operation.setdefault('parameters', []).append({'name': 'v', 'in': 'query', 'required': False,
            'schema': {'type': 'integer', 'minimum': 0}, 'description': 'Current posterRevision cache key; media always follows the current selection.'})
