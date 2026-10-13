# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from pathlib import Path
import os
import sys

datas = []
binaries = []
hiddenimports = []
for package in ('paddleocr', 'paddle', 'cv2', 'pywinauto', 'keyring'):
    try:
        package_datas, package_bins, package_hidden = collect_all(package)
        datas += package_datas
        binaries += package_bins
        hiddenimports += package_hidden
    except Exception:
        pass

# PyInstaller's paddle hook omits this runtime dependency on Windows.
mklml = Path(sys.prefix) / 'Lib' / 'site-packages' / 'paddle' / 'libs' / 'mklml.dll'
if mklml.is_file():
    binaries.append((str(mklml), 'paddle/libs'))

models = Path.home() / '.paddleocr' / 'whl'
model_paths = {
    'det': models / 'det' / 'ch' / 'ch_PP-OCRv4_det_infer',
    'rec': models / 'rec' / 'ch' / 'ch_PP-OCRv4_rec_infer',
    'cls': models / 'cls' / 'ch_ppocr_mobile_v2.0_cls_infer',
}
for kind, source in model_paths.items():
    if not (source / 'inference.pdmodel').is_file():
        raise RuntimeError(f'Missing OCR model: {source}. Run OCR once before building.')
    datas.append((str(source), f'ocr_models/{kind}'))

a = Analysis(['main.py'], pathex=['.'], binaries=binaries, datas=datas,
             hiddenimports=hiddenimports, hookspath=[], runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
if os.environ.get('AI_AUTOANSWER_ONEFILE') == '1':
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='AI_AutoAnswer',
              debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
              console=False)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='AI_AutoAnswer',
              debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
              console=False)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False,
                   name='AI_AutoAnswer')
