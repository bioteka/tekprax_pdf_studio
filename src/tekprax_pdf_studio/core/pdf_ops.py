from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import zipfile

import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter


def merge_pdfs(inputs: list[str | Path], output: str | Path) -> Path:
    if len(inputs) < 2:
        raise ValueError("Selecione pelo menos dois PDFs.")

    writer = PdfWriter()
    for file in inputs:
        writer.append(str(file))

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as fh:
        writer.write(fh)
    writer.close()
    return output


def split_pdf_to_zip(input_pdf: str | Path, output_zip: str | Path) -> Path:
    reader = PdfReader(str(input_pdf))
    output_zip = Path(output_zip)
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="tekprax_split_") as tmp:
        tmpdir = Path(tmp)
        created: list[Path] = []
        for i, page in enumerate(reader.pages, start=1):
            writer = PdfWriter()
            writer.add_page(page)
            target = tmpdir / f"pagina_{i:03d}.pdf"
            with target.open("wb") as fh:
                writer.write(fh)
            writer.close()
            created.append(target)

        with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file in created:
                zf.write(file, arcname=file.name)

    return output_zip


def organize_pdf(
    input_pdf: str | Path,
    output_pdf: str | Path,
    plan: list[tuple[int, int]],
) -> Path:
    """plan: [(original_page_index_zero_based, clockwise_rotation_degrees), ...]"""
    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()

    for page_index, rotation in plan:
        page = reader.pages[page_index]
        if rotation % 360:
            page.rotate(rotation % 360)
        writer.add_page(page)

    output_pdf = Path(output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as fh:
        writer.write(fh)
    writer.close()
    return output_pdf


def optimize_pdf(input_pdf: str | Path, output_pdf: str | Path) -> tuple[Path, int, int]:
    input_pdf = Path(input_pdf)
    output_pdf = Path(output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    before = input_pdf.stat().st_size
    doc = fitz.open(str(input_pdf))
    try:
        doc.save(
            str(output_pdf),
            garbage=4,
            clean=True,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            linear=True,
        )
    finally:
        doc.close()

    after = output_pdf.stat().st_size
    return output_pdf, before, after


def copy_pdf(input_pdf: str | Path, output_pdf: str | Path) -> Path:
    output_pdf = Path(output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_pdf, output_pdf)
    return output_pdf
