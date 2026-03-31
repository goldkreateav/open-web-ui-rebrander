from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


OLD_BRAND = "Open WebUI"


# Phrases that appear in i18n translation keys AND are passed to $i18n.t("...").
# We replace them by building a new phrase via string replacement of OLD_BRAND -> appName.
#
# NOTE: Values in locales/en-US/translation.json are often empty (i.e. the key itself is used as display string),
# so we must update both translation.json keys/values and the $i18n.t() callsite arguments.
I18N_PHRASES_WITH_OLD_BRAND: List[str] = [
	"CORS must be properly configured by the provider to allow requests from Open WebUI.",
	"Discover how to use Open WebUI and seek support from the community.",
	"Do you want to sync your usage stats with Open WebUI Community?",
	"Made by Open WebUI Community",
	"MCP support is experimental and its specification changes often, which can lead to incompatibilities. OpenAPI specification support is directly maintained by the Open WebUI team, making it the more reliable option for compatibility.",
	"Open WebUI can use tools provided by any OpenAPI server.",
	"Open WebUI uses faster-whisper internally.",
	"Open WebUI uses SpeechT5 and CMU Arctic speaker embeddings.",
	"Open WebUI version",
	"Open WebUI version (v{{OPEN_WEBUI_VERSION}}) is lower than required version (v{{REQUIRED_VERSION}})",
	"Participate in community leaderboards and evaluations! Syncing aggregated usage stats helps drive research and improvements to Open WebUI. Your privacy is paramount: no message content is ever shared.",
	"Redirecting you to Open WebUI Community",
	"Share to Open WebUI Community",
	"Your entire contribution will go directly to the plugin developer; Open WebUI does not take any percentage. However, the chosen funding platform might have its own fees.",
]


# Non-i18n hard-coded fragments.
#
# These are chosen to be narrow enough to avoid accidental replacements of URLs/domains.
HARD_CODED_REPLACEMENTS = [
	{
		"needle": " • Open WebUI",
		"desc": "Notification titles and page titles",
	},
	{
		"needle": "Help us translate Open WebUI!",
		"desc": "Manual translation call-to-action",
	},
]


USER_LIST_MARKDOWN_NEEDLE = (
	"Open WebUI is completely free to use as-is, with no restrictions or hidden limits, and we'd love to keep it that way."
)


def build_replacements_for_app_name(app_name: str) -> Dict[str, str]:
	"""
	Builds a dict of needle->replacement for hard-coded fragments where we can safely
	replace Open WebUI with the configured app name.
	"""
	repl: Dict[str, str] = {}
	for item in HARD_CODED_REPLACEMENTS:
		needle = item["needle"]
		# Only replace the OLD_BRAND part, keep surrounding punctuation/spaces intact.
		repl[needle] = needle.replace(OLD_BRAND, app_name)

	return repl


def i18n_phrase_replacements(app_name: str) -> Dict[str, str]:
	return {old: old.replace(OLD_BRAND, app_name) for old in I18N_PHRASES_WITH_OLD_BRAND}

