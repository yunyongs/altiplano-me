"""Tests for build_config.py — .env parsing, defaults, and template rendering."""
import pathlib

from build_config import apply_defaults, load_env, render


# ---------------------------------------------------------------------------
# load_env
# ---------------------------------------------------------------------------

class TestLoadEnv:
    def test_parses_key_value_pairs(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\nBAZ=123\n")
        assert load_env(env_file) == {"FOO": "bar", "BAZ": "123"}

    def test_strips_whitespace(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("  KEY  =  value  \n")
        assert load_env(env_file) == {"KEY": "value"}

    def test_skips_comments(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\nKEY=val\n")
        assert load_env(env_file) == {"KEY": "val"}

    def test_skips_blank_lines(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("\n\nKEY=val\n\n")
        assert load_env(env_file) == {"KEY": "val"}

    def test_skips_lines_without_equals(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("NOEQ\nKEY=val\n")
        assert load_env(env_file) == {"KEY": "val"}

    def test_value_may_contain_equals(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("URL=https://example.com?a=1&b=2\n")
        assert load_env(env_file) == {"URL": "https://example.com?a=1&b=2"}

    def test_empty_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("")
        assert load_env(env_file) == {}

    def test_nonexistent_file(self, tmp_path):
        assert load_env(tmp_path / "missing") == {}


# ---------------------------------------------------------------------------
# apply_defaults
# ---------------------------------------------------------------------------

class TestApplyDefaults:
    def test_sets_defaults_on_empty_dict(self):
        env = {}
        apply_defaults(env)
        assert env == {
            "DEFAULT_COMPONENT": "C1",
            "ROW_START": "1",
            "ROW_END": "9999",
        }

    def test_preserves_existing_keys(self):
        env = {"DEFAULT_COMPONENT": "C2", "ROW_START": "10"}
        apply_defaults(env)
        assert env["DEFAULT_COMPONENT"] == "C2"
        assert env["ROW_START"] == "10"
        assert env["ROW_END"] == "9999"


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

class TestRender:
    def test_replaces_known_placeholders(self):
        tpl = "const x = '${FOO}';"
        assert render(tpl, {"FOO": "bar"}) == "const x = 'bar';"

    def test_unknown_placeholders_become_empty(self):
        tpl = "val = ${MISSING};"
        assert render(tpl, {}) == "val = ;"

    def test_no_placeholders_unchanged(self):
        tpl = "hello world"
        assert render(tpl, {"FOO": "bar"}) == "hello world"

    def test_multiple_placeholders(self):
        tpl = "${A} and ${B}"
        assert render(tpl, {"A": "1", "B": "2"}) == "1 and 2"
