"""Local-first Photo Content OS Studio.

The desktop package deliberately uses only the Python standard library and the
existing Content OS runtime.  It exposes a loopback-only HTTP application for
ordinary users while keeping raw media paths and bytes on the local device.
"""

from .project_store import ProjectStore, ProjectStoreError

__all__ = ["ProjectStore", "ProjectStoreError"]
