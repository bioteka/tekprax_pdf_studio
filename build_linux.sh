#!/usr/bin/env bash
set -euo pipefail
python3 -m pip install --upgrade pip
pip install -r requirements-dev.txt
pyinstaller --clean TekPraxPDFStudio.spec
echo "Build concluído em dist/TekPraxPDFStudio/"
