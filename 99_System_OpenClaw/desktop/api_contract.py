"""Canonical route inventory and OpenAPI contract for the loopback desktop service."""

from __future__ import annotations

import re
from typing import Any


ROUTE_SPECS: tuple[dict[str, object], ...] = (
    {"method": "GET", "path": "/api/bootstrap", "operation_id": "getBootstrap", "summary": "Read desktop bootstrap state"},
    {"method": "GET", "path": "/api/health", "operation_id": "getHealth", "summary": "Read loopback service health"},
    {"method": "GET", "path": "/api/diagnostics", "operation_id": "getDiagnostics", "summary": "Run dynamic local diagnostics"},
    {"method": "GET", "path": "/api/settings", "operation_id": "getSettings", "summary": "Read redacted desktop settings"},
    {"method": "GET", "path": "/api/settings/analysis-budget", "operation_id": "getAnalysisBudget", "summary": "Read the effective analysis budget"},
    {"method": "POST", "path": "/api/settings/analysis-budget", "operation_id": "updateAnalysisBudget", "summary": "Update the analysis budget with CAS", "write": True},
    {"method": "GET", "path": "/api/projects", "operation_id": "listProjects", "summary": "List local projects"},
    {"method": "POST", "path": "/api/projects", "operation_id": "createProject", "summary": "Create a local project", "write": True},
    {"method": "GET", "path": "/api/projects/{projectId}", "operation_id": "getProject", "summary": "Read a project"},
    {"method": "PATCH", "path": "/api/projects/{projectId}", "operation_id": "updateProject", "summary": "Update a project with CAS", "write": True},
    {"method": "POST", "path": "/api/projects/{projectId}/inbox-plan", "operation_id": "previewInboxPlan", "summary": "Preview deterministic inbox batches", "write": True},
    {"method": "POST", "path": "/api/projects/{projectId}/inbox-plan/confirm", "operation_id": "confirmInboxPlan", "summary": "Confirm one plan batch and target project", "write": True},
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


def is_registered_route(method: str, path: str) -> bool:
    for spec in ROUTE_SPECS:
        if spec["method"] != method.upper():
            continue
        pattern = re.sub(r"\{[A-Za-z][A-Za-z0-9]*\}", r"[^/]+", str(spec["path"]))
        if re.fullmatch(pattern, path):
            return True
    return False


def _response(description: str = "Successful local response") -> dict[str, Any]:
    return {
        "description": description,
        "content": {"application/json": {"schema": {"type": "object", "required": ["ok"]}}},
    }


def _operation(spec: dict[str, object]) -> dict[str, Any]:
    operation: dict[str, Any] = {
        "operationId": spec["operation_id"],
        "summary": spec["summary"],
        "responses": {"200": _response(), "400": _response("Invalid request")},
    }
    if spec.get("write") is True:
        operation["parameters"] = [
            {"name": "X-Content-OS-CSRF", "in": "header", "required": True, "schema": {"type": "string", "minLength": 1}}
        ]
        operation["requestBody"] = {"required": True, "content": {"application/json": {"schema": {"type": "object"}}}}
        operation["responses"]["409"] = _response("Revision conflict")
    return operation


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
            "description": "Loopback-only, CSRF-protected desktop contract. Upstream login is optional.",
        },
        "servers": [{"url": "http://127.0.0.1:8765"}],
        "paths": paths,
    }


__all__ = ["ROUTE_SPECS", "build_openapi", "is_registered_route", "route_inventory"]
