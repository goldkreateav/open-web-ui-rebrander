from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> str:
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=False,
        check=False,
    )
    if p.stdout:
        print(p.stdout.rstrip())
    if p.returncode != 0:
        raise RuntimeError(f"Command failed (exit {p.returncode}): {' '.join(cmd)}")
    return (p.stdout or "").strip()


def _print_custom_css_preview(open_webui_dir: Path) -> None:
    candidates = [
        open_webui_dir / "backend" / "open_webui" / "static" / "custom.css",
        open_webui_dir / "static" / "static" / "custom.css",
    ]
    for p in candidates:
        if not p.exists():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        line = next((ln.strip() for ln in text.splitlines() if "--color-gray-950" in ln), None)
        if line:
            print(f"custom.css ({p}): {line}")


def which_or_fail(name: str) -> None:
    # We rely on subprocess resolving PATH; keep the check simple.
    try:
        subprocess.run([name, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except FileNotFoundError as e:
        raise RuntimeError(f"Command not found in PATH: {name}") from e


def git_is_repo(open_webui_dir: Path) -> bool:
    out = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=open_webui_dir)
    return out.strip() == "true"


def git_fast_forward_pull(open_webui_dir: Path, remote: str, branch: str) -> None:
    run(["git", "fetch", "--prune", remote], cwd=open_webui_dir)

    local_ref = "HEAD"
    remote_ref = f"{remote}/{branch}"

    local_sha = run(["git", "rev-parse", local_ref], cwd=open_webui_dir)
    remote_sha = run(["git", "rev-parse", remote_ref], cwd=open_webui_dir)

    if local_sha == remote_sha:
        print(f"open-webui is already up to date ({local_sha})")
        return

    # Only allow fast-forward updates. If diverged/ahead, abort.
    try:
        run(["git", "merge-base", "--is-ancestor", local_ref, remote_ref], cwd=open_webui_dir)
    except RuntimeError as e:
        raise RuntimeError(
            f"Local branch is not a fast-forward of {remote_ref}. "
            "Resolve manually (local changes/ahead/diverged), then rerun."
        ) from e

    print(f"Updating open-webui: fast-forwarding to {remote_ref} ({remote_sha})")
    run(["git", "pull", "--ff-only", remote, branch], cwd=open_webui_dir)


def git_clone(open_webui_dir: Path, repo_url: str, branch: str) -> None:
    """
    Clone Open WebUI into open_webui_dir.

    We clone a single branch to keep it fast and deterministic.
    """
    parent = open_webui_dir.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

    print(f"Cloning open-webui into {open_webui_dir} (branch: {branch})")
    run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            branch,
            repo_url,
            str(open_webui_dir),
        ],
        cwd=parent,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update open-webui from git (if behind), apply branding, then build Docker image."
    )
    parser.add_argument(
        "--open-webui-dir",
        default=str(Path(__file__).resolve().parent / "open-webui"),
        help="Path to the open-webui clone (default: ./open-webui)",
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent / "branding-tools" / "branding" / "branding.config.json"),
        help="Path to branding.config.json (default: ./branding-tools/branding/branding.config.json)",
    )
    parser.add_argument("--image-tag", default="open-webui:branded", help="Docker image tag (default: open-webui:branded)")
    parser.add_argument(
        "--repo",
        default="https://github.com/open-webui/open-webui.git",
        help="Git repo URL to clone when open-webui-dir is missing (default: upstream Open WebUI)",
    )
    parser.add_argument("--remote", default="origin", help="Git remote (default: origin)")
    parser.add_argument("--branch", default="main", help="Git branch (default: main)")
    parser.add_argument("--no-cache", action="store_true", help="Build Docker image without cache (docker build --no-cache)")
    parser.add_argument("--no-pull", action="store_true", help="Skip git update step")
    parser.add_argument("--no-branding", action="store_true", help="Skip apply_branding.py step")
    parser.add_argument("--no-build", action="store_true", help="Skip docker build step")

    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    open_webui_dir = Path(args.open_webui_dir).resolve()
    config_path = Path(args.config).resolve()

    which_or_fail("git")
    which_or_fail("docker")
    # Use current interpreter for branding execution.

    if not config_path.exists():
        raise RuntimeError(f"Branding config not found: {config_path}")

    if not open_webui_dir.exists():
        git_clone(open_webui_dir, repo_url=args.repo, branch=args.branch)

    if not args.no_pull:
        if not git_is_repo(open_webui_dir):
            raise RuntimeError(f"Not a git repository: {open_webui_dir}")
        git_fast_forward_pull(open_webui_dir, remote=args.remote, branch=args.branch)

    if not args.no_branding:
        apply_branding = (root / "branding-tools" / "branding" / "apply_branding.py").resolve()
        if not apply_branding.exists():
            raise RuntimeError(f"Branding script not found: {apply_branding}")

        print("Applying branding...")
        run(
            [
                sys.executable,
                str(apply_branding),
                "--config",
                str(config_path),
                "--target-dir",
                str(open_webui_dir),
            ],
            cwd=root,
        )
        _print_custom_css_preview(open_webui_dir)

    if not args.no_build:
        print(f"Building Docker image: {args.image_tag}")
        docker_cmd = ["docker", "build"]
        if args.no_cache:
            docker_cmd.append("--no-cache")
        docker_cmd += ["-t", args.image_tag, "."]
        run(docker_cmd, cwd=open_webui_dir)

    print("Done.")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    raise SystemExit(main())

