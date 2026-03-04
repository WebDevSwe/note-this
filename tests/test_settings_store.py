from pathlib import Path

from notethis import settings_store


def test_load_tooltips_config_default(monkeypatch, tmp_path: Path) -> None:
    tooltips_path = tmp_path / "tooltips.json"
    monkeypatch.setattr(settings_store, "TOOLTIPS_CONFIG_PATH", tooltips_path)
    settings_store._tooltips_cache = None

    config = settings_store.load_tooltips_config()
    assert config["enabled"] is False
    assert isinstance(config["buttons"], dict)


def test_save_and_load_user_settings(monkeypatch, tmp_path: Path) -> None:
    settings_path = tmp_path / "user_settings.json"
    monkeypatch.setattr(settings_store, "USER_SETTINGS_PATH", settings_path)
    settings_store._user_settings_cache = None

    settings_store.save_user_settings({"theme_mode": "dark"})
    settings_store._user_settings_cache = None

    loaded = settings_store.load_user_settings()
    assert loaded["theme_mode"] == "dark"
