#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class EquationObject:
    image_filename: str  # e.g. image1.wmf
    ole_filename: str  # e.g. oleObject1.bin
    inline: bool


DOCX_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "v": "urn:schemas-microsoft-com:vml",
    "o": "urn:schemas-microsoft-com:office:office",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def _run(
    args: list[str],
    *,
    cwd: Path | None = None,
    input_text: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        cmd = " ".join(args)
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {cmd}\n\nSTDERR:\n{proc.stderr.strip()}"
        )
    return proc


def _require_executable(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Missing required executable: {name}")


def _check_runtime_dependencies() -> None:
    _require_executable("pandoc")
    _require_executable("ruby")
    _run(
        [
            "ruby",
            "-e",
            "require 'mathtype_to_mathml_plus'; puts 'ok'",
        ],
        check=True,
    )


def _read_zip_text(z: zipfile.ZipFile, name: str) -> str:
    return z.read(name).decode("utf-8", errors="replace")


def _parse_rels(z: zipfile.ZipFile) -> dict[str, str]:
    rels_xml = _read_zip_text(z, "word/_rels/document.xml.rels")
    root = ET.fromstring(rels_xml)
    rels: dict[str, str] = {}
    for rel in root:
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rid and target:
            rels[rid] = target
    return rels


def _iter_equation_objects(z: zipfile.ZipFile) -> Iterable[EquationObject]:
    rels = _parse_rels(z)
    document_xml = _read_zip_text(z, "word/document.xml")
    root = ET.fromstring(document_xml)

    for p in root.iterfind(".//w:p", DOCX_NS):
        paragraph_text = "".join((t.text or "") for t in p.iterfind(".//w:t", DOCX_NS))
        has_text = bool(paragraph_text.strip())

        for obj in p.iterfind(".//w:object", DOCX_NS):
            imagedata = obj.find(".//v:imagedata", DOCX_NS)
            ole = obj.find(".//o:OLEObject", DOCX_NS)
            if imagedata is None or ole is None:
                continue

            img_rid = imagedata.attrib.get(f"{{{DOCX_NS['r']}}}id")
            ole_rid = ole.attrib.get(f"{{{DOCX_NS['r']}}}id")
            if not img_rid or not ole_rid:
                continue

            img_target = rels.get(img_rid)
            ole_target = rels.get(ole_rid)
            if not img_target or not ole_target:
                continue

            image_filename = Path(img_target).name
            ole_filename = Path(ole_target).name

            yield EquationObject(
                image_filename=image_filename,
                ole_filename=ole_filename,
                inline=has_text,
            )


def _convert_docx_to_tex(
    *,
    input_docx: Path,
    output_dir: Path,
    tex_filename: str,
    media_dirname: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    _run(
        [
            "pandoc",
            str(input_docx),
            "-o",
            tex_filename,
            "--standalone",
            "--wrap=none",
            f"--extract-media={media_dirname}",
        ],
        cwd=output_dir,
        check=True,
    )


def _ole_to_mathml(ole_bin_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(prefix="docx2tex_ole_", suffix=".bin", delete=False) as f:
        tmp_path = Path(f.name)
        f.write(ole_bin_bytes)
    try:
        ruby = "require 'mathtype_to_mathml_plus'; print MathTypeToMathMLPlus::Converter.new(ARGV[0]).convert"
        proc = _run(["ruby", "-e", ruby, str(tmp_path)], check=True)
        return proc.stdout
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def _mathml_to_latex(mathml: str) -> str:
    html = f"<html><body>{mathml}</body></html>"
    proc = _run(["pandoc", "-f", "html", "-t", "latex"], input_text=html, check=True)
    return proc.stdout.strip()


def _wrap_math(latex: str, *, inline: bool) -> str:
    s = latex.strip()
    if inline:
        if s.startswith("\\[") and s.endswith("\\]"):
            s = s[2:-2].strip()
        return f"\\({s}\\)"

    if s.startswith("\\[") and s.endswith("\\]"):
        return s
    return f"\\[{s}\\]"


def _replace_equation_images_with_latex(
    *,
    input_docx: Path,
    tex_path: Path,
    backup: bool,
    verbose: bool,
) -> dict[str, int]:
    with zipfile.ZipFile(input_docx) as z:
        equation_objects = list(_iter_equation_objects(z))
        img_to_obj: dict[str, EquationObject] = {}
        for obj in equation_objects:
            img_to_obj[obj.image_filename] = obj

        tex_original = tex_path.read_text(encoding="utf-8")

        if backup:
            backup_path = tex_path.with_suffix(tex_path.suffix + ".bak")
            if not backup_path.exists():
                backup_path.write_text(tex_original, encoding="utf-8")

        ole_to_latex_cache: dict[str, str] = {}

        def ole_to_wrapped_latex(obj: EquationObject) -> str:
            if obj.ole_filename not in ole_to_latex_cache:
                ole_bytes = z.read(f"word/embeddings/{obj.ole_filename}")
                mathml = _ole_to_mathml(ole_bytes)
                latex = _mathml_to_latex(mathml)
                ole_to_latex_cache[obj.ole_filename] = latex
            return _wrap_math(ole_to_latex_cache[obj.ole_filename], inline=obj.inline)

        replaced = 0
        skipped_no_map = 0
        failed = 0

        # Matches both:
        #   \pandocbounded{\includegraphics[...]{...}}
        # and:
        #   \includegraphics[...]{...}
        #
        # We replace the whole wrapper (including the trailing brace) when present.
        include_pattern = re.compile(
            r"(\\pandocbounded\{)?"
            r"(\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\})"
            r"\}?"
        )

        def replacer(m: re.Match[str]) -> str:
            nonlocal replaced, skipped_no_map, failed
            img_path = m.group(3)
            image_filename = Path(img_path).name
            obj = img_to_obj.get(image_filename)
            if obj is None:
                skipped_no_map += 1
                return m.group(0)
            try:
                latex = ole_to_wrapped_latex(obj)
            except Exception as e:
                failed += 1
                if verbose:
                    sys.stderr.write(
                        f"[warn] failed converting {obj.ole_filename} (for {image_filename}): {e}\n"
                    )
                return m.group(0)
            replaced += 1
            return latex

        tex_new = include_pattern.sub(replacer, tex_original)
        tex_path.write_text(tex_new, encoding="utf-8")

        return {
            "equation_objects": len(equation_objects),
            "replaced": replaced,
            "skipped_no_map": skipped_no_map,
            "failed": failed,
        }


def _default_output_name(input_docx: Path) -> str:
    return input_docx.stem + ".tex"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="docx2tex_mathtype.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
            Convert a Word .docx to a .tex file while converting MathType OLE equations to LaTeX math.

            This avoids WMF->PNG conversion and math OCR by extracting embedded OLE equation objects
            (e.g. Equation.DSMT4 / MathType) from the docx and converting them to MathML and then LaTeX.
            """
        ),
    )
    parser.add_argument("docx", type=Path, help="Input .docx path")
    parser.add_argument("out_dir", type=Path, help="Output directory")
    parser.add_argument(
        "--tex-name",
        type=str,
        default=None,
        help="Output .tex filename (default: <docx_stem>.tex)",
    )
    parser.add_argument(
        "--media-dir",
        type=str,
        default=None,
        help="Extracted media folder name (default: <docx_stem>_media)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not write a .bak copy of the generated .tex before patching equations",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-equation warnings when conversion fails",
    )
    args = parser.parse_args(argv)

    input_docx = args.docx.expanduser().resolve()
    out_dir = args.out_dir.expanduser().resolve()
    tex_name = args.tex_name or _default_output_name(input_docx)
    media_dir = args.media_dir or (input_docx.stem + "_media")

    if not input_docx.exists():
        sys.stderr.write(f"Input file not found: {input_docx}\n")
        return 2
    if input_docx.suffix.lower() != ".docx":
        sys.stderr.write(f"Input must be a .docx file: {input_docx}\n")
        return 2

    try:
        _check_runtime_dependencies()
    except Exception as e:
        sys.stderr.write(
            "Missing dependencies.\n"
            "Required: pandoc, ruby, and Ruby gem mathtype_to_mathml_plus.\n\n"
            f"Error: {e}\n"
        )
        return 2

    _convert_docx_to_tex(
        input_docx=input_docx,
        output_dir=out_dir,
        tex_filename=tex_name,
        media_dirname=media_dir,
    )

    stats = _replace_equation_images_with_latex(
        input_docx=input_docx,
        tex_path=out_dir / tex_name,
        backup=not args.no_backup,
        verbose=args.verbose,
    )

    sys.stdout.write(
        "done\n"
        f"- tex: {out_dir / tex_name}\n"
        f"- media: {out_dir / media_dir}\n"
        f"- equation objects in docx: {stats['equation_objects']}\n"
        f"- replaced includegraphics: {stats['replaced']}\n"
        f"- failed conversions: {stats['failed']}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
