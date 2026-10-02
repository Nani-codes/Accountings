# PyInstaller spec for the Accountings Tally Connector.
# Build on Windows (PyInstaller is not a cross-compiler):
#   pip install -e . pyinstaller
#   pyinstaller build.spec
# Output: dist/AccountingsConnector.exe  (single-file, console app)

block_cipher = None

a = Analysis(
    ["connector/main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    # Ensure third-party deps are picked up even if PyInstaller's static
    # analysis misses a lazy import.
    hiddenimports=[
        "httpx",
        "websockets",
        "websockets.legacy",
        "websockets.legacy.client",
        "pydantic",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "pytest_asyncio", "pytest_cov"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AccountingsConnector",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # To code-sign later, build unsigned here and sign dist/AccountingsConnector.exe
    # in CI with signtool (see .github/workflows/connector-release.yml).
)
