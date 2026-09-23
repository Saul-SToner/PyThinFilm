import sys

from app import main


def test_optiland_configuration_prefers_project_checkout(monkeypatch, tmp_path):
    project = tmp_path / "project"
    checkout = project / "optiland" / "optiland"
    checkout.mkdir(parents=True)
    (checkout / "__init__.py").touch()
    monkeypatch.setattr(main, "PYTHINFILM_ROOT", project)
    monkeypatch.delenv("THINFILM_OPTILAND_ROOT", raising=False)
    monkeypatch.delenv("THINFILM_OPTILAND_PYTHON", raising=False)

    root, python, script = main._optiland_configuration()

    assert root == project / "optiland"
    assert python == main.Path(sys.executable).resolve()
    assert script == project / "experiments" / "optiland_real_material_ar_comparison.py"


def test_optiland_configuration_honors_explicit_paths(monkeypatch, tmp_path):
    checkout = tmp_path / "custom"
    python = tmp_path / "runtime" / "python.exe"
    monkeypatch.setenv("THINFILM_OPTILAND_ROOT", str(checkout))
    monkeypatch.setenv("THINFILM_OPTILAND_PYTHON", str(python))

    root, executable, _ = main._optiland_configuration()

    assert root == checkout
    assert executable == python


def test_optiland_configuration_retains_sibling_fallback(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(main, "PYTHINFILM_ROOT", project)
    monkeypatch.delenv("THINFILM_OPTILAND_ROOT", raising=False)
    monkeypatch.delenv("THINFILM_OPTILAND_PYTHON", raising=False)

    root, python, _ = main._optiland_configuration()

    assert root == tmp_path / "optiland"
    assert python == root / ".venv" / "Scripts" / "python.exe"
