# MinerU + Chem

MinerU 2.5.4 with chemical recognition

## Requirements

This project is based on [opendatalab/MinerU](https://github.com/opendatalab/MinerU) and keeps the chemical recognition flow on the pipeline backend.

| Item | Requirement |
| --- | --- |
| Python | 3.10-3.13 |
| Operating system | Linux, Windows, or macOS.  |
| CPU | Supported for pipeline inference, but slower. |
| GPU acceleration | NVIDIA GPU with Turing or later architecture, or Apple Silicon. |
| VRAM | 6 GB or more recommended for pipeline acceleration. |
| RAM | 16 GB minimum, 32 GB or more recommended. |
| Disk | 15 GB for this fork's usual pipeline + chemistry setup; 20 GB or more recommended, preferably on SSD. |

## Install
It is recommended to install this project in a dedicated conda virtual environment.

Install dependencies:
```bash
cd mineru-chem
bash scripts/install.sh
```

## Storage
Plan for about 15 GB of disk space for a complete local setup:

| Component | Estimated size |
| --- | ---: |
| Repository | About 50 MB |
| Pipeline model files | About 2.1 GB |
| Chemical detection and recognition weights | About 1.3 GB |
| Python environment and packages | About 4-8 GB |
| Runtime output and caches | Depends on input size; reserve at least 1-3 GB |


## Using
If your device meets the GPU acceleration requirements, you can use a simple command line for document parsing:
```bash
mineru -p <input_path> -o <output_path>
```
Currently, chemical formula recognition is only available in pipeline backend.

You can also call the pipeline from a Python file:
```python
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
```
