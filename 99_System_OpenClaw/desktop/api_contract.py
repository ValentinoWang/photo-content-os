"""Canonical OpenAPI contract for the loopback desktop service."""

from __future__ import annotations

from typing import Any


def _response(description: str = "Successful local response") -> dict[str, Any]:
    return {
        "description": description,
        "content": {"application/json": {"schema": {"type": "object", "required": ["ok"]}}},
    }


def _operation(operation_id: str, summary: str, *, write: bool = False) -> dict[str, Any]:
    operation: dict[str, Any] = {
        "operationId": operation_id,
        "summary": summary,
        "responses": {"200": _response(), "400": _response("Invalid request")},
    }
    if write:
        operation["parameters"] = [
            {
                "name": "X-Content-OS-CSRF",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "minLength": 1},
            }
        ]
        operation["requestBody"] = {
            "required": True,
            "content": {"application/json": {"schema": {"type": "object"}}},
        }
        operation["responses"]["409"] = _response("Revision conflict")
    return operation


def _project_parameters() -> list[dict[str, Any]]:
    return [
        {
            "name": "projectId",
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        }
    ]


def build_openapi() -> dict[str, Any]:
    paths: dict[str, Any] = {
        "/api/bootstrap": {"get": _operation("getBootstrap", "Read desktop bootstrap state")},
        "/api/health": {"get": _operation("getHealth", "Read loopback service health")},
        "/api/diagnostics": {"get": _operation("getDiagnostics", "Run dynamic local diagnostics")},
        "/api/settings": {"get": _operation("getSettings", "Read redacted desktop settings")},
        "/api/settings/analysis-budget": {
            "get": _operation("getAnalysisBudget", "Read the effective analysis budget"),
            "post": _operation("updateAnalysisBudget", "Update the analysis budget with CAS", write=True),
        },
        "/api/projects": {
            "get": _operation("listProjects", "List local projects"),
            "post": _operation("createProject", "Create a local project", write=True),
        },
        "/api/projects/{projectId}": {
            "parameters": _project_parameters(),
            "get": _operation("getProject", "Read a project"),
            "patch": _operation("updateProject", "Update a project with CAS", write=True),
        },
        "/api/projects/{projectId}/inbox-plan": {
            "parameters": _project_parameters(),
            "post": _operation("previewInboxPlan", "Preview deterministic inbox batches", write=True),
        },
        "/api/projects/{projectId}/inbox-plan/confirm": {
            "parameters": _project_parameters(),
            "post": _operation("confirmInboxPlan", "Confirm one plan batch and target project", write=True),
        },
        "/api/assets": {"get": _operation("listAssets", "Query the structured asset index")},
        "/api/assets/statistics": {"get": _operation("getAssetStatistics", "Read dynamic asset facets")},
        "/api/assets/{assetId}": {
            "parameters": [{"name": "assetId", "in": "path", "required": True, "schema": {"type": "string"}}],
            "get": _operation("getAsset", "Read one structured asset"),
        },
        "/api/projects/{projectId}/assets": {
            "parameters": _project_parameters(),
            "post": _operation("addProjectAsset", "Add an indexed asset reference to a project", write=True),
        },
        "/api/setup/state": {
            "get": _operation("getSetupState", "Read resumable four-step setup state"),
            "post": _operation("updateSetupState", "Persist one setup transition with CAS", write=True),
        },
        "/api/upstream/tasks": {"get": _operation("getUpstreamTasks", "Read optional upstream task projections")},
    }
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


__all__ = ["build_openapi"]
