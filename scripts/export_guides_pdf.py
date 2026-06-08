import pathlib
import textwrap


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT_MARGIN = 48
TOP_MARGIN = 60
BOTTOM_MARGIN = 48
FONT_SIZE = 11
LINE_HEIGHT = 15
MAX_CHARS = 88


def normalize_markdown_line(line):
    stripped = line.rstrip()
    if not stripped:
        return ""

    if stripped.startswith("```"):
        return "[bloque de codigo]"

    prefixes = ["# ", "## ", "### ", "#### ", "- ", "* "]
    for prefix in prefixes:
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):]
            break

    for marker in ("1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ", "8. ", "9. "):
        if stripped.startswith(marker):
            return stripped

    return stripped


def markdown_to_lines(content):
    lines = []
    in_code_block = False

    for raw_line in content.splitlines():
        stripped = raw_line.rstrip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            lines.append("[bloque de codigo]" if in_code_block else "")
            continue

        if in_code_block:
            if stripped:
                lines.extend(textwrap.wrap(stripped, width=MAX_CHARS, replace_whitespace=False) or [""])
            else:
                lines.append("")
            continue

        normalized = normalize_markdown_line(raw_line)
        if not normalized:
            lines.append("")
            continue

        wrapped = textwrap.wrap(normalized, width=MAX_CHARS, replace_whitespace=False, drop_whitespace=True)
        lines.extend(wrapped or [""])

    return lines


def pdf_escape(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_page_stream(lines):
    commands = ["BT", f"/F1 {FONT_SIZE} Tf"]
    y = PAGE_HEIGHT - TOP_MARGIN
    for line in lines:
        commands.append(f"1 0 0 1 {LEFT_MARGIN} {y} Tm ({pdf_escape(line)}) Tj")
        y -= LINE_HEIGHT
    commands.append("ET")
    return "\n".join(commands).encode("latin-1", errors="replace")


def paginate(lines):
    usable_height = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN
    lines_per_page = max(1, usable_height // LINE_HEIGHT)
    for offset in range(0, len(lines), lines_per_page):
        yield lines[offset : offset + lines_per_page]


def write_simple_pdf(lines, output_path, title):
    pages = list(paginate(lines)) or [[""]]

    objects = []

    def add_object(payload):
        objects.append(payload)
        return len(objects)

    font_id = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    pages_root_id = add_object(b"<< /Type /Pages /Kids [] /Count 0 >>")

    page_ids = []

    for page_lines in pages:
        stream = build_page_stream(page_lines)
        content_id = add_object(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        page_dict = (
            f"<< /Type /Page /Parent {pages_root_id} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")
        page_id = add_object(page_dict)
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_root = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")
    objects[pages_root_id - 1] = pages_root

    title_text = pdf_escape(title)
    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_root_id} 0 R >>".encode("ascii"))
    info_id = add_object(f"<< /Title ({title_text}) /Producer (OpenCode) >>".encode("latin-1", errors="replace"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as pdf_file:
        pdf_file.write(b"%PDF-1.4\n")
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(pdf_file.tell())
            pdf_file.write(f"{index} 0 obj\n".encode("ascii"))
            pdf_file.write(obj)
            pdf_file.write(b"\nendobj\n")

        xref_offset = pdf_file.tell()
        pdf_file.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf_file.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf_file.write(f"{offset:010d} 00000 n \n".encode("ascii"))

        trailer = (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R /Info {info_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        )
        pdf_file.write(trailer.encode("ascii"))


def export_markdown_to_pdf(input_path, output_path):
    content = input_path.read_text(encoding="utf-8")
    lines = markdown_to_lines(content)
    write_simple_pdf(lines, output_path, input_path.stem)


def main():
    project_root = pathlib.Path(__file__).resolve().parent.parent
    docs_dir = project_root / "docs"
    pdf_dir = docs_dir / "pdf"

    generated = []
    for markdown_file in sorted(docs_dir.glob("*.md")):
        output_file = pdf_dir / f"{markdown_file.stem}.pdf"
        export_markdown_to_pdf(markdown_file, output_file)
        generated.append(output_file)

    for output_file in generated:
        print(output_file)


if __name__ == "__main__":
    main()
