# MinerU + Chem

MinerU 2.5.4 with chemical recognition

## Install
Install dependencies:
```bash
git clone https://github.com/Www-pixelx/mineru-chem.git
cd mineru-chem
pip install -e .[all]
pip install albumentations==1.1.0
```

## Using
If your device meets the GPU acceleration requirements, you can use a simple command line for document parsing:
```bash
mineru -p <input_path> -o <output_path>
```
If you need chemical formula recognition , use this command line:
```bash
mineru -p <input_path> -o <output_path> -c True
```
Currently, chemical formula recognition is only available in pipeline backend.