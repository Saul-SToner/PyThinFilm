# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

datas = [
    ('data', 'data'),
    ('thinfilm', 'thinfilm'),
    ('guided_grating', 'guided_grating'),
    ('cases', 'cases'),
]

hiddenimports = [
    'numpy',
    'scipy',
    'scipy.interpolate',
    'scipy.optimize',
    'matplotlib',
    'matplotlib.pyplot',
    'pandas',
    'plotly',
    'thinfilm',
    'thinfilm.tmm',
    'thinfilm.materials',
    'thinfilm.validation',
    'thinfilm.education',
    'thinfilm.api',
    'guided_grating',
    'guided_grating.emt',
]

a = Analysis(
    ['run_teaching_demo.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PyThinFilm_TeachingDemo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PyThinFilm_v1.1_National',
)
