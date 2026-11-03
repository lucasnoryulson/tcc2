"""Export the reviewed Markdown manuscript and speaker notes to editable Office files."""

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WRITING = ROOT / "docs/monografia"
DEFENSE = ROOT / "docs/defesa"


def plain(text):
    text = re.sub(r"\[([^]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    return text.replace("**", "").replace("`", "")


def architecture():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    labels = ["AST e\ndependências", "Classificação\ne planejamento", "Transformação\ndeterminística", "Corretude e\nbenchmark",
              "Seleção\nmedida", "Contexto +\nCoordinator LLM", "Executor e\nrevalidação", "Código +\nmanifesto"]
    positions = [(0, 1), (1, 1), (2, 1), (3, 1), (3, 0), (2, 0), (1, 0), (0, 0)]
    fig, ax = plt.subplots(figsize=(10, 3.6))
    for index, ((x, y), label) in enumerate(zip(positions, labels)):
        color = "#FFF0CA" if index == 5 else "#DDF2E7" if index == 7 else "#DFEDF7"
        ax.add_patch(FancyBboxPatch((x * 2.5, y * 1.5), 2.1, 0.8, boxstyle="round,pad=0.06", facecolor=color, edgecolor="#245365"))
        ax.text(x * 2.5 + 1.05, y * 1.5 + 0.4, label, ha="center", va="center", fontsize=12)
        if index:
            px, py = positions[index - 1]
            start = (px * 2.5 + 2.15, py * 1.5 + 0.4) if y == py and x > px else (px * 2.5 - 0.05, py * 1.5 + 0.4)
            end = (x * 2.5 - 0.05, y * 1.5 + 0.4) if y == py and x > px else (x * 2.5 + 2.15, y * 1.5 + 0.4)
            if x == px:
                start, end = (x * 2.5 + 1.05, py * 1.5 - 0.07), (x * 2.5 + 1.05, y * 1.5 + 0.87)
            ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "color": "#245365", "lw": 1.4})
    ax.text(4.8, -0.4, "RETUNE / MODIFY / REJECT: encerra a tentativa; não executa reparo automático", ha="center", fontsize=10)
    ax.set(xlim=(-0.25, 9.9), ylim=(-0.6, 2.65))
    ax.axis("off")
    fig.tight_layout()
    for extension in ("png", "svg"):
        fig.savefig(WRITING / ("ARQUITETURA." + extension), dpi=180)
    plt.close(fig)


def word_export(source, target):
    from docx import Document
    from docx.shared import Cm, Inches, Pt

    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2.1)
    section.left_margin = section.right_margin = Cm(2.2)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Times New Roman", Pt(12)
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.space_after = Pt(7)
    for name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        doc.styles[name].font.name = "Arial"
    section.footer.paragraphs[0].text = "Versão revisada — 03/11/2026 — conteúdo e evidências consolidados; adequação institucional pendente."
    section.footer.paragraphs[0].runs[0].font.size = Pt(8)
    doc.core_properties.author = "Lucas Nory Ulson"
    doc.core_properties.title = "TCC2 — monografia revisada"
    doc.core_properties.subject = "Conteúdo e evidências consolidados; adequação ao modelo institucional pendente"
    lines = source.read_text().splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)", line)
        image = re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)", line)
        if heading:
            doc.add_heading(plain(heading[2]), level=len(heading[1]) - 1)
        elif image:
            doc.add_picture(str((source.parent / image[2]).resolve(strict=True)), width=Inches(6.2))
            caption = doc.add_paragraph(image[1])
            caption.runs[0].italic = True
            caption.runs[0].font.size = Pt(9)
        elif line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                    table_lines.append(cells)
                index += 1
            table = doc.add_table(rows=0, cols=len(table_lines[0]))
            table.style = "Table Grid"
            for number, cells in enumerate(table_lines):
                if len(cells) != len(table_lines[0]):
                    raise ValueError("Inconsistent manuscript table.")
                for cell, text in zip(table.add_row().cells, cells):
                    cell.text = plain(text)
                    for run in cell.paragraphs[0].runs:
                        run.font.size = Pt(9)
                        run.bold = number == 0
            continue
        elif re.match(r"^(- |\d+\. )", line):
            text = [line]
            while index + 1 < len(lines) and lines[index + 1].startswith("  "):
                index += 1
                text.append(lines[index].strip())
            numbered = bool(re.match(r"^\d+\. ", line))
            doc.add_paragraph(plain(re.sub(r"^(- |\d+\. )", "", " ".join(text))), style="List Number" if numbered else "List Bullet")
        else:
            text = [line]
            while index + 1 < len(lines) and lines[index + 1].strip() and not re.match(r"^(#|\||!\[|- |\d+\. )", lines[index + 1]):
                index += 1
                text.append(lines[index].strip())
            doc.add_paragraph(plain(" ".join(text)))
        index += 1
    doc.save(target)
    reopened = Document(target)
    assert reopened.tables and len(reopened.inline_shapes) == 2
    exported_text = " ".join(paragraph.text for paragraph in reopened.paragraphs)
    assert "Não foi demonstrado benefício adicional" in exported_text
    assert "22 campanhas" in exported_text


def slide_sources(path):
    slides = []
    for chunk in path.read_text().split("\n---\n"):
        notes = re.search(r"<!-- fala:\s*(.*?)-->", chunk, re.S)
        if not notes:
            raise ValueError("Each slide requires explicit speaker notes.")
        lines = [line.strip() for line in re.sub(r"<!-- fala:.*?-->", "", chunk, flags=re.S).splitlines() if line.strip()]
        if not lines or not lines[0].startswith("# "):
            raise ValueError("Each slide requires a title.")
        slides.append({"title": lines[0][2:], "body": lines[1:], "notes": " ".join(notes[1].split())})
    return slides


def powerpoint_export(source, target):
    from PIL import Image
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches, Pt

    slides = slide_sources(source)
    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
    deck.core_properties.author = "Lucas Nory Ulson"
    deck.core_properties.title = "TCC2 — defesa revisada"
    ink = RGBColor.from_string("173447")
    for number, item in enumerate(slides, 1):
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string("F7FAFC")
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, deck.slide_width, Inches(0.14))
        bar.fill.solid()
        bar.fill.fore_color.rgb = RGBColor.from_string("187F89")
        bar.line.fill.background()

        def text_box(text, x, y, width, height, size, bold=False):
            frame = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(width), Inches(height)).text_frame
            frame.word_wrap = True
            for index, line in enumerate(text.split("\n")):
                paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
                paragraph.text = plain(line)
                paragraph.font.name, paragraph.font.size = "Arial", Pt(size)
                paragraph.font.bold, paragraph.font.color.rgb = bold, ink
                paragraph.space_after = Pt(13)
            return frame

        text_box(item["title"], 0.65, 0.48, 12, 1.2, 30, True)
        images = [re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)", line) for line in item["body"]]
        images = [match for match in images if match]
        if images:
            if len(images) != 1:
                raise ValueError("This deck layout supports one image per slide.")
            path = (source.parent / images[0][2]).resolve(strict=True)
            with Image.open(path) as picture:
                ratio = picture.width / picture.height
            width = min(11.9, 4.1 * ratio)
            slide.shapes.add_picture(str(path), Inches((13.333 - width) / 2), Inches(1.65), width=Inches(width))
            remaining = [line for line in item["body"] if not line.startswith("![")]
            text_box("\n".join(remaining), 0.7, 6, 12, 0.85, 13)
        else:
            body = [line for line in item["body"] if not line.startswith("Fonte:")]
            text_box("\n".join("• " + line[2:] if line.startswith("- ") else line for line in body), 0.75, 1.9, 11.9, 4.55, 23 if number != 15 else 20)
            sources = [line for line in item["body"] if line.startswith("Fonte:")]
            if sources:
                text_box("\n".join(sources), 0.75, 6.35, 11.9, 0.45, 11)
        text_box("VERSÃO REVISADA · evidências consolidadas", 0.72, 7.02, 10.5, 0.32, 10)
        text_box(f"{number:02d}/{len(slides)}", 12.05, 7.02, 0.6, 0.32, 10)
        slide.notes_slide.notes_text_frame.text = item["notes"]
    deck.save(target)
    reopened = Presentation(target)
    assert len(reopened.slides) == len(slides)
    assert all(slide.has_notes_slide and slide.notes_slide.notes_text_frame.text for slide in reopened.slides)


def main():
    architecture()
    word_export(WRITING / "BASE_MONOGRAFIA.md", WRITING / "MONOGRAFIA_REVISAO_FINAL.docx")
    powerpoint_export(DEFENSE / "SLIDES.md", DEFENSE / "DEFESA_REVISAO_FINAL.pptx")
    sources = [WRITING / "BASE_MONOGRAFIA.md", WRITING / "LEITURA_DOS_DOCUMENTOS.md", WRITING / "referencias.bib",
               DEFENSE / "SLIDES.md", DEFENSE / "DEMONSTRACAO.md", Path(__file__)]
    outputs = [WRITING / "MONOGRAFIA_REVISAO_FINAL.docx", WRITING / "ARQUITETURA.png",
               WRITING / "ARQUITETURA.svg", DEFENSE / "DEFESA_REVISAO_FINAL.pptx"]
    originals = [ROOT.parent / name for name in (
        "tcc_proposta(1).docx", "Guia_TCC2_Paralelizacao_Automatica_atualizado_2026-09-02(1).docx",
        "Resumo_Executivo_TCC2_Lucas_Ulson_Atualizado_2026-10-08.docx",
    ) if (ROOT.parent / name).is_file()]
    manifest = {"status": "CONTENT_REVIEW_COMPLETE_EXTERNAL_FORMATTING_PENDING", "author": "Lucas Nory Ulson",
                "originals_referenced": [{"path": str(path.relative_to(ROOT.parent)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in originals],
                "sources": [{"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in sources],
                "outputs": [{"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in outputs]}
    (WRITING / "REVIEW_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("REVISED_MATERIAL_EXPORTED: Word manuscript, PowerPoint with notes, architecture and review manifest.")


if __name__ == "__main__":
    main()
