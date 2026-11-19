import json

from fieldcore.config.manager import ConfigManager


def test_load_persists_merged_defaults_to_disk(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"existing_section": {"a": 1}}))

    defaults = {
        "existing_section": {"a": 1, "b": 2},
        "new_section": {"c": 3},
    }

    ConfigManager(config_path, default_config=defaults)

    on_disk = json.loads(config_path.read_text())
    assert on_disk == {
        "existing_section": {"a": 1, "b": 2},
        "new_section": {"c": 3},
    }


def test_load_does_not_rewrite_file_when_nothing_missing(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"section": {"a": 1}}))
    mtime_before = config_path.stat().st_mtime_ns

    ConfigManager(config_path, default_config={"section": {"a": 1}})

    assert config_path.stat().st_mtime_ns == mtime_before


def test_reload_picks_up_new_defaults_added_after_first_load(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"section": {"a": 1}}))

    manager = ConfigManager(config_path, default_config={"section": {"a": 1}})
    assert manager.get_section("new_section") is None

    # Simulate a code upgrade that introduces a new module/section default,
    # without the on-disk config having been touched in between.
    manager._default_config["new_section"] = {"c": 3}
    manager.load()

    assert manager.get_section("new_section") == {"c": 3}
    on_disk = json.loads(config_path.read_text())
    assert on_disk["new_section"] == {"c": 3}
