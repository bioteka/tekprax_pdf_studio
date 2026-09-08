@echo off
setlocal
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pyinstaller --clean TekPraxPDFStudio.spec

echo.
echo Build concluido em dist\TekPraxPDFStudio\
pause
