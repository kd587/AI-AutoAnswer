# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
for package in ('windows_mcp', 'fastmcp', 'dxcam', 'comtypes'):
    package_datas, package_bins, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_bins
    hiddenimports += package_hidden

a = Analysis(['scripts/mcp_server.py'], pathex=['.'], binaries=binaries,
             datas=datas, hiddenimports=hiddenimports, hookspath=[],
             runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name='windows-mcp-server', debug=False, strip=False,
          upx=False, console=True)
