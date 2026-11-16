"""Tests for upgrade-guard-helper using small fixture packages."""

from __future__ import annotations

from pathlib import Path

from upgrade_guard_helper.cli import main
from upgrade_guard_helper.compare import compare_trees
from upgrade_guard_helper.extract import extract_js, extract_python

FIXTURES = Path(__file__).parent / "fixtures"


def test_python_knob_defaults_change():
    old = FIXTURES / "python" / "old"
    new = FIXTURES / "python" / "new"
    result = compare_trees(old, new, "old", "new")
    by_name = {c.name: c for c in result.changes}
    assert by_name["TIMEOUT"].kind == "changed"
    assert by_name["TIMEOUT"].old_value == "5"
    assert by_name["TIMEOUT"].new_value == "10"
    assert by_name["request(timeout)"].old_value == "5.0"
    assert by_name["request(timeout)"].new_value == "10.0"
    assert by_name["Client.retries"].old_value == "3"
    assert by_name["Client.retries"].new_value == "5"
    assert by_name["Client(timeout)"].old_value == "5.0"
    assert by_name["Client(timeout)"].new_value == "10.0"
    assert by_name["Client(backoff)"].kind == "added"
    assert by_name["Client(backoff)"].new_value == "0.2"
    # Unchanged knobs must not appear.
    assert "DEFAULT_RETRIES" not in by_name
    assert "request(retries)" not in by_name
    assert "Client(verify)" not in by_name
    report = result.report()
    assert "TIMEOUT: 5 -> 10" in report
    assert "DEFAULT_RETRIES" not in report


def test_js_knob_defaults_change():
    old = FIXTURES / "js" / "old"
    new = FIXTURES / "js" / "new"
    result = compare_trees(old, new, "js-old", "js-new")
    by_name = {c.name: c for c in result.changes}
    assert by_name["TIMEOUT"].old_value == "5"
    assert by_name["TIMEOUT"].new_value == "15"
    assert by_name["defaultConfig.timeout"].new_value == "15.0"
    assert by_name["defaultConfig.nested.size"].old_value == "8"
    assert by_name["defaultConfig.nested.size"].new_value == "16"
    assert by_name["request(timeout)"].old_value == "5.0"
    assert by_name["request(timeout)"].new_value == "15.0"
    assert "defaultConfig.retries" not in by_name
    assert "connect(delay)" not in by_name


def test_extract_python_skips_non_literals():
    knobs = extract_python("def f(x=os.getenv('T', '1')):\n    return x\nTIMEOUT = 1 + y\n")
    names = {k.name for k in knobs}
    assert "f(x)" not in names
    assert "TIMEOUT" not in names


def test_extract_js_default_params():
    knobs = extract_js("export const load = (retries = 2, timeout = 1.5) => retries;\n")
    values = {k.name: k.value for k in knobs}
    assert values["load(retries)"] == "2"
    assert values["load(timeout)"] == "1.5"


def test_identical_trees_report_no_changes():
    old = FIXTURES / "python" / "old"
    result = compare_trees(old, old, "a", "a")
    assert result.changes == []
    assert "No knob defaults changed" in result.report()


def test_cli_local_trees_and_write(tmp_path, capsys):
    old = FIXTURES / "python" / "old"
    new = FIXTURES / "python" / "new"
    dest = tmp_path / "knobs.tidy.txt"
    assert main(["--old", str(old), "--new", str(new), "--write", str(dest)]) == 1
    # Source fixtures must be untouched.
    assert "TIMEOUT = 5" in (old / "demo_pkg" / "__init__.py").read_text()
    text = dest.read_text(encoding="utf-8")
    assert "TIMEOUT: 5 -> 10" in text
    assert "Wrote" in capsys.readouterr().err


def test_cli_identical_exit_zero(capsys):
    old = FIXTURES / "python" / "old"
    assert main(["--old", str(old), "--new", str(old)]) == 0
    assert "No knob defaults changed" in capsys.readouterr().out
