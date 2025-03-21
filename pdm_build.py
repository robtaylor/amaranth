import os
from datetime import datetime
from pdm.backend.hooks.version import SCMVersion
from pdm.backend._vendor.packaging.version import Version


def format_version(version: SCMVersion) -> str:
    # Split version parts and ensure we have at least 3 parts (major, minor, patch)
    version_parts = str(version.version).split(".")
    
    # Handle the case with fewer than 3 version components
    if len(version_parts) < 3:
        if len(version_parts) == 1:
            major = int(version_parts[0])
            minor = 0
            patch = 0
        elif len(version_parts) == 2:
            major = int(version_parts[0])
            minor = int(version_parts[1])
            patch = 0
        else:
            # This should never happen (length can't be < 1), but just in case
            major = 0
            minor = 0
            patch = 0
    else:
        major, minor, patch = (int(n) for n in version_parts[:3])
    
    dirty = f"+{datetime.utcnow():%Y%m%d.%H%M%S}" if version.dirty else ""
    if version.distance is None:
        return f"{major}.{minor}.{patch}{dirty}"
    else:
        return f"{major}.{minor}.{patch}.dev{version.distance}{dirty}"


def pdm_build_initialize(context):
    version = Version(context.config.metadata["version"])

    # This is done in a PDM build hook without specifying `dynamic = [..., "version"]` to put all
    # of the static metadata into pyproject.toml. Tools other than PDM will not execute this script
    # and will use the generic version of the documentation URL (which redirects to /latest).
    if version.is_prerelease:
        url_version = "latest"
    else:
        url_version = f"v{version}"
    context.config.metadata["urls"]["Documentation"] += url_version
