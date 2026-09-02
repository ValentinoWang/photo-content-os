"""Fail closed when the desktop OpenAPI and served route inventory drift."""

from __future__ import annotations

import importlib
import json
import re
import sys
import unittest
from pathlib import Path


SYSTEM = Path(__file__).resolve().parents[1]
if str(SYSTEM) not in sys.path:
    sys.path.insert(0, str(SYSTEM))


class DesktopOpenApiRouteSyncTests(unittest.TestCase):
    def test_openapi_methods_equal_the_server_registration(self) -> None:
        contract = importlib.import_module("desktop.api_contract")
        server = importlib.import_module("desktop.server")
        checked_in = json.loads((SYSTEM / "schemas" / "desktop_openapi.json").read_text(encoding="utf-8"))

        documented = {
            (method.upper(), path)
            for path, path_item in checked_in["paths"].items()
            for method in path_item
            if method.lower() in {"get", "post", "patch", "put", "delete"}
        }
        registered = {(item["method"], item["path"]) for item in contract.route_inventory()}

        self.assertEqual(documented, registered)
        self.assertEqual(contract.route_inventory(), server.served_route_inventory())
        for method, path in registered:
            concrete = re.sub(r"\{[^}]+\}", "contract-value", path)
            self.assertTrue(contract.is_registered_route(method, concrete), (method, path))


if __name__ == "__main__":
    unittest.main()
