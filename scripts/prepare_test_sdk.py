"""Bridge a release-asset naming mismatch in genlayer-test 0.29.2.

The contract's pinned runner is in GenVM v0.3.0-rc7. genlayer-test 0.29.2
tries to download an old 'genvm-universal.tar.xz' asset name that no longer
exists on that GitHub release. genvm-linter 0.11.0 downloads the same archive
from the current release asset. This script lets gltest reuse that local file.
It does not modify installed packages or any contract source.
"""

from pathlib import Path
import os
import shutil
import subprocess
import sys


VERSION = "v0.3.0-rc7"
NAME = f"genvm-universal-{VERSION}.tar.xz"


def main() -> None:
    home = Path.home()
    origin = home / ".cache" / "genvm-linter" / NAME
    target = home / ".cache" / "gltest-direct" / NAME
    if target.exists():
        print(f"Test SDK already prepared: {target}")
        return
    if not origin.exists():
        subprocess.run(["genvm-lint", "download", "-v", VERSION], check=True)
    if not origin.is_file():
        raise RuntimeError(f"Missing GenVM release archive: {origin}")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        if os.name == "nt":
            raise OSError("Use a copy on Windows")
        target.symlink_to(origin)
        print(f"Linked GenVM artifact: {target}")
    except OSError:
        shutil.copy2(origin, target)
        print(f"Copied GenVM artifact: {target}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Test SDK preparation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
