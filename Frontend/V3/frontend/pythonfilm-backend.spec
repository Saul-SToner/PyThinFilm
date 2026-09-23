# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


frontend = Path.cwd().resolve()
project = frontend.parents[2]
optiland_checkout = project / "optiland"
backend = project / "Frontend" / "V3" / "backend"

datas = [
    (str(project / "data"), "data"),
    (str(project / "web3d" / "public"), "web3d/public"),
    (str(project / "docs" / "evidence" / "rough_absorbing_surface_topic_v1_baseline_spectrum.csv"), "docs/evidence"),
    (str(frontend / "src" / "assets" / "materials" / "app_materials_metadata.csv"), "materials"),
    (str(optiland_checkout / "optiland"), "optiland/optiland"),
]
for name in (
    "optiland_draft_render.py", "optiland_engineering_nsq.py", "optiland_sampling.py",
    "optiland_poc.py", "optiland_ar_comparison.py", "optiland_real_material_ar_comparison.py",
):
    datas.append((str(project / "experiments" / name), "experiments"))
datas += collect_data_files("matplotlib")
datas += collect_data_files("optiland")
datas += collect_data_files("rcwa")
datas += collect_data_files("wptherml")

hiddenimports = [
    "experiments.optiland_draft_render", "experiments.optiland_real_material_ar_comparison",
    "experiments.optiland_engineering_nsq", "experiments.optiland_sampling",
    "experiments.optiland_poc", "experiments.optiland_ar_comparison",
    "rcwa", "wptherml",
]
hiddenimports += collect_submodules("optiland", on_error="warn once")

analysis = Analysis(
    [str(backend / "run.py")],
    pathex=[str(project), str(backend), str(optiland_checkout)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["optiland_gui", "torch", "tensorflow", "pytest"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="thinfilm-backend",
    console=True,
    contents_directory=".",
)
coll = COLLECT(exe, analysis.binaries, analysis.datas, name="thinfilm-backend")
