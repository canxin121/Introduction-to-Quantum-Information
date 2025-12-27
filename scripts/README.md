# scripts

## docx2tex_mathtype.py

Convert a `.docx` to a `.tex` file **and** replace embedded MathType/Equation Editor OLE equations with real LaTeX math.

This is designed for Word documents whose “formulas” are stored as:

- `o:OLEObject` (e.g. `ProgID="Equation.DSMT4"`) in `word/embeddings/oleObject*.bin`
- with a VML preview image like `word/media/image*.wmf`

### Requirements

- `pandoc` in `PATH`
- `ruby` in `PATH`
- Ruby gem `mathtype_to_mathml_plus`

Install the gem:

```bash
gem install mathtype_to_mathml_plus -N
```

If `gem install` fails building native extensions, you likely need `ruby-devel` / `ruby-dev` installed.

### Usage

```bash
python scripts/docx2tex_mathtype.py /path/to/input.docx /path/to/output_dir
```

Outputs:

- `/path/to/output_dir/<docx_stem>.tex`
- `/path/to/output_dir/<docx_stem>_media/` (images extracted by pandoc)
- `/path/to/output_dir/<docx_stem>.tex.bak` (unless `--no-backup`)

### Notes / limitations

- The script converts MathType OLE data → MathML → LaTeX; the resulting LaTeX is usually good but may still need minor cleanup for typographic polish (e.g. `sin` vs `\\sin`).
- It heuristically chooses inline math `\\( ... \\)` vs display math `\\[ ... \\]` using whether the original Word paragraph contained non-empty text.

