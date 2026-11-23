"""Canonical route inventory and OpenAPI contract for the loopback studio service."""

from __future__ import annotations

import re
from typing import Any

from studio.direct_revision_contract import SHOT_PROPERTIES, operation_contract, routes
from studio import direct_style_contract, direct_handoff_contract

ROUGH_CUT_ROUTE_SPECS: tuple[dict[str, object], ...] = (
    {'method': 'GET', 'path': '/api/review/pieces/{id}/roughcut', 'operation_id': 'getRoughcut', 'summary': 'Read the version-bound roughcut plan'},
    {'method': 'POST', 'path': '/api/review/pieces/{id}/roughcut/commands', 'operation_id': 'commandRoughcut', 'summary': 'Accept a CAS-bound roughcut command (202)', 'write': True},
    {'method': 'GET', 'path': '/api/review/roughcut-jobs/{jobId}', 'operation_id': 'getRoughcutJob', 'summary': 'Read an owned roughcut job'},
    {'method': 'POST', 'path': '/api/review/roughcut-jobs/{jobId}', 'operation_id': 'stopRoughcutJob', 'summary': 'Stop only this roughcut job (202)', 'write': True},
    {'method': 'GET', 'path': '/api/review/editing-presets', 'operation_id': 'getEditingPresets', 'summary': 'Read built-in and local editing recipes'},
    {'method': 'POST', 'path': '/api/review/editing-presets', 'operation_id': 'saveEditingPreset', 'summary': 'Save a cross-project recipe with CAS (201)', 'write': True},
    {'method': 'GET', 'path': '/api/review/pieces/{id}/editor-capabilities', 'operation_id': 'getRoughcutEditorCapabilities', 'summary': 'Read R228 choice and roughcut capabilities'},
    {'method': 'POST', 'path': '/api/review/pieces/{id}/roughcut/transcriptions', 'operation_id': 'transcribeRoughcutShots', 'summary': 'Accept selected local transcription work (202)', 'write': True},
    {'method': 'POST', 'path': '/api/review/pieces/{id}/roughcut/drafts', 'operation_id': 'createRoughcutDraft', 'summary': 'Generate the saved editor choice in an owned job (202)', 'write': True},
    {'method': 'POST', 'path': '/api/review/pieces/{id}/roughcut/drafts/open', 'operation_id': 'openRoughcutDraft', 'summary': 'Open only this piece latest current Kdenlive project', 'write': True},
    {'method': 'GET', 'path': '/api/review/pieces/{id}/roughcut/media/{artifactId}', 'operation_id': 'getRoughcutMedia', 'summary': 'Read a bound derived roughcut artifact', 'response_media': 'video/mp4', 'byte_ranges': True},
)


ROUTE_SPECS: tuple[dict[str, object], ...] = routes() + direct_style_contract.routes() + direct_handoff_contract.routes() + ROUGH_CUT_ROUTE_SPECS + (
    {'method': 'GET', 'path': '/api/direct/recipes', 'operation_id': 'getDirectRecipes', 'summary': 'Read promotional shot recipes'},
    {'method': 'GET', 'path': '/api/direct/recipes/{recipeId}/poster.jpg', 'operation_id': 'getRecipePoster', 'summary': 'Read recipe poster', 'response_media': 'image/jpeg'},
    {'method': 'GET', 'path': '/api/direct/recipes/{recipeId}/clip.mp4', 'operation_id': 'getRecipeClip', 'summary': 'Read recipe clip', 'response_media': 'video/mp4', 'byte_ranges': True},
    {'method': 'POST', 'path': '/api/projects/{projectId}/direct/promo-images', 'operation_id': 'uploadPromoImage', 'summary': 'Upload promotional image', 'write': True},
    {'method': 'POST', 'path': '/api/projects/{projectId}/direct/jobs', 'operation_id': 'createDirectJob', 'summary': 'createDirectJob', 'write': True},
    {'method': 'GET', 'path': '/api/projects/{projectId}/direct/jobs/latest', 'operation_id': 'getLatestDirectJob', 'summary': 'getLatestDirectJob'},
    {'method': 'GET', 'path': '/api/projects/{projectId}/direct/jobs/{jobId}', 'operation_id': 'getDirectJob', 'summary': 'getDirectJob'},
    {'method': 'POST', 'path': '/api/projects/{projectId}/direct/jobs/{jobId}/shots/{shotId}/rewrite', 'operation_id': 'rewriteDirectShot', 'summary': 'rewriteDirectShot', 'write': True},
    {'method': 'POST', 'path': '/api/projects/{projectId}/direct/jobs/{jobId}/narration', 'operation_id': 'uploadDirectNarration', 'summary': 'uploadDirectNarration', 'write': True},
    {'method': 'POST', 'path': '/api/projects/{projectId}/direct/jobs/{jobId}/compose', 'operation_id': 'composeDirectVideo', 'summary': 'composeDirectVideo', 'write': True},
    {'method': 'GET', 'path': '/api/projects/{projectId}/direct/jobs/{jobId}/shots/{shotId}/poster.jpg', 'operation_id': 'getDirectPoster', 'summary': 'getDirectPoster', 'response_media': 'image/jpeg'},
    {'method': 'GET', 'path': '/api/projects/{projectId}/direct/jobs/{jobId}/shots/{shotId}/code', 'operation_id': 'getDirectShotCode', 'summary': 'getDirectShotCode', 'response_media': 'text/plain; charset=utf-8'},
    {'method': 'GET', 'path': '/api/projects/{projectId}/direct/jobs/{jobId}/output.mp4', 'operation_id': 'getDirectOutput', 'summary': 'getDirectOutput', 'response_media': 'video/mp4', 'byte_ranges': True},
    {"method": "GET", "path": "/api/review/assets/{assetId}/preview", "operation_id": "getAssetPreview", "summary": "Read a derived asset preview", "response_media": "video/mp4", "byte_ranges": True},
    {'method': 'GET', 'path': '/api/review/catalog', 'operation_id': 'getReviewCatalog', 'summary': 'getReviewCatalog'},
    {'method': 'GET', 'path': '/api/review/pieces/{pieceId}/shots', 'operation_id': 'getReviewShots', 'summary': 'getReviewShots'},
    {'method': 'POST', 'path': '/api/review/pieces/{pieceId}/decisions', 'operation_id': 'saveReviewDecision', 'summary': 'saveReviewDecision', 'write': True},
    {'method': 'POST', 'path': '/api/review/pieces/{pieceId}/jobs', 'operation_id': 'runShotSelection', 'summary': 'runShotSelection', 'write': True},
    {'method': 'GET', 'path': '/api/review/pieces/{pieceId}/media/{kind}/{mediaId}', 'operation_id': 'getReviewMedia', 'summary': 'getReviewMedia', 'response_media': 'video/mp4', 'byte_ranges': True},
    {'method': 'GET', 'path': '/api/review/music', 'operation_id': 'getMusicLibrary', 'summary': 'getMusicLibrary'},
    {'method': 'GET', 'path': '/api/review/music/{trackId}/audio', 'operation_id': 'getMusicAudio', 'summary': 'getMusicAudio', 'response_media': 'audio/mpeg', 'byte_ranges': True},
    {'method': 'GET', 'path': '/api/review/music-settings', 'operation_id': 'getMusicSettings', 'summary': 'getMusicSettings'},
    {'method': 'POST', 'path': '/api/review/music/{trackId}/reanalyze', 'operation_id': 'reanalyzeMusic', 'summary': 'Reanalyze beat or tags', 'write': True},
    {'method': 'POST', 'path': '/api/review/music/import', 'operation_id': 'importMusic', 'summary': 'importMusic', 'write': True},
    {'method': 'GET', 'path': '/api/review/imports/{jobId}', 'operation_id': 'getMusicImport', 'summary': 'getMusicImport'},
    {"method": "GET", "path": "/api/bootstrap", "operation_id": "getBootstrap", "summary": "Read studio bootstrap state"},
    {"method": "GET", "path": "/api/health", "operation_id": "getHealth", "summary": "Read loopback service health"},
    {"method": "GET", "path": "/api/diagnostics", "operation_id": "getDiagnostics", "summary": "Read cached diagnostics or explicitly rerun the local checks", "query_parameters": [{"name": "refresh", "in": "query", "required": False, "schema": {"type": "string", "enum": ["1"]}}]},
    {"method": "GET", "path": "/api/settings", "operation_id": "getSettings", "summary": "Read redacted studio settings"},
    {"method": "GET", "path": "/api/settings/analysis-budget", "operation_id": "getAnalysisBudget", "summary": "Read the effective analysis budget"},
    {"method": "POST", "path": "/api/settings/analysis-budget", "operation_id": "updateAnalysisBudget", "summary": "Update the analysis budget with CAS", "write": True},
    {'method': 'POST', 'path': '/api/projects/delete-preview', 'operation_id': 'previewProjectDeletion', 'summary': 'Check selected work folders only when confirming deletion', 'write': True},
    {'method': 'POST', 'path': '/api/projects/delete', 'operation_id': 'deleteProjects', 'summary': 'Soft-delete each selected work with CAS and optional folder trash', 'write': True},
    {'method': 'GET', 'path': '/api/projects/deleted', 'operation_id': 'listDeletedProjects', 'summary': 'List recent deletions with current recovery reasons'},
    {'method': 'POST', 'path': '/api/projects/restore', 'operation_id': 'restoreProjects', 'summary': 'Restore an undo batch with per-work CAS', 'write': True},
    {'method': 'POST', 'path': '/api/projects/{projectId}/restore', 'operation_id': 'restoreProject', 'summary': 'Restore one deleted work with CAS', 'write': True},
    {'method': 'POST', 'path': '/api/projects/{projectId}/dismiss', 'operation_id': 'dismissDeletedProject', 'summary': 'Dismiss only an unrecoverable deleted work with CAS', 'write': True},
    {"method": "GET", "path": "/api/projects", "operation_id": "listProjects", "summary": "List local projects"},
    {"method": "POST", "path": "/api/projects", "operation_id": "createProject", "summary": "Create a local project", "write": True},
    {"method": "GET", "path": "/api/projects/{projectId}", "operation_id": "getProject", "summary": "Read a project"},
    {"method": "PATCH", "path": "/api/projects/{projectId}", "operation_id": "updateProject", "summary": "Update a project with CAS", "write": True},
    {"method": "POST", "path": "/api/projects/{projectId}/inbox-plan", "operation_id": "previewInboxPlan", "summary": "Preview deterministic inbox batches", "write": True},
    {"method": "POST", "path": "/api/projects/{projectId}/inbox-plan/confirm", "operation_id": "confirmInboxPlan", "summary": "Confirm one plan batch and target project", "write": True},
    {"method": "POST", "path": "/api/projects/{projectId}/video-workflow", "operation_id": "editLocalVideoWorkflow", "summary": "Edit the identity-bound local video workflow", "write": True},
    {"method": "POST", "path": "/api/projects/{projectId}/video-return", "operation_id": "returnLocalVideo", "summary": "Stream an exported video for deterministic checks", "write": True, "binary": True},
    {"method": "GET", "path": "/api/projects/{projectId}/video-preview/{candidateId}", "operation_id": "getLocalVideoPreview", "summary": "Read a checked low-resolution candidate preview", "response_media": "video/mp4", "byte_ranges": True},
    {"method": "GET", "path": "/api/projects/{projectId}/video-subtitles", "operation_id": "downloadVideoSubtitles", "summary": "Download the bound SRT", "response_media": "application/x-subrip"},
    {"method": "GET", "path": "/api/assets", "operation_id": "listAssets", "summary": "Query the structured asset index"},
    {"method": "GET", "path": "/api/assets/statistics", "operation_id": "getAssetStatistics", "summary": "Read dynamic asset facets"},
    {"method": "GET", "path": "/api/assets/{assetId}", "operation_id": "getAsset", "summary": "Read one structured asset"},
    {"method": "POST", "path": "/api/projects/{projectId}/assets", "operation_id": "addProjectAsset", "summary": "Add an indexed asset reference to a project", "write": True},
    {"method": "GET", "path": "/api/setup/state", "operation_id": "getSetupState", "summary": "Read resumable four-step setup state"},
    {"method": "POST", "path": "/api/setup/state", "operation_id": "updateSetupState", "summary": "Persist one setup transition with CAS", "write": True},
    {"method": "GET", "path": "/api/upstream/tasks", "operation_id": "getUpstreamTasks", "summary": "Read optional upstream task projections"},
    {"method": "POST", "path": "/api/projects/{projectId}/media-delete/recommendations", "operation_id": "recommendMediaDeletion", "summary": "Build explainable deletion recommendations", "write": True},
    {"method": "POST", "path": "/api/projects/{projectId}/media-delete/confirm", "operation_id": "confirmMediaDeletion", "summary": "Move selected media to the system recycle bin", "write": True},
    {"method": "POST", "path": "/api/projects/{projectId}/media-delete/restore", "operation_id": "restoreMediaDeletion", "summary": "Restore one recycle-bin receipt", "write": True},
    {"method": "GET", "path": "/api/projects/{projectId}/media-delete/receipts", "operation_id": "listMediaDeletionReceipts", "summary": "Read recycle-bin receipts"},
    {"method": "POST", "path": "/api/projects/{projectId}/documents/{documentName}/{action}", "operation_id": "mutateProjectDocument", "summary": "Patch, lock, unlock, roll back, or AI-patch a project document", "write": True},
    {"method": "GET", "path": "/api/projects/{projectId}/documents/{documentName}/diff", "operation_id": "getProjectDocumentDiff", "summary": "Read a document version diff"},
    {"method": "GET", "path": "/api/projects/{projectId}/edl-bridge", "operation_id": "getEdlBridge", "summary": "Read the structured EDL bridge"},
    {"method": "POST", "path": "/api/projects/{projectId}/workspace", "operation_id": "connectProjectWorkspace", "summary": "Connect a local project workspace", "write": True},
    {"method": "POST", "path": "/api/projects/{projectId}/publishing", "operation_id": "recordPublishing", "summary": "Record publishing and review evidence", "write": True},
    {"method": "POST", "path": "/api/projects/{projectId}/references", "operation_id": "addProjectReference", "summary": "Add a non-editing reference", "write": True},
    {"method": "POST", "path": "/api/settings/model-providers", "operation_id": "saveModelProvider", "summary": "Save a redacted model provider configuration", "write": True},
    {"method": "POST", "path": "/api/settings/model-providers/{providerId}/probe", "operation_id": "probeModelProvider", "summary": "Probe one configured model provider", "write": True},
    {"method": "POST", "path": "/api/settings/archive/lifecycle", "operation_id": "saveArchiveLifecycle", "summary": "Save the two-state archive lifecycle", "write": True},
    {"method": "POST", "path": "/api/settings/archive/locations", "operation_id": "addArchiveLocation", "summary": "Register one physical archive location", "write": True},
    {"method": "POST", "path": "/api/settings/upstream/pair", "operation_id": "pairUpstream", "summary": "Pair the optional upstream identity", "write": True},
    {"method": "POST", "path": "/api/settings/upstream/refresh", "operation_id": "refreshUpstream", "summary": "Refresh the optional upstream identity", "write": True},
    {"method": "POST", "path": "/api/settings/upstream/logout", "operation_id": "logoutUpstream", "summary": "Clear the optional upstream identity", "write": True},
    {"method": "POST", "path": "/api/settings/chatcut/probe", "operation_id": "probeChatCut", "summary": "Probe the local ChatCut MCP", "write": True},
    {"method": "POST", "path": "/api/settings/chatcut/confirm", "operation_id": "confirmChatCut", "summary": "Confirm a detected local ChatCut MCP", "write": True},
)


def route_inventory() -> list[dict[str, str]]:
    """Return the exact path/method registration consumed by server and tests."""

    return [
        {"method": str(spec["method"]), "path": str(spec["path"]), "operation_id": str(spec["operation_id"])}
        for spec in ROUTE_SPECS
    ]


def _route_pattern(spec: dict[str, object]) -> str:
    return re.sub(r"\{[A-Za-z][A-Za-z0-9]*\}", r"[^/]+", str(spec["path"]))


_ROUGHCUT_ROUTE_PATTERNS = tuple(re.compile(_route_pattern(spec)) for spec in ROUGH_CUT_ROUTE_SPECS)


def is_roughcut_route(path: str) -> bool:
    return any(pattern.fullmatch(path) for pattern in _ROUGHCUT_ROUTE_PATTERNS)


def is_registered_route(method: str, path: str) -> bool:
    for spec in ROUTE_SPECS:
        if spec["method"] != method.upper():
            continue
        if re.fullmatch(_route_pattern(spec), path):
            return True
    return False


def _response(description: str = "Successful local response") -> dict[str, Any]:
    return {
        "description": description,
        "content": {"application/json": {"schema": {"type": "object", "required": ["ok"]}}},
    }


def _direct_job_schema() -> dict[str, Any]:
    text = {'type': ['string', 'null']}
    seconds = {'type': ['number', 'null']}
    check_item = {'type': 'object', 'required': ['code', 'message'], 'properties': {
        'code': {'type': 'string'}, 'message': {'type': 'string'}, 'atSeconds': {'type': 'number'}}}
    checks = {'type': 'object', 'required': ['errors', 'warnings'], 'properties': {
        name: {'type': 'array', 'items': check_item} for name in ('errors', 'warnings')}}
    checks['properties']['warnings']['description'] = 'Nonblocking reminders. layout_bottom_gap marks >30% empty space below visible content in y=200..1500, using the rendered keyframe and edge-sampled background; it never triggers automatic rewriting.'
    checks['properties']['warnings']['examples'] = [[{'code': 'layout_bottom_gap', 'message': '画面下半截空着：主画面只占到 y=900，离字幕带还空 46.2%'}]]
    shot = {'shotId': {'type': 'string'}, 'dialogue': {'type': 'string'}, 'mainAction': text,
            'estimatedSeconds': {'type': 'number'}, 'measuredSeconds': seconds,
            'timingSource': {'enum': ['estimate', 'narration', 'proportional']},
            'status': {'enum': ['queued', 'writing', 'written', 'rendering', 'rendered', 'failed', 'interrupted']},
            'failureCode': text, 'attempts': {'type': 'integer', 'minimum': 0}, 'lastInstruction': text,
            'writingStartedAt': {'type': ['string', 'null'], 'format': 'date-time',
                                 'description': 'Latest model-writing start, including retries; retained after writing. Null before first write or when an older job did not record it.'},
            'writtenAt': text, 'renderedAt': text, 'codeChars': {'type': 'integer', 'minimum': 0},
            'posterRevision': {'type': 'integer', 'minimum': 0}, 'checks': checks}
    shot.update(SHOT_PROPERTIES)
    shot.update({key: {'type': ['string', 'null']} for key in direct_style_contract.COLUMN_FIELDS})
    shot['fromDraft'] = {'type': 'boolean'}
    design = {'status': {'enum': ['pending', 'writing', 'done', 'failed']},
              'palette': {'type': ['object', 'null'], 'required': ['background', 'primary', 'accent', 'neutral'],
                          'properties': {k: {'type': 'string', 'pattern': '^#[0-9a-fA-F]{6}$'}
                                         for k in ('background', 'primary', 'accent', 'neutral')}},
              'typeScale': {'type': ['array', 'null'], 'minItems': 3, 'maxItems': 3, 'items': {'type': 'integer'}},
              'motionRules': text, 'banned': {'type': 'array', 'items': {'type': 'string'}}}
    design.update(direct_style_contract.SHORT_FIELDS)
    output = {'status': {'enum': ['none', 'composing', 'ready', 'failed']},
              'composedAt': {'type': ['string', 'null'], 'format': 'date-time',
                             'description': 'Latest successful composition time. Null before composition, during composition, after failure or shot rewrite, or for older jobs without a recorded time. Narration upload preserves it until recomposition.'},
              'kind': {'enum': ['silent', 'narrated']}, 'durationSeconds': seconds,
              'frames': {'type': ['integer', 'null']}, 'revision': {'type': 'integer', 'minimum': 0},
              'checks': {'type': 'object', 'required': ['playable', 'avOffsetSeconds', 'blackFrames'], 'properties': {
                  'playable': {'enum': ['pass', 'fail', 'unknown']}, 'avOffsetSeconds': seconds,
                  'blackFrames': {'enum': ['pass', 'fail', None]}}}}
    properties = {'jobId': {'type': 'string'}, 'projectId': {'type': 'string'},
                  'model': {'const': 'claude-opus-5-5'},
                  'status': {'enum': ['designing', 'writing', 'rendering', 'ready', 'composing', 'done', 'failed']},
                  'createdAt': {'type': 'string'}, 'updatedAt': {'type': 'string'}, 'failureCode': text,
                  'design': {'type': 'object', 'required': list(design), 'properties': design},
                  'shots': {'type': 'array', 'items': {'type': 'object', 'required': list(shot), 'properties': shot}},
                  'narration': {'type': 'object', 'required': ['status', 'durationSeconds'], 'properties': {
                      'status': {'enum': ['none', 'aligning', 'ready', 'invalid']}, 'durationSeconds': seconds}},
                  'output': {'type': 'object', 'required': list(output), 'properties': output}}
    properties['handoff'] = {'anyOf': [direct_handoff_contract.HANDOFF_REF, {'type': 'null'}]}
    properties['handoffNewer'] = {'type': 'boolean'}
    return {'type': 'object', 'required': list(properties), 'properties': properties, 'additionalProperties': False}


def _operation(spec: dict[str, object]) -> dict[str, Any]:
    operation: dict[str, Any] = {
        "operationId": spec["operation_id"],
        "summary": spec["summary"],
        "responses": {"200": _response(), "400": _response("Invalid request")},
    }
    if spec.get('response_media'):
        operation['responses']['200']['content']={str(spec['response_media']):{'schema':{'type':'string','format':'binary'}}}
    if spec.get('query_parameters'):
        operation['parameters'] = spec['query_parameters']
    if spec.get('byte_ranges'):
        operation['parameters'] = [{'name': 'Range', 'in': 'header', 'required': False,
            'description': 'One bytes=start-end, bytes=start- or bytes=-suffix range.', 'schema': {'type': 'string'}}]
        for code, description in [('206', 'Requested preview byte range'), ('416', 'Invalid or unsatisfiable preview byte range')]:
            operation['responses'][code] = {'description': description,
                'headers': {'Content-Range': {'schema': {'type': 'string'}}, 'Accept-Ranges': {'schema': {'type': 'string'}}},
                'content': {str(spec['response_media']): {'schema': {'type': 'string', 'format': 'binary'}}}}
    if spec.get("write") is True:
        operation["parameters"] = [
            {"name": "X-Content-OS-CSRF", "in": "header", "required": True, "schema": {"type": "string", "minLength": 1}}
        ]
        operation["requestBody"] = {"required": True, "content": {"application/json": {"schema": {"type": "object"}}}}
        if spec.get('binary'):
            operation['requestBody'] = {'required': True, 'content': {'video/mp4': {'schema': {'type': 'string', 'format': 'binary'}}}}
            operation['parameters'].append({'name': 'X-Video-Identity', 'in': 'header', 'required': True, 'schema': {'type': 'string'}})
        operation["responses"]["409"] = _response("Revision conflict")
    if '/direct/jobs' in str(spec['path']) and not spec.get('response_media'):
        job_schema = {'$ref': '#/components/schemas/DirectJob'}
        if spec['operation_id'] == 'getLatestDirectJob':
            job_schema = {'anyOf': [job_schema, {'type': 'null'}]}
        operation['responses']['200']['content']['application/json']['schema'] = {
            'type': 'object', 'required': ['ok', 'job'],
            'properties': {'ok': {'const': True}, 'job': job_schema}}
        if spec['operation_id'] == 'createDirectJob':
            operation['responses']['201'] = operation['responses'].pop('200')
        operation['responses']['403'] = _response('Same-origin or CSRF check failed')
        operation['responses']['404'] = _response('Project, job, shot or artifact not found')
        operation['responses']['409'] = _response('Task busy or required artifacts not ready')
    if spec['operation_id'] == 'uploadDirectNarration':
        operation['requestBody'] = {'required': True, 'content': {'audio/wav': {'schema': {'type': 'string', 'format': 'binary', 'maxLength': 104857600}}}}
    if spec['operation_id'] == 'uploadPromoImage':
        operation['requestBody'] = {'required': True, 'content': {mime: {'schema': {'type': 'string', 'format': 'binary', 'maxLength': 20971520}} for mime in ('image/png', 'image/jpeg')}}
    if spec['operation_id'] == 'getMusicLibrary':
        operation['description'] = ('Each track retains its existing beat field; promoBeat contains status '
                                    '(ready, missing or failed), bars, bpm, sections (startBar, endBar, kind), '
                                    'firstBuildBar, and reason on failure.')
    if spec['operation_id'] == 'createDirectJob':
        operation['requestBody']['content']['application/json']['schema'] = {
            'type': 'object', 'oneOf': [{'required': ['script']}, {'required': ['storyboard']}],
            'properties': {'script': {'type': 'string', 'maxLength': 20000},
                           'storyboard': {'type': 'object', 'required': ['shots'], 'properties': {'shots': {
                               'type': 'array', 'minItems': 1, 'maxItems': 99, 'items': {
                                   'type': 'object', 'required': ['shotId', 'dialogue'], 'properties': {
                                       'shotId': {'type': 'string', 'pattern': '^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$'},
                                       'dialogue': {'type': 'string', 'minLength': 1, 'maxLength': 2000}}}}}},
                           'style': {'type': 'string', 'maxLength': 4000}, 'model': {'type': 'string', 'enum': ['claude-opus-5-5']}}}
    if spec['operation_id'] == 'rewriteDirectShot':
        operation['description'] = 'For interrupted or failed shots, omitted, null or blank instruction retries the prior writing intent and includes prior check errors. Every other state requires 1–200 characters after trimming.'
        operation['requestBody']['required'] = False
        operation['requestBody']['content']['application/json']['schema'] = {
            'type': 'object', 'properties': {'instruction': {'type': ['string', 'null'], 'maxLength': 200,
                'description': 'May be empty only when the current shot is interrupted or failed; otherwise a nonblank instruction is required.'}}}
    if spec['operation_id'] == 'reanalyzeMusic':
        operation['requestBody']['content']['application/json']['schema'] = {
            'type': 'object', 'required': ['part'],
            'properties': {'part': {'type': 'string', 'enum': ['beat', 'tags']}},
        }
        operation['responses'].pop('409', None)
        for status, codes in [('400', ['music_part_invalid']),
                              ('404', ['music_track_not_found']),
                              ('403', ['csrf_invalid', 'origin_forbidden'])]:
            operation['responses'][status] = {
                'description': 'Music reanalysis error',
                'content': {'application/json': {'schema': {
                    'type': 'object', 'required': ['ok', 'error'],
                    'properties': {
                        'ok': {'const': False},
                        'error': {'type': 'object', 'required': ['code', 'message'],
                                  'properties': {'code': {'type': 'string', 'enum': codes},
                                                 'message': {'type': 'string'}}},
                    },
                }}},
            }
    # The revision-library decorator assumes /api/direct responses are JSON.
    if not (spec.get('response_media') and str(spec['path']).startswith('/api/direct/')):
        operation_contract(operation, spec)
    direct_style_contract.operation_contract(operation, spec)
    direct_handoff_contract.operation_contract(operation, spec)
    if spec['operation_id'] in WORK_DELETE_OPERATIONS:
        _work_delete_operation(operation, str(spec['operation_id']))
    return operation


WORK_DELETE_OPERATIONS = {'previewProjectDeletion', 'deleteProjects', 'listDeletedProjects',
                          'restoreProjects', 'restoreProject', 'dismissDeletedProject'}


def _work_delete_operation(operation, name):
    from studio.work_trash import ELIGIBILITY_CODES, RESULT_CODES
    project_ids = {'type': 'array', 'minItems': 1, 'maxItems': 500, 'uniqueItems': True,
                   'items': {'type': 'string', 'pattern': '^[a-z0-9][a-z0-9_-]{7,63}$'}}
    revision = {'type': 'integer', 'minimum': 1}
    expected = {'type': 'object', 'minProperties': 1, 'additionalProperties': revision,
                'description': 'Exactly one current revision per requested project ID.'}
    batch = {'type': 'string', 'pattern': '^delete-[0-9a-f]{32}$'}
    undo = {'type': 'object', 'required': ['projectIds', 'expectedRevisions', 'batchId'],
            'properties': {'projectIds': {**project_ids, 'minItems': 0},
                           'expectedRevisions': {**expected, 'minProperties': 0}, 'batchId': batch}}
    if name != 'listDeletedProjects':
        if name in ('restoreProject', 'dismissDeletedProject'):
            properties, required = {'expectedRevision': revision}, ['expectedRevision']
        else:
            properties, required = {'projectIds': project_ids}, ['projectIds']
            if name != 'previewProjectDeletion':
                properties['expectedRevisions'] = expected
                required.append('expectedRevisions')
            if name == 'deleteProjects':
                properties.update(moveFolders={'type': 'boolean', 'default': False},
                                  folderProjectIds={**project_ids, 'minItems': 0,
                                                    'description': 'Optional selected subset to move; requires moveFolders=true. Omitted means all requested works. Ineligible requested moves fail individually.'})
            if name == 'restoreProjects':
                properties['batchId'] = batch
        operation['requestBody']['content']['application/json']['schema'] = {
            'type': 'object', 'required': required, 'properties': properties, 'additionalProperties': False}
    item = {'type': 'object', 'required': ['id', 'title', 'group_title', 'folder_name', 'created_at', 'revision'],
            'properties': {key: {'type': 'string'} for key in ('id', 'title', 'group_title', 'folder_name', 'created_at')}}
    item['properties']['revision'] = revision
    if name in ('previewProjectDeletion', 'listDeletedProjects'):
        if name == 'previewProjectDeletion':
            item['required'] += ['can_move_folder', 'reason_code']
            item['properties'].update(can_move_folder={'type': 'boolean'},
                                      reason_code={'enum': [None, *ELIGIBILITY_CODES]})
        else:
            item['required'] += ['deleted_at', 'folder_status', 'reason_code', 'can_restore', 'can_dismiss']
            item['properties'].update(deleted_at={'type': 'string', 'format': 'date-time'},
                                      folder_status={'enum': ['original', 'trash', 'unrecoverable']},
                                      reason_code={'enum': [None, *RESULT_CODES]},
                                      can_restore={'type': 'boolean'}, can_dismiss={'type': 'boolean'})
        payload = {'items': {'type': 'array', 'items': item}}
    elif name == 'dismissDeletedProject':
        payload = {'id': {'type': 'string'}, 'revision': revision}
    else:
        result = {'type': 'object', 'required': ['id', 'ok', 'code'],
                  'properties': {'id': {'type': 'string'}, 'ok': {'type': 'boolean'},
                                 'code': {'enum': [None, *RESULT_CODES]}, 'revision': revision}}
        payload = {'results': {'type': 'array', 'items': result},
                   'succeeded': {'type': 'integer', 'minimum': 0}, 'failed': {'type': 'integer', 'minimum': 0}}
        if name == 'deleteProjects':
            payload.update(batch_id=batch, undo=undo)
    operation['responses']['200']['content']['application/json']['schema'] = {
        'type': 'object', 'required': ['ok', *payload], 'properties': {'ok': {'const': True}, **payload}}
    operation['responses']['200']['description'] = 'Per-item failures remain HTTP 200; succeeded + failed equals requested count.' if name in ('deleteProjects', 'restoreProjects', 'restoreProject') else 'Successful local response'
    operation['responses']['403'] = _response('Invalid CSRF token or forbidden origin')


def _path_parameters(path: str) -> list[dict[str, Any]]:
    return [
        {"name": name, "in": "path", "required": True, "schema": {"type": "string"}}
        for name in re.findall(r"\{([A-Za-z][A-Za-z0-9]*)\}", path)
    ]


def build_openapi() -> dict[str, Any]:
    paths: dict[str, Any] = {}
    for spec in ROUTE_SPECS:
        path = str(spec["path"])
        item = paths.setdefault(path, {})
        parameters = _path_parameters(path)
        if parameters:
            item["parameters"] = parameters
        item[str(spec["method"]).lower()] = _operation(spec)
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Photo Content OS Desktop API",
            "version": "1.0.0",
            "description": "Loopback-only, CSRF-protected studio contract. Upstream login is optional.",
        },
        "servers": [{"url": "http://127.0.0.1:8765"}],
        "paths": paths,
        "components": {"schemas": {"DirectJob": _direct_job_schema(), "DirectStyleDraft": direct_style_contract.draft_schema(_direct_job_schema())}},
    }


__all__ = ["ROUTE_SPECS", "build_openapi", "is_registered_route", "route_inventory"]
