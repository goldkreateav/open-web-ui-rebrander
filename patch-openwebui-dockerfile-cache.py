from __future__ import annotations

import argparse
from pathlib import Path


def patch_text(src: str) -> str:
    # Require BuildKit syntax that supports RUN --mount=type=cache
    if src.startswith("# syntax=docker/dockerfile:1\n"):
        src = src.replace("# syntax=docker/dockerfile:1\n", "# syntax=docker/dockerfile:1.7\n", 1)
    elif src.startswith("# syntax=docker/dockerfile:"):
        # leave as-is (already pinned)
        pass
    else:
        src = "# syntax=docker/dockerfile:1.7\n" + src

    # Frontend: persist npm cache between builds (BuildKit cache mount)
    src = src.replace(
        "RUN npm ci --force\n",
        "RUN --mount=type=cache,target=/root/.npm npm ci --force\n",
        1,
    )

    # Backend: enable caching for pip/uv downloads by:
    # - mounting /root/.cache (pip + uv)
    # - removing --no-cache-dir (it disables cache and defeats the mount)
    src = src.replace("pip3 install --no-cache-dir uv;", "pip3 install uv;")
    src = src.replace("uv pip install --system -r requirements.txt --no-cache-dir;", "uv pip install --system -r requirements.txt;")
    src = src.replace(
        "RUN set -e; \\",
        "RUN --mount=type=cache,target=/root/.cache set -e; \\",
        1,
    )

    # Optional: torch installs also download wheels; allow cache usage.
    src = src.replace("--no-cache-dir; \\", "; \\")

    return src


def main() -> int:
    ap = argparse.ArgumentParser(description="Patch Open WebUI Dockerfile to use BuildKit cache mounts.")
    ap.add_argument("--dockerfile", default="Dockerfile", help="Path to Dockerfile (default: ./Dockerfile)")
    ap.add_argument("--in-place", action="store_true", help="Modify Dockerfile in place (default)")
    args = ap.parse_args()

    dockerfile = Path(args.dockerfile).resolve()
    if not dockerfile.exists():
        raise SystemExit(f"Dockerfile not found: {dockerfile}")

    original = dockerfile.read_text(encoding="utf-8")
    patched = patch_text(original)
    if patched == original:
        return 0

    dockerfile.write_text(patched, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

