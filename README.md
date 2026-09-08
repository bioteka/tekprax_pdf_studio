# TekPrax PDF Studio Desktop

Aplicativo desktop multiplataforma, pronto para GitHub, com as funções exibidas no PDF Studio da TekPrax:

- Juntar PDFs
- Dividir PDF em páginas e gerar ZIP
- Organizar, excluir e girar páginas
- Otimizar PDF
- Converter DOC/DOCX para PDF
- Converter PDF para DOCX editável, com OCR opcional para PDFs digitalizados
- Converter PPT/PPTX para PDF
- Traduzir PDF textual preservando imagens e o layout de forma aproximada

## Tecnologias

- Python 3.11+
- PySide6 (interface desktop)
- pypdf / PyMuPDF
- pdf2docx
- pytesseract (OCR opcional)
- deep-translator
- LibreOffice (conversões DOC/DOCX/PPT/PPTX -> PDF)

## Executar pelo código-fonte

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
python -m tekprax_pdf_studio
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m tekprax_pdf_studio
```

## Dependências externas

### LibreOffice

Necessário para DOC/DOCX -> PDF e PPT/PPTX -> PDF.

O aplicativo procura automaticamente o executável do LibreOffice em locais comuns e também no `PATH`.

### Tesseract OCR

Opcional. É usado como fallback quando o PDF não possui texto pesquisável.

- Windows: instale o Tesseract OCR e mantenha-o em `C:\Program Files\Tesseract-OCR\tesseract.exe` ou no `PATH`.
- Linux: instale o pacote `tesseract-ocr`.
- macOS: instale com Homebrew (`brew install tesseract`).

## Gerar executável localmente

```bash
pip install -r requirements-dev.txt
pyinstaller TekPraxPDFStudio.spec
```

O resultado ficará em `dist/TekPraxPDFStudio/`.

## GitHub Actions

O workflow `.github/workflows/build.yml` gera um instalador `.exe` e pacote portátil para Windows, além de pacotes para macOS e Linux, sempre que houver push de tag `v*` ou execução manual.

## Instalador do Windows

O arquivo `installer/windows.iss` cria um instalador com Inno Setup a partir da pasta gerada pelo PyInstaller.

## Observações sobre fidelidade

Conversões entre formatos de escritório e PDF podem variar conforme fontes instaladas e recursos do arquivo original. A tradução de PDF preserva as páginas e imagens, mas substitui blocos de texto de forma heurística; documentos muito complexos podem exigir revisão.

## Licença

MIT. Veja `LICENSE`.
