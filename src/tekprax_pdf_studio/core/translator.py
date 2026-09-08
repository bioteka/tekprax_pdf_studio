from __future__ import annotations

from pathlib import Path
import re
import shutil

import fitz
from deep_translator import GoogleTranslator


LANGUAGES = {
    "Português": "pt",
    "Inglês": "en",
    "Espanhol": "es",
    "Francês": "fr",
    "Alemão": "de",
    "Italiano": "it",
}


def _chunk_text(text: str, max_chars: int = 3500) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            if len(sentence) <= max_chars:
                current = sentence
            else:
                for i in range(0, len(sentence), max_chars):
                    chunks.append(sentence[i:i + max_chars])
                current = ""
    if current:
        chunks.append(current)
    return chunks


def _translate_text(text: str, target: str) -> str:
    chunks = _chunk_text(text)
    if not chunks:
        return ""
    translator = GoogleTranslator(source="auto", target=target)
    translated = []
    for chunk in chunks:
        translated.append(translator.translate(chunk))
    return " ".join(translated)


def translate_pdf(input_pdf: str | Path, output_pdf: str | Path, target_language: str) -> Path:
    """Translate searchable text blocks while keeping the original PDF pages/images.

    The layout is preserved approximately. Text blocks are redacted and rewritten
    inside their original rectangles using a built-in PDF font.
    """
    input_pdf = Path(input_pdf)
    output_pdf = Path(output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_pdf, output_pdf)

    doc = fitz.open(str(output_pdf))
    try:
        any_text = False
        for page in doc:
            blocks = page.get_text("blocks")
            work: list[tuple[fitz.Rect, str]] = []
            for block in blocks:
                x0, y0, x1, y1, text, *_ = block
                text = (text or "").strip()
                if not text:
                    continue
                any_text = True
                rect = fitz.Rect(x0, y0, x1, y1)
                translated = _translate_text(text, target_language)
                if translated:
                    work.append((rect, translated))
                    page.add_redact_annot(rect, fill=(1, 1, 1))

            if work:
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
                for rect, translated in work:
                    fontsize = 10.5
                    result = -1
                    while fontsize >= 5.5 and result < 0:
                        result = page.insert_textbox(
                            rect,
                            translated,
                            fontname="helv",
                            fontsize=fontsize,
                            color=(0, 0, 0),
                            align=fitz.TEXT_ALIGN_LEFT,
                        )
                        if result < 0:
                            fontsize -= 0.7

        if not any_text:
            raise RuntimeError(
                "Este PDF não possui texto pesquisável. Faça OCR antes de traduzir."
            )

        temp = output_pdf.with_name(output_pdf.stem + "_tmp.pdf")
        doc.save(str(temp), garbage=4, clean=True, deflate=True)
    finally:
        doc.close()

    temp.replace(output_pdf)
    return output_pdf
