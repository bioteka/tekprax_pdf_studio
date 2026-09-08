from __future__ import annotations

import os
import sys
from pathlib import Path

import fitz
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QCursor, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .core.pdf_ops import merge_pdfs, split_pdf_to_zip, organize_pdf, optimize_pdf
from .core.converters import office_to_pdf, pdf_to_docx
from .core.translator import LANGUAGES, translate_pdf


APP_TITLE = "TekPrax PDF Studio"


class ToolCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, description: str, accent: str, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setObjectName("ToolCard")
        self.setStyleSheet(
            f"""
            QFrame#ToolCard {{
                background: white;
                border: 1px solid #dbe5ef;
                border-top: 4px solid {accent};
                border-radius: 13px;
            }}
            QFrame#ToolCard:hover {{
                background: #f8fbff;
                border-color: #b9cee2;
                border-top: 4px solid {accent};
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 13, 16, 14)
        layout.setSpacing(6)

        t = QLabel(title)
        t.setStyleSheet("font-size: 16px; font-weight: 800; color: #0b1f33; border: none;")
        d = QLabel(description)
        d.setWordWrap(True)
        d.setStyleSheet("font-size: 12px; color: #607089; border: none;")
        layout.addWidget(t)
        layout.addWidget(d)
        layout.addStretch(1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class OrganizeDialog(QDialog):
    def __init__(self, pdf_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Organizar páginas")
        self.resize(720, 620)
        self.pdf_path = pdf_path

        root = QVBoxLayout(self)
        info = QLabel("Arraste pela lista usando os botões, exclua páginas ou aplique rotação.")
        info.setWordWrap(True)
        root.addWidget(info)

        self.list = QListWidget()
        self.list.setIconSize(QSize(92, 122))
        self.list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        root.addWidget(self.list, 1)

        controls = QHBoxLayout()
        for label, fn in [
            ("↑ Subir", self.move_up),
            ("↓ Descer", self.move_down),
            ("↶ -90°", lambda: self.rotate(-90)),
            ("↷ +90°", lambda: self.rotate(90)),
            ("Excluir", self.delete_selected),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(fn)
            controls.addWidget(btn)
        root.addLayout(controls)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._load_pages()

    def _load_pages(self):
        doc = fitz.open(self.pdf_path)
        try:
            for i, page in enumerate(doc):
                pix = page.get_pixmap(matrix=fitz.Matrix(0.22, 0.22), alpha=False)
                image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
                item = QListWidgetItem(QIcon(QPixmap.fromImage(image)), f"Página {i + 1}  |  rotação 0°")
                item.setData(Qt.ItemDataRole.UserRole, i)
                item.setData(Qt.ItemDataRole.UserRole + 1, 0)
                item.setSizeHint(QSize(240, 132))
                self.list.addItem(item)
        finally:
            doc.close()

    def move_up(self):
        row = self.list.currentRow()
        if row > 0:
            item = self.list.takeItem(row)
            self.list.insertItem(row - 1, item)
            self.list.setCurrentRow(row - 1)

    def move_down(self):
        row = self.list.currentRow()
        if 0 <= row < self.list.count() - 1:
            item = self.list.takeItem(row)
            self.list.insertItem(row + 1, item)
            self.list.setCurrentRow(row + 1)

    def delete_selected(self):
        row = self.list.currentRow()
        if row >= 0 and self.list.count() > 1:
            self.list.takeItem(row)
        elif self.list.count() <= 1:
            QMessageBox.warning(self, APP_TITLE, "O PDF precisa manter pelo menos uma página.")

    def rotate(self, delta: int):
        item = self.list.currentItem()
        if not item:
            return
        original = int(item.data(Qt.ItemDataRole.UserRole))
        rotation = (int(item.data(Qt.ItemDataRole.UserRole + 1)) + delta) % 360
        item.setData(Qt.ItemDataRole.UserRole + 1, rotation)
        item.setText(f"Página {original + 1}  |  rotação {rotation}°")

    def plan(self) -> list[tuple[int, int]]:
        result = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            result.append(
                (
                    int(item.data(Qt.ItemDataRole.UserRole)),
                    int(item.data(Qt.ItemDataRole.UserRole + 1)),
                )
            )
        return result


class TranslateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Traduzir PDF")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Idioma de destino:"))
        self.combo = QComboBox()
        for name, code in LANGUAGES.items():
            self.combo.addItem(name, code)
        layout.addWidget(self.combo)
        note = QLabel("A tradução usa serviço online e funciona melhor em PDFs com texto pesquisável.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#607089")
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def language_code(self) -> str:
        return str(self.combo.currentData())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1180, 760)
        self.setMinimumSize(920, 640)
        self.setAcceptDrops(True)
        self.current_pdf: str | None = None

        self.setStyleSheet("""
            QMainWindow { background: #eef7fb; }
            QLabel { color: #10233a; }
            QPushButton {
                background: #ffffff;
                color: #0b1f33;
                border: 1px solid #cbd8e5;
                border-radius: 8px;
                padding: 8px 13px;
                font-weight: 700;
            }
            QPushButton:hover { background: #f3f8fc; }
            QProgressBar {
                border: 1px solid #cbd8e5;
                border-radius: 6px;
                text-align: center;
                background: white;
                height: 12px;
            }
            QProgressBar::chunk { background: #0ca678; border-radius: 5px; }
        """)

        outer = QWidget()
        self.setCentralWidget(outer)
        page = QVBoxLayout(outer)
        page.setContentsMargins(18, 18, 18, 18)
        page.setSpacing(14)

        header = QFrame()
        header.setStyleSheet("background:#082d4c; border-radius:14px;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        brand = QLabel("TekPrax")
        brand.setStyleSheet("font-size:23px; font-weight:900; color:#38bdf8;")
        subtitle = QLabel("PDF Studio Desktop")
        subtitle.setStyleSheet("font-size:14px; color:#d7ecf8; margin-left:10px;")
        header_layout.addWidget(brand)
        header_layout.addWidget(subtitle)
        header_layout.addStretch(1)
        page.addWidget(header)

        hero = QFrame()
        hero.setStyleSheet("background:#0d4968; border-radius:16px;")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(20, 16, 20, 16)
        h1 = QLabel("📄  PDF Studio")
        h1.setStyleSheet("font-size:22px; font-weight:900; color:white;")
        h2 = QLabel("Escolha um PDF ou abra diretamente uma das operações profissionais abaixo.")
        h2.setStyleSheet("font-size:12px; color:#d8eef7;")
        hero_layout.addWidget(h1)
        hero_layout.addWidget(h2)
        page.addWidget(hero)

        selector = QFrame()
        selector.setStyleSheet("background:#eaf9ff; border:1px solid #75d5ff; border-radius:14px;")
        s_layout = QHBoxLayout(selector)
        s_layout.setContentsMargins(16, 12, 16, 12)
        text_box = QVBoxLayout()
        title = QLabel("Arquivo selecionado para edição")
        title.setStyleSheet("font-weight:900; font-size:14px;")
        self.file_label = QLabel("Nenhum PDF escolhido. Você também pode arrastar um PDF para esta janela.")
        self.file_label.setStyleSheet("color:#607089; font-size:12px;")
        self.file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text_box.addWidget(title)
        text_box.addWidget(self.file_label)
        choose = QPushButton("📁 Escolher PDF")
        choose.clicked.connect(self.choose_pdf)
        s_layout.addLayout(text_box, 1)
        s_layout.addWidget(choose)
        page.addWidget(selector)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        cards_widget = QWidget()
        cards_widget.setStyleSheet("background:transparent;")
        grid = QGridLayout(cards_widget)
        grid.setSpacing(12)

        cards = [
            ("Juntar PDFs", "Selecione 2 ou mais PDFs e gere um único arquivo.", "#0ea5e9", self.do_merge),
            ("Dividir PDF", "Separe cada página e baixe tudo em um ZIP.", "#7c3aed", self.do_split),
            ("Organizar páginas", "Pré-visualize, reordene, exclua e gire páginas.", "#f59e0b", self.do_organize),
            ("Otimizar PDF", "Reempacote e comprima estruturas sem alterar o conteúdo visual.", "#10b981", self.do_optimize),
            ("DOC / DOCX → PDF", "Converta documentos do Word para PDF via LibreOffice.", "#2563eb", self.do_doc_to_pdf),
            ("PDF → DOC / DOCX", "Reconstrução editável com texto, imagens, tabelas, layout e OCR opcional.", "#db2777", self.do_pdf_to_docx),
            ("PPT / PPTX → PDF", "Converta apresentações para PDF via LibreOffice.", "#ea580c", self.do_ppt_to_pdf),
            ("Traduzir PDF", "Extraia, traduza e gere um novo PDF textual preservando a página original.", "#0891b2", self.do_translate),
        ]

        for idx, (title_, desc, accent, handler) in enumerate(cards):
            card = ToolCard(title_, desc, accent)
            card.clicked.connect(handler)
            grid.addWidget(card, idx // 4, idx % 4)

        scroll.setWidget(cards_widget)
        page.addWidget(scroll, 1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        page.addWidget(self.progress)

        self.status = QLabel("Pronto.")
        self.status.setStyleSheet("color:#5f6f82; padding:2px 4px;")
        page.addWidget(self.status)

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].toLocalFile().lower().endswith(".pdf"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        path = event.mimeData().urls()[0].toLocalFile()
        self.set_pdf(path)
        event.acceptProposedAction()

    def set_pdf(self, path: str):
        self.current_pdf = path
        self.file_label.setText(path)
        self.status.setText(f"PDF selecionado: {Path(path).name}")

    def choose_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Escolher PDF", "", "PDF (*.pdf)")
        if path:
            self.set_pdf(path)

    def ensure_pdf(self) -> str | None:
        if self.current_pdf and Path(self.current_pdf).exists():
            return self.current_pdf
        path, _ = QFileDialog.getOpenFileName(self, "Escolher PDF", "", "PDF (*.pdf)")
        if path:
            self.set_pdf(path)
            return path
        return None

    def busy(self, message: str):
        self.status.setText(message)
        self.progress.setRange(0, 0)
        self.progress.show()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()

    def ready(self, message: str = "Pronto."):
        QApplication.restoreOverrideCursor()
        self.progress.hide()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.status.setText(message)

    def run_action(self, message: str, fn):
        try:
            self.busy(message)
            result = fn()
            self.ready("Concluído.")
            return result
        except Exception as exc:
            self.ready("Ocorreu um erro.")
            QMessageBox.critical(self, APP_TITLE, str(exc))
            return None

    def do_merge(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Selecionar PDFs", "", "PDF (*.pdf)")
        if len(files) < 2:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Salvar PDF unido", "pdf_unido.pdf", "PDF (*.pdf)")
        if not out:
            return
        result = self.run_action("Juntando PDFs...", lambda: merge_pdfs(files, out))
        if result:
            QMessageBox.information(self, APP_TITLE, f"PDF criado com sucesso:\n{result}")

    def do_split(self):
        pdf = self.ensure_pdf()
        if not pdf:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Salvar páginas em ZIP", f"{Path(pdf).stem}_paginas.zip", "ZIP (*.zip)")
        if not out:
            return
        result = self.run_action("Dividindo PDF...", lambda: split_pdf_to_zip(pdf, out))
        if result:
            QMessageBox.information(self, APP_TITLE, f"ZIP criado com sucesso:\n{result}")

    def do_organize(self):
        pdf = self.ensure_pdf()
        if not pdf:
            return
        dlg = OrganizeDialog(pdf, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Salvar PDF organizado", f"{Path(pdf).stem}_organizado.pdf", "PDF (*.pdf)")
        if not out:
            return
        result = self.run_action("Organizando páginas...", lambda: organize_pdf(pdf, out, dlg.plan()))
        if result:
            QMessageBox.information(self, APP_TITLE, f"PDF organizado com sucesso:\n{result}")

    def do_optimize(self):
        pdf = self.ensure_pdf()
        if not pdf:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Salvar PDF otimizado", f"{Path(pdf).stem}_otimizado.pdf", "PDF (*.pdf)")
        if not out:
            return
        result = self.run_action("Otimizando PDF...", lambda: optimize_pdf(pdf, out))
        if result:
            path, before, after = result
            reduction = 0 if before == 0 else (1 - after / before) * 100
            QMessageBox.information(
                self,
                APP_TITLE,
                f"PDF otimizado:\n{path}\n\nAntes: {before/1024/1024:.2f} MB\nDepois: {after/1024/1024:.2f} MB\nRedução: {reduction:.1f}%",
            )

    def do_doc_to_pdf(self):
        inp, _ = QFileDialog.getOpenFileName(self, "Selecionar documento", "", "Documentos (*.doc *.docx)")
        if not inp:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", f"{Path(inp).stem}.pdf", "PDF (*.pdf)")
        if not out:
            return
        result = self.run_action("Convertendo documento para PDF...", lambda: office_to_pdf(inp, out))
        if result:
            QMessageBox.information(self, APP_TITLE, f"PDF criado com sucesso:\n{result}")

    def do_pdf_to_docx(self):
        pdf = self.ensure_pdf()
        if not pdf:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Salvar DOCX", f"{Path(pdf).stem}.docx", "Word (*.docx)")
        if not out:
            return
        result = self.run_action("Convertendo PDF para DOCX...", lambda: pdf_to_docx(pdf, out, True))
        if result:
            path, used_ocr = result
            note = "\nOCR foi usado como fallback." if used_ocr else ""
            QMessageBox.information(self, APP_TITLE, f"DOCX criado com sucesso:\n{path}{note}")

    def do_ppt_to_pdf(self):
        inp, _ = QFileDialog.getOpenFileName(self, "Selecionar apresentação", "", "Apresentações (*.ppt *.pptx)")
        if not inp:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", f"{Path(inp).stem}.pdf", "PDF (*.pdf)")
        if not out:
            return
        result = self.run_action("Convertendo apresentação para PDF...", lambda: office_to_pdf(inp, out))
        if result:
            QMessageBox.information(self, APP_TITLE, f"PDF criado com sucesso:\n{result}")

    def do_translate(self):
        pdf = self.ensure_pdf()
        if not pdf:
            return
        dlg = TranslateDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        code = dlg.language_code()
        out, _ = QFileDialog.getSaveFileName(self, "Salvar PDF traduzido", f"{Path(pdf).stem}_{code}.pdf", "PDF (*.pdf)")
        if not out:
            return
        result = self.run_action("Traduzindo PDF...", lambda: translate_pdf(pdf, out, code))
        if result:
            QMessageBox.information(self, APP_TITLE, f"PDF traduzido criado:\n{result}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("TekPrax")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
