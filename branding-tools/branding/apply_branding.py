from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import colorsys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from branding_rules import (  # type: ignore  # local import
	I18N_PHRASES_WITH_OLD_BRAND,
	HARD_CODED_REPLACEMENTS,
	OLD_BRAND,
	USER_LIST_MARKDOWN_NEEDLE,
	build_replacements_for_app_name,
	i18n_phrase_replacements,
)


@dataclass(frozen=True)
class Config:
	path: Path
	app_name: str
	company_name: Optional[str]
	copyright_owner: Optional[str]
	suffix_strategy: str
	colors: Dict[str, str]
	css_vars: Dict[str, Dict[str, str]]
	favicon: Dict[str, str]
	splash: Dict[str, str]
	logo: Dict[str, str]
	pwa: Dict[str, str]
	links: Dict[str, str]
	attribution: Dict[str, Any]
	webui_favicon_url: Optional[str]
	openwebui_team_name: str


def _read_text(path: Path) -> str:
	return path.read_text(encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
	path.write_text(content, encoding="utf-8")


def _resolve_config_relpath(config_path: Path, p: str) -> Path:
	pp = Path(p)
	if pp.is_absolute():
		return pp
	return (config_path.parent / pp).resolve()


def _sha1_head(path: Path) -> str:
	# Only for reports; avoid git dependency.
	# If the file doesn't exist, return empty.
	if not path.exists():
		return ""
	import hashlib

	h = hashlib.sha1()
	with path.open("rb") as f:
		for chunk in iter(lambda: f.read(1024 * 1024), b""):
			h.update(chunk)
	return h.hexdigest()[:12]


def load_config(config_path: Path) -> Config:
	with config_path.open("r", encoding="utf-8") as f:
		raw = json.load(f)

	if not isinstance(raw, dict):
		raise ValueError("Config JSON root must be an object")
	if "appName" not in raw or not raw["appName"]:
		raise ValueError("Missing required config key: appName")

	default_colors = {
		"primaryColor": "#171717",
		"lightThemeColor": "#ffffff",
		"oledThemeColor": "#000000",
		"herThemeColor": "#983724",
	}
	colors = {**default_colors, **(raw.get("colors") or {})}

	# Optional CSS variable overrides. This is the "full control" surface.
	# Structure:
	# "cssVars": {
	#   "root": { "--color-gray-950": "#0d0d0d", ... },
	#   "dark": { "--color-gray-950": "#101010", ... },
	#   "oled-dark": { ... },
	#   "her": { ... }
	# }
	css_vars = raw.get("cssVars") or {}
	if not isinstance(css_vars, dict):
		raise ValueError("cssVars must be an object/dict if provided")
	normalized_css_vars: Dict[str, Dict[str, str]] = {}
	for scope, mapping in css_vars.items():
		if not isinstance(mapping, dict):
			continue
		normalized_css_vars[str(scope)] = {str(k): str(v) for k, v in mapping.items()}

	favicon = raw.get("favicon") or {}
	splash = raw.get("splash") or {}
	logo = raw.get("logo") or {}
	pwa = raw.get("pwa") or {}

	attribution = raw.get("attribution") or {}
	if "keepCommunityLinks" not in attribution:
		attribution["keepCommunityLinks"] = True
	if "keepLicenseBlock" not in attribution:
		attribution["keepLicenseBlock"] = True

	links = raw.get("links") or {}

	# Reasonable fallbacks if the user doesn't provide separate logo/pwa assets.
	if "png" not in logo and "png" in favicon:
		logo = {**logo, "png": favicon["png"]}
	if "webAppManifest192" not in pwa and "png" in logo:
		pwa = {**pwa, "webAppManifest192": logo["png"]}
	if "webAppManifest512" not in pwa and "png" in logo:
		pwa = {**pwa, "webAppManifest512": logo["png"]}

	return Config(
		path=config_path,
		app_name=raw["appName"],
		company_name=raw.get("companyName"),
		copyright_owner=raw.get("copyrightOwner"),
		suffix_strategy=raw.get("suffixStrategy", "keep_openwebui_suffix"),
		colors={
			"primaryColor": colors["primaryColor"],
			"lightThemeColor": colors["lightThemeColor"],
			"oledThemeColor": colors["oledThemeColor"],
			"herThemeColor": colors["herThemeColor"],
		},
		css_vars=normalized_css_vars,
		favicon=favicon,
		splash=splash,
		logo=logo,
		pwa=pwa,
		links=links,
		attribution=attribution,
		webui_favicon_url=raw.get("webuiFaviconUrl"),
		openwebui_team_name=raw.get("openwebuiTeamName") or raw["appName"],
	)


def _ensure_dir(path: Path) -> None:
	path.mkdir(parents=True, exist_ok=True)


def backup_path(backup_root: Path, file_path: Path, workspace_root: Path) -> Path:
	rel = file_path.resolve().relative_to(workspace_root.resolve())
	return backup_root / rel


def backup_file(
	file_path: Path,
	backup_root: Path,
	workspace_root: Path,
	ops: List[dict],
	dry_run: bool,
) -> None:
	backup_root_file = backup_path(backup_root, file_path, workspace_root)
	if backup_root_file.exists():
		return
	backup_root_file.parent.mkdir(parents=True, exist_ok=True)
	if dry_run:
		ops.append({"type": "backup", "file": str(file_path), "backup": str(backup_root_file), "dryRun": True})
		return
	shutil.copy2(str(file_path), str(backup_root_file))
	ops.append({"type": "backup", "file": str(file_path), "backup": str(backup_root_file)})


def replace_in_text(
	file_path: Path,
	replacements: Iterable[Tuple[str, str]],
	ops: List[dict],
	dry_run: bool,
	strict: bool,
	workspace_root: Path,
	backup_root: Path,
) -> None:
	original = _read_text(file_path)
	new_text = original
	found_any = False
	repl_list = list(replacements)
	for old, new in repl_list:
		if old == "":
			continue
		if old in new_text:
			found_any = True
			new_text = new_text.replace(old, new)

	if strict and not found_any:
		raise RuntimeError(f"[strict] No needles found in {file_path}")

	if new_text != original:
		backup_file(file_path, backup_root, workspace_root, ops, dry_run=dry_run)
		if not dry_run:
			_write_text(file_path, new_text)
		ops.append({"type": "textReplace", "file": str(file_path), "replacements": len(repl_list)})


def patch_text_by_regex(
	file_path: Path,
	pattern: str,
	repl: str,
	ops: List[dict],
	dry_run: bool,
	strict: bool,
	workspace_root: Path,
	backup_root: Path,
	flags: int = 0,
) -> None:
	original = _read_text(file_path)
	new_text = re.sub(pattern, repl, original, flags=flags)
	if strict and new_text == original:
		raise RuntimeError(f"[strict] Regex patch did not change anything: {file_path}")
	if new_text != original:
		backup_file(file_path, backup_root, workspace_root, ops, dry_run=dry_run)
		if not dry_run:
			_write_text(file_path, new_text)
		ops.append({"type": "regexPatch", "file": str(file_path)})


def replace_json_branding(
	json_path: Path,
	app_name: str,
	ops: List[dict],
	dry_run: bool,
	strict: bool,
	workspace_root: Path,
	backup_root: Path,
) -> None:
	data = json.loads(_read_text(json_path))
	if not isinstance(data, dict):
		raise RuntimeError(f"Expected JSON object in {json_path}")

	changed = False
	new_data: Dict[str, Any] = {}
	for k, v in data.items():
		new_k = k.replace(OLD_BRAND, app_name) if isinstance(k, str) else k
		new_v = v
		if isinstance(v, str) and OLD_BRAND in v:
			new_v = v.replace(OLD_BRAND, app_name)

		if new_k != k or new_v != v:
			changed = True
		new_data[new_k] = new_v

	if strict and not changed:
		raise RuntimeError(f"[strict] No JSON branding strings found in {json_path}")

	if changed:
		backup_file(json_path, backup_root, workspace_root, ops, dry_run=dry_run)
		if not dry_run:
			_write_text(json_path, json.dumps(new_data, ensure_ascii=False, indent=2) + "\n")
		ops.append({"type": "jsonBranding", "file": str(json_path)})


def iter_source_files(root: Path, exts: Iterable[str]) -> Iterable[Path]:
	for p in root.rglob("*"):
		if p.is_file() and p.suffix.lower() in exts:
			yield p


def apply_text_replacement_set_in_tree(
	source_root: Path,
	replacements: Dict[str, str],
	ops: List[dict],
	dry_run: bool,
	strict: bool,
	workspace_root: Path,
	backup_root: Path,
	only_exts: Iterable[str],
) -> None:
	exts = set([e.lower() for e in only_exts])
	for file_path in source_root.rglob("*"):
		if not file_path.is_file():
			continue
		if file_path.suffix.lower() not in exts:
			continue

		text = _read_text(file_path)
		needle_hits = sum(1 for old in replacements.keys() if old and old in text)
		if needle_hits == 0:
			continue

		file_repls: List[Tuple[str, str]] = []
		for old, new in replacements.items():
			if old and old in text:
				file_repls.append((old, new))

		replace_in_text(
			file_path=file_path,
			replacements=file_repls,
			ops=ops,
			dry_run=dry_run,
			strict=False,  # we already checked
			workspace_root=workspace_root,
			backup_root=backup_root,
		)

	if strict:
		# If strict: ensure at least one file hit each replacement.
		for old in replacements.keys():
			if old == "":
				continue
			hit = any(old in _read_text(p) for p in source_root.rglob("*") if p.is_file() and p.suffix.lower() in exts and "dry" not in p.name)
			# Note: we can't reliably check post-change. Keep it simple and validate pre-change hits separately in caller.
			_ = hit


def copy_asset(
	src: Path,
	dst: Path,
	ops: List[dict],
	dry_run: bool,
	workspace_root: Path,
	backup_root: Path,
) -> None:
	if not src.exists():
		raise FileNotFoundError(f"Asset source not found: {src}")
	backup_file(dst, backup_root, workspace_root, ops, dry_run=dry_run) if dst.exists() else None
	ops.append({"type": "assetCopy", "src": str(src), "dst": str(dst), "dryRun": dry_run})
	if dry_run:
		return
	dst.parent.mkdir(parents=True, exist_ok=True)
	shutil.copy2(str(src), str(dst))


def _normalize_hex_color(s: str) -> str:
	ss = (s or "").strip()
	if not ss:
		raise ValueError("Empty color string")
	if not ss.startswith("#"):
		raise ValueError(f"Color must start with '#': {s!r}")
	ss = ss.lower()
	if len(ss) == 4:
		# #rgb -> #rrggbb
		ss = "#" + "".join([c * 2 for c in ss[1:]])
	if len(ss) != 7:
		raise ValueError(f"Unsupported color format (expected #rrggbb or #rgb): {s!r}")
	return ss


def _hex_to_rgb01(hex_color: str) -> Tuple[float, float, float]:
	h = _normalize_hex_color(hex_color)
	r = int(h[1:3], 16) / 255.0
	g = int(h[3:5], 16) / 255.0
	b = int(h[5:7], 16) / 255.0
	return (r, g, b)


def _rgb01_to_hex(rgb: Tuple[float, float, float]) -> str:
	r, g, b = rgb
	ri = max(0, min(255, int(round(r * 255))))
	gi = max(0, min(255, int(round(g * 255))))
	bi = max(0, min(255, int(round(b * 255))))
	return f"#{ri:02x}{gi:02x}{bi:02x}"


def _mix_hex(a: str, b: str, t: float) -> str:
	"""Linear blend between two hex colors. t=0 -> a, t=1 -> b."""
	ar, ag, ab = _hex_to_rgb01(a)
	br, bg, bb = _hex_to_rgb01(b)
	t = max(0.0, min(1.0, float(t)))
	return _rgb01_to_hex((ar * (1 - t) + br * t, ag * (1 - t) + bg * t, ab * (1 - t) + bb * t))


def _lightness_adjust(hex_color: str, factor: float) -> str:
	"""Adjust lightness in HLS space. factor>1 => lighter, <1 => darker."""
	r, g, b = _hex_to_rgb01(hex_color)
	h, l, s = colorsys.rgb_to_hls(r, g, b)
	l = max(0.0, min(1.0, l * float(factor)))
	r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
	return _rgb01_to_hex((r2, g2, b2))


def write_custom_css(
	dst: Path,
	cfg_colors: Dict[str, str],
	cfg_css_vars: Dict[str, Dict[str, str]],
	ops: List[dict],
	dry_run: bool,
	workspace_root: Path,
	backup_root: Path,
) -> None:
	"""
	Generate a small CSS override that actually changes the app palette.
	Open WebUI relies heavily on `--color-gray-*` variables (see `src/tailwind.css`).
	We override those to match the configured branding colors.
	"""
	primary = _normalize_hex_color(cfg_colors["primaryColor"])
	light = _normalize_hex_color(cfg_colors["lightThemeColor"])
	oled = _normalize_hex_color(cfg_colors["oledThemeColor"])
	her = _normalize_hex_color(cfg_colors["herThemeColor"])

	# Dark palette: derive grays from the primary color by mixing towards black.
	# Chosen to keep enough contrast for text/UI while visibly changing the "scheme".
	d950 = _mix_hex(primary, "#000000", 0.75)
	d900 = _mix_hex(primary, "#000000", 0.55)
	d850 = _mix_hex(primary, "#000000", 0.40)
	d800 = _mix_hex(primary, "#000000", 0.25)
	d700 = _lightness_adjust(primary, 1.15)
	d600 = _lightness_adjust(primary, 1.35)
	d500 = _lightness_adjust(primary, 1.55)
	d400 = _lightness_adjust(primary, 1.85)
	d300 = _mix_hex(light, primary, 0.18)
	d200 = _mix_hex(light, primary, 0.10)
	d100 = _mix_hex(light, primary, 0.06)
	d50 = _mix_hex(light, primary, 0.03)

	def _emit_block(selector: str, vars_map: Dict[str, str]) -> List[str]:
		if not vars_map:
			return []
		lines = [f"{selector} {{"]
		for k, v in vars_map.items():
			lines.append(f"  {k}: {v};")
		lines.append("}")
		return lines

	# Base palette derived from config colors (works out of the box).
	root_vars: Dict[str, str] = {
		"--brand-primary": primary,
		"--brand-light": light,
		"--brand-oled": oled,
		"--brand-her": her,
		"--color-gray-50": d50,
		"--color-gray-100": d100,
		"--color-gray-200": d200,
		"--color-gray-300": d300,
		"--color-gray-400": d400,
		"--color-gray-500": d500,
		"--color-gray-600": d600,
		"--color-gray-700": d700,
		"--color-gray-800": d800,
		"--color-gray-850": d850,
		"--color-gray-900": d900,
		"--color-gray-950": d950,
	}

	dark_vars: Dict[str, str] = {
		"--color-gray-800": d800,
		"--color-gray-850": d850,
		"--color-gray-900": d900,
		"--color-gray-950": d950,
	}

	oled_vars: Dict[str, str] = {
		"--color-gray-800": _mix_hex(oled, "#000000", 0.40),
		"--color-gray-850": _mix_hex(oled, "#000000", 0.60),
		"--color-gray-900": oled,
		"--color-gray-950": oled,
	}

	her_vars: Dict[str, str] = {
		"--color-gray-900": _mix_hex(her, "#000000", 0.55),
		"--color-gray-950": _mix_hex(her, "#000000", 0.75),
	}

	# User overrides: full control per scope.
	# These overwrite derived defaults.
	root_vars.update(cfg_css_vars.get("root", {}))
	dark_vars.update(cfg_css_vars.get("dark", {}))
	oled_vars.update(cfg_css_vars.get("oled-dark", {}))
	her_vars.update(cfg_css_vars.get("her", {}))

	css_lines: List[str] = ["/* Auto-generated by branding-tools. */", ""]
	css_lines += _emit_block(":root", root_vars)
	css_lines.append("")
	css_lines += _emit_block("html.dark", dark_vars)
	css_lines.append("")
	css_lines += _emit_block("html.oled-dark, html.dark.oled-dark", oled_vars)
	css_lines.append("")
	css_lines += _emit_block("html.her", her_vars)
	css_lines.append("")

	css = "\n".join(css_lines)

	if dst.exists():
		backup_file(dst, backup_root, workspace_root, ops, dry_run=dry_run)
	ops.append({"type": "cssWrite", "file": str(dst), "dryRun": dry_run})
	if dry_run:
		return
	dst.parent.mkdir(parents=True, exist_ok=True)
	_write_text(dst, css)


def main(argv: Optional[List[str]] = None) -> int:
	parser = argparse.ArgumentParser(description="Apply Open WebUI branding based on a config file.")
	parser.add_argument("--config", required=True, help="Path to branding.config.json")
	parser.add_argument("--target-dir", required=True, help="Path to cloned open-webui (upstream or copy)")
	parser.add_argument("--dry-run", action="store_true", help="Show planned operations without writing")
	parser.add_argument("--strict", action="store_true", help="Fail if a replacement needle is not found")
	parser.add_argument(
		"--static-dir",
		default=None,
		help="Backend static dir to copy assets into (default: <target-dir>/backend/open_webui/static)",
	)
	parser.add_argument(
		"--no-frontend-static",
		action="store_true",
		help=(
			"Do not copy branding assets into frontend public static directories "
			"(<target-dir>/static/static and <target-dir>/static/favicon.png)."
		),
	)
	parser.add_argument(
		"--no-custom-css",
		action="store_true",
		help="Do not generate custom.css theme overrides.",
	)
	parser.add_argument(
		"--workspace-root",
		default=None,
		help="Workspace root for backups/paths (default: --target-dir)",
	)
	parser.add_argument(
		"--report",
		default=None,
		help="Report path (default: <target-dir>/branding-report.md)",
	)
	args = parser.parse_args(argv)

	config_path = Path(args.config).resolve()
	cfg = load_config(config_path)

	target_dir = Path(args.target_dir).resolve()
	if not target_dir.exists():
		raise RuntimeError(f"Target open-webui directory not found: {target_dir}")

	workspace_root = Path(args.workspace_root).resolve() if args.workspace_root else target_dir
	backup_root = target_dir / ".branding-backups" / datetime.now().strftime("%Y%m%d-%H%M%S")
	report_path = Path(args.report).resolve() if args.report else (target_dir / "branding-report.md")

	if args.static_dir:
		static_dir = Path(args.static_dir).resolve()
	else:
		static_dir = target_dir / "backend" / "open_webui" / "static"
	if not static_dir.exists():
		raise RuntimeError(f"Static dir not found: {static_dir}")

	ops: List[dict] = []
	app_name = cfg.app_name

	FRONTEND_DIR = target_dir / "src"
	BACKEND_DIR = target_dir / "backend" / "open_webui"
	FRONTEND_PUBLIC_DIR = target_dir / "static"
	FRONTEND_PUBLIC_STATIC_DIR = FRONTEND_PUBLIC_DIR / "static"

	# 1) Theme colors + title in frontend
	# (We change app.html; the rest of the UI uses WEBUI_NAME from backend.)
	app_html = FRONTEND_DIR / "app.html"
	replace_in_text(
		app_html,
		replacements=[
			('<title>Open WebUI</title>', f"<title>{app_name}</title>"),
			('meta name="theme-color" content="#171717"', f'meta name="theme-color" content="{cfg.colors["primaryColor"]}"'),
		],
		ops=ops,
		dry_run=args.dry_run,
		strict=args.strict,
		workspace_root=workspace_root,
		backup_root=backup_root,
	)

	# Keep APP_NAME constant in sync (used as frontend default before backend config loads).
	constants_ts = FRONTEND_DIR / "lib" / "constants.ts"
	if constants_ts.exists():
		replace_in_text(
			constants_ts,
			replacements=[("export const APP_NAME = 'Open WebUI';", f"export const APP_NAME = {json.dumps(app_name)};")],
			ops=ops,
			dry_run=args.dry_run,
			strict=args.strict,
			workspace_root=workspace_root,
			backup_root=backup_root,
		)

	# Update inline script theme-color values. We patch by exact hex tokens used in this file.
	hex_repls = [
		("#171717", cfg.colors["primaryColor"]),
		("#ffffff", cfg.colors["lightThemeColor"]),
		("#000000", cfg.colors["oledThemeColor"]),
		("#983724", cfg.colors["herThemeColor"]),
	]
	replace_in_text(
		app_html,
		replacements=hex_repls,
		ops=ops,
		dry_run=args.dry_run,
		strict=False,  # may not exist if upstream changed
		workspace_root=workspace_root,
		backup_root=backup_root,
	)

	# 2) Backend env: default WEBUI_NAME + optional suffix behavior
	env_py = BACKEND_DIR / "env.py"

	# Replace default name
	patch_text_by_regex(
		env_py,
		pattern=r"WEBUI_NAME\s*=\s*os\.environ\.get\('WEBUI_NAME',\s*'Open WebUI'\)",
		repl=f"WEBUI_NAME = os.environ.get('WEBUI_NAME', {json.dumps(app_name)})",
		ops=ops,
		dry_run=args.dry_run,
		strict=args.strict,
		workspace_root=workspace_root,
		backup_root=backup_root,
	)

	if cfg.suffix_strategy == "keep_openwebui_suffix":
		# Update conditional sentinel from 'Open WebUI' -> appName
		patch_text_by_regex(
			env_py,
			pattern=r"if\s+WEBUI_NAME\s*!=\s*'Open WebUI':\s*\n\s*WEBUI_NAME\s*\+=\s*' \(Open WebUI\)'",
			repl="if WEBUI_NAME != "
			+ json.dumps(app_name)
			+ ":\\n    WEBUI_NAME += ' (Open WebUI)'",
			ops=ops,
			dry_run=args.dry_run,
			strict=args.strict,
			workspace_root=workspace_root,
			backup_root=backup_root,
			flags=re.MULTILINE,
		)
	else:
		# Remove the entire suffix-append conditional block.
		patch_text_by_regex(
			env_py,
			pattern=r"if\s+WEBUI_NAME\s*!=\s*'Open WebUI':\s*\n\s*WEBUI_NAME\s*\+=\s*' \(Open WebUI\)'",
			repl="",
			ops=ops,
			dry_run=args.dry_run,
			strict=False,
			workspace_root=workspace_root,
			backup_root=backup_root,
			flags=re.MULTILINE,
		)

	# 3) OAuth client_name in provider metadata
	oauth_py = BACKEND_DIR / "utils" / "oauth.py"
	patch_text_by_regex(
		oauth_py,
		pattern=r"client_name='Open WebUI'",
		repl=f"client_name={json.dumps(app_name)}",
		ops=ops,
		dry_run=args.dry_run,
		strict=args.strict,
		workspace_root=workspace_root,
		backup_root=backup_root,
	)

	# 4) PWA manifest / site.webmanifest
	site_manifest = static_dir / "site.webmanifest"
	if site_manifest.exists():
		# Replace name and theme colors.
		patch_text_by_regex(
			site_manifest,
			pattern=r'"name"\s*:\s*"[^"]+"',
			repl=f'"name": {json.dumps(app_name)}',
			ops=ops,
			dry_run=args.dry_run,
			strict=False,
			workspace_root=workspace_root,
			backup_root=backup_root,
		)
		patch_text_by_regex(
			site_manifest,
			pattern=r'"short_name"\s*:\s*"[^"]+"',
			repl=f'"short_name": {json.dumps(app_name[:12])}',
			ops=ops,
			dry_run=args.dry_run,
			strict=False,
			workspace_root=workspace_root,
			backup_root=backup_root,
		)
		patch_text_by_regex(
			site_manifest,
			pattern=r'"theme_color"\s*:\s*"#[0-9a-fA-F]{6}"',
			repl=f'"theme_color": {json.dumps(cfg.colors["lightThemeColor"])}',
			ops=ops,
			dry_run=args.dry_run,
			strict=False,
			workspace_root=workspace_root,
			backup_root=backup_root,
		)
		patch_text_by_regex(
			site_manifest,
			pattern=r'"background_color"\s*:\s*"#[0-9a-fA-F]{6}"',
			repl=f'"background_color": {json.dumps(cfg.colors["lightThemeColor"])}',
			ops=ops,
			dry_run=args.dry_run,
			strict=False,
			workspace_root=workspace_root,
			backup_root=backup_root,
		)

	# 5) Assets
	#
	# Backend serves STATIC_DIR at '/static'.
	# Frontend (SvelteKit) also serves from '<target-dir>/static', and many upstream assets live under
	# '<target-dir>/static/static'. If we only patch backend static, UI assets can remain unchanged in dev builds.
	#
	# We therefore copy branding assets into:
	# - backend static_dir (always)
	# - frontend public static dirs (best-effort, unless --no-frontend-static)
	assets: List[Tuple[str, Optional[str]]] = [
		("favicon.png", cfg.favicon.get("png")),
		("favicon-dark.png", cfg.favicon.get("darkPng")),
		("favicon.svg", cfg.favicon.get("svg")),
		("favicon.ico", cfg.favicon.get("ico")),
		("favicon-96x96.png", cfg.favicon.get("png96")),
		("apple-touch-icon.png", cfg.favicon.get("appleTouch")),
		("splash.png", cfg.splash.get("light")),
		("splash-dark.png", cfg.splash.get("dark")),
		("logo.png", cfg.logo.get("png")),
		("web-app-manifest-192x192.png", cfg.pwa.get("webAppManifest192")),
		("web-app-manifest-512x512.png", cfg.pwa.get("webAppManifest512")),
	]

	def copy_asset_to_dirs(filename: str, src_rel: str, dst_dirs: List[Path]) -> None:
		src = _resolve_config_relpath(cfg.path, src_rel)
		for d in dst_dirs:
			# Best-effort: don't create entirely new trees by default; only copy if the dir exists.
			if not d.exists():
				ops.append({"type": "assetSkip", "dstDirMissing": str(d), "file": filename})
				continue
			copy_asset(
				src=src,
				dst=d / filename,
				ops=ops,
				dry_run=args.dry_run,
				workspace_root=workspace_root,
				backup_root=backup_root,
			)

	for filename, src_rel in assets:
		if not src_rel:
			continue
		dst_dirs: List[Path] = [static_dir]
		if not args.no_frontend_static:
			# Most upstream assets are in static/static/*
			dst_dirs.append(FRONTEND_PUBLIC_STATIC_DIR)
			# Additionally, favicon.png is referenced from /static/favicon.png in the repo root.
			# (We only mirror that one into static/ root.)
			if filename == "favicon.png":
				dst_dirs.append(FRONTEND_PUBLIC_DIR)

		copy_asset_to_dirs(filename=filename, src_rel=src_rel, dst_dirs=dst_dirs)

	# 5b) Generate custom.css to actually apply the palette across the UI.
	if not args.no_custom_css:
		# Backend-served (Docker/prod) path.
		write_custom_css(
			dst=static_dir / "custom.css",
			cfg_colors=cfg.colors,
			cfg_css_vars=cfg.css_vars,
			ops=ops,
			dry_run=args.dry_run,
			workspace_root=workspace_root,
			backup_root=backup_root,
		)
		# Frontend public (dev) path: /static/custom.css -> <target-dir>/static/static/custom.css
		if not args.no_frontend_static and FRONTEND_PUBLIC_STATIC_DIR.exists():
			write_custom_css(
				dst=FRONTEND_PUBLIC_STATIC_DIR / "custom.css",
				cfg_colors=cfg.colors,
				cfg_css_vars=cfg.css_vars,
				ops=ops,
				dry_run=args.dry_run,
				workspace_root=workspace_root,
				backup_root=backup_root,
			)

	# Optional WEBUI_FAVICON_URL override in env.py.
	if cfg.webui_favicon_url:
		patch_text_by_regex(
			env_py,
			pattern=r"WEBUI_FAVICON_URL\s*=\s*['\"][^'\"]+['\"]",
			repl=f"WEBUI_FAVICON_URL = {json.dumps(cfg.webui_favicon_url)}",
			ops=ops,
			dry_run=args.dry_run,
			strict=False,
			workspace_root=workspace_root,
			backup_root=backup_root,
		)

	# 6) Hard-coded UI snippets (notifications/title/translate CTA/userlist)
	text_replacements = build_replacements_for_app_name(app_name)
	# Bullet replacement and some other fragments are safe and non-URL.
	apply_text_replacement_set_in_tree(
		source_root=FRONTEND_DIR,
		replacements=text_replacements,
		ops=ops,
		dry_run=args.dry_run,
		strict=False,
		workspace_root=workspace_root,
		backup_root=backup_root,
		only_exts=[".svelte", ".ts", ".js"],
	)

	# Dynamic PWA manifest endpoint (/manifest.json) uses hard-coded background_color.
	main_py = BACKEND_DIR / "main.py"
	if main_py.exists():
		patch_text_by_regex(
			main_py,
			pattern=r"'background_color'\s*:\s*'#[0-9a-fA-F]{6}'",
			repl=f"'background_color': {json.dumps(cfg.colors['primaryColor'])}",
			ops=ops,
			dry_run=args.dry_run,
			strict=False,
			workspace_root=workspace_root,
			backup_root=backup_root,
			flags=0,
		)

	# Patch that one file precisely to reduce accidental matches.
	user_list = FRONTEND_DIR / "lib" / "components" / "admin" / "Users" / "UserList.svelte"
	if user_list.exists() and USER_LIST_MARKDOWN_NEEDLE in _read_text(user_list):
		user_new = USER_LIST_MARKDOWN_NEEDLE.replace(OLD_BRAND, app_name)
		replace_in_text(
			user_list,
			replacements=[(USER_LIST_MARKDOWN_NEEDLE, user_new)],
			ops=ops,
			dry_run=args.dry_run,
			strict=args.strict,
			workspace_root=workspace_root,
			backup_root=backup_root,
		)

	# 7) i18n: update translation.json keys/values AND $i18n.t call arguments
	# Update translation.json first.
	locales_dir = FRONTEND_DIR / "lib" / "i18n" / "locales"
	locale_files = list(locales_dir.rglob("translation.json"))
	for lp in locale_files:
		replace_json_branding(
			json_path=lp,
			app_name=app_name,
			ops=ops,
			dry_run=args.dry_run,
			strict=False,
			workspace_root=workspace_root,
			backup_root=backup_root,
		)

	# Update callsite string literals for i18n.t('...').
	# We do it by exact old phrase -> new phrase replacement.
	i18n_repls = i18n_phrase_replacements(app_name)

	for file_path in FRONTEND_DIR.rglob("*"):
		if not file_path.is_file() or file_path.suffix.lower() not in [".svelte", ".ts", ".js"]:
			continue
		text = None
		try:
			text = _read_text(file_path)
		except Exception:
			continue
		if OLD_BRAND not in text:
			continue

		# Only patch exact i18n phrases.
		to_apply: List[Tuple[str, str]] = []
		for old_phrase, new_phrase in i18n_repls.items():
			if old_phrase in text:
				to_apply.append((old_phrase, new_phrase))
		if to_apply:
			replace_in_text(
				file_path=file_path,
				replacements=to_apply,
				ops=ops,
				dry_run=args.dry_run,
				strict=False,
				workspace_root=workspace_root,
				backup_root=backup_root,
			)

	# 8) About/attribution (company/link) - kept minimal and deterministic.
	about_svelte = FRONTEND_DIR / "lib" / "components" / "chat" / "Settings" / "About.svelte"
	if about_svelte.exists():
		# License block (company and legal attribution) is controlled separately.
		if not cfg.attribution.get("keepLicenseBlock", True):
			# Replace company name text and the openwebui.com link.
			company_value = cfg.copyright_owner or cfg.company_name
			if company_value and "Open WebUI Inc." in _read_text(about_svelte):
				replace_in_text(
					about_svelte,
					replacements=[("Open WebUI Inc.", company_value)],
					ops=ops,
					dry_run=args.dry_run,
					strict=False,
					workspace_root=workspace_root,
					backup_root=backup_root,
				)
			if cfg.links.get("website") and "https://openwebui.com" in _read_text(about_svelte):
				replace_in_text(
					about_svelte,
					replacements=[("https://openwebui.com", cfg.links["website"])],
					ops=ops,
					dry_run=args.dry_run,
					strict=False,
					workspace_root=workspace_root,
					backup_root=backup_root,
				)

		# Community links/shields are controlled separately by keepCommunityLinks.
		if not cfg.attribution.get("keepCommunityLinks", True):
			about_text = _read_text(about_svelte)
			# Discord invite
			if cfg.links.get("discord") and "https://discord.gg/5rJgQTnV4s" in about_text:
				replace_in_text(
					about_svelte,
					replacements=[("https://discord.gg/5rJgQTnV4s", cfg.links["discord"])],
					ops=ops,
					dry_run=args.dry_run,
					strict=False,
					workspace_root=workspace_root,
					backup_root=backup_root,
				)

			# Twitter/X
			twitter_handle = cfg.links.get("twitterHandle")
			if twitter_handle and "https://twitter.com/OpenWebUI" in about_text:
				replace_in_text(
					about_svelte,
					replacements=[("https://twitter.com/OpenWebUI", f"https://twitter.com/{twitter_handle}")],
					ops=ops,
					dry_run=args.dry_run,
					strict=False,
					workspace_root=workspace_root,
					backup_root=backup_root,
				)
			if twitter_handle and "https://img.shields.io/twitter/follow/OpenWebUI" in about_text:
				replace_in_text(
					about_svelte,
					replacements=[
						(
							"https://img.shields.io/twitter/follow/OpenWebUI",
							f"https://img.shields.io/twitter/follow/{twitter_handle}",
						)
					],
					ops=ops,
					dry_run=args.dry_run,
					strict=False,
					workspace_root=workspace_root,
					backup_root=backup_root,
				)

			# GitHub repo (link + stars badge)
			if cfg.links.get("githubUrl"):
				gh_url = cfg.links["githubUrl"].rstrip("/")
				gh_path = None
				m = re.search(r"https?://github\\.com/([^/]+/[^/]+)$", gh_url)
				if m:
					gh_path = m.group(1)

				if gh_path:
					old_repo = "open-webui/open-webui"
					old_href = "https://github.com/open-webui/open-webui"
					old_badge_prefix = f"https://img.shields.io/github/stars/{old_repo}"
					new_href = f"https://github.com/{gh_path}"
					new_badge_prefix = f"https://img.shields.io/github/stars/{gh_path}"

					if old_href in about_text:
						replace_in_text(
							about_svelte,
							replacements=[(old_href, new_href)],
							ops=ops,
							dry_run=args.dry_run,
							strict=False,
							workspace_root=workspace_root,
							backup_root=backup_root,
						)
					if old_badge_prefix in about_text:
						replace_in_text(
							about_svelte,
							replacements=[(old_badge_prefix, new_badge_prefix)],
							ops=ops,
							dry_run=args.dry_run,
							strict=False,
							workspace_root=workspace_root,
							backup_root=backup_root,
						)

	# 9) Report
	report_lines: List[str] = []
	report_lines.append("# Branding report")
	report_lines.append("")
	report_lines.append(f"- Timestamp: {datetime.now().isoformat(timespec='seconds')}")
	report_lines.append(f"- Config: {cfg.path}")
	report_lines.append(f"- App name: {cfg.app_name}")
	report_lines.append(f"- Backend static dir: {static_dir}")
	if not args.no_frontend_static:
		report_lines.append(f"- Frontend public dir: {FRONTEND_PUBLIC_DIR}")
		report_lines.append(f"- Frontend public static dir: {FRONTEND_PUBLIC_STATIC_DIR}")
	report_lines.append("")
	report_lines.append("## Operations")
	report_lines.append("")
	for op in ops:
		typ = op.get("type", "op")
		if typ == "backup":
			report_lines.append(f"- backup: {op.get('file')} -> {op.get('backup')}")
		elif typ == "textReplace":
			report_lines.append(f"- textReplace: {op.get('file')}")
		elif typ == "regexPatch":
			report_lines.append(f"- regexPatch: {op.get('file')}")
		elif typ == "jsonBranding":
			report_lines.append(f"- jsonBranding: {op.get('file')}")
		elif typ == "assetCopy":
			report_lines.append(f"- assetCopy: {op.get('src')} -> {op.get('dst')}")
		elif typ == "assetSkip":
			if op.get("dstDirMissing"):
				report_lines.append(f"- assetSkip: missing dir {op.get('dstDirMissing')} (file {op.get('file')})")
		elif typ == "cssWrite":
			report_lines.append(f"- cssWrite: {op.get('file')}{' (dry-run)' if op.get('dryRun') else ''}")
		else:
			report_lines.append(f"- {typ}: {json.dumps(op, ensure_ascii=False)}")

	if not args.dry_run:
		report_path.parent.mkdir(parents=True, exist_ok=True)
		report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

	print(f"Branding applied. Report: {report_path}{' (dry-run)' if args.dry_run else ''}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

