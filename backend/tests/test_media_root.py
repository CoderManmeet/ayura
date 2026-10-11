"""
Phase B (Ayura): uploads can be pointed at another folder with DJANGO_MEDIA_ROOT.

The Playwright suite uploads a product photo through the admin area; it sets DJANGO_MEDIA_ROOT
to backend/e2e-media/ so nothing is written into backend/media/ (CLAUDE.md, section 2 traps).

Settings are read once when Django starts, so each case starts a fresh interpreter.
Fails before the change (MEDIA_ROOT ignores the variable) and passes after it.
"""

import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent

SCRIPT = "import django; django.setup(); from django.conf import settings; print(settings.MEDIA_ROOT)"


def _media_root(extra_env):
    env = {name: value for name, value in os.environ.items() if name != "DJANGO_MEDIA_ROOT"}
    env.update({"DJANGO_SETTINGS_MODULE": "backend.settings", **extra_env})
    result = subprocess.run([sys.executable, "-c", SCRIPT], cwd=BACKEND, env=env,
                            capture_output=True, text=True, timeout=120, check=True)
    return Path(result.stdout.strip().splitlines()[-1])


def test_media_root_defaults_to_backend_media():
    assert _media_root({}) == BACKEND / "media"


def test_media_root_follows_django_media_root(tmp_path):
    target = tmp_path / "uploads"
    assert _media_root({"DJANGO_MEDIA_ROOT": str(target)}) == target
