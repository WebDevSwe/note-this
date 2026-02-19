from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
NOTES_DIR = BASE_DIR / "notes"
TEMPLATES_DIR = BASE_DIR / "templates"
SETTINGS_DIR = BASE_DIR / "settings"
TOKENS_CONFIG_PATH = SETTINGS_DIR / "tokens.json"
TOOLTIPS_CONFIG_PATH = SETTINGS_DIR / "tooltips.json"
ABOUT_MARKDOWN_PATH = SETTINGS_DIR / "about_notethis.md"
USER_SETTINGS_PATH = SETTINGS_DIR / "user_settings.json"

FILE_PREFIX = "note_A"
FILE_SUFFIX = ".md"
AUTOSAVE_INTERVAL_MINUTES = 5
AUTOSAVE_INTERVAL_MS = AUTOSAVE_INTERVAL_MINUTES * 60_000
