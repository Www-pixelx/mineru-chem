#!/usr/bin/env python
from pathlib import Path
from mineru.cli.common import do_parse, read_fn

pdf_path = Path("demo/pdfs/demo1.pdf")

do_parse(
    output_dir="output",
    pdf_file_names=[pdf_path.stem],
    pdf_bytes_list=[read_fn(pdf_path)],
    p_lang_list=["ch"],
    backend="pipeline",
    parse_method="auto",
    chem_enable=True,
)
