# ice-penguin


## Overview

`app.py` implements Project IcePenguin with both CLI and interactive GUI:
- rasterize PDF pages to bitmap
- map coordinates to pixel indices
- overwrite pixels with pure black (`[0,0,0]`) using NumPy
- strip image metadata on save
- **GUI features**: live preview, zoom, drag-to-select redaction box, drag & drop file loading

## Requirements

- Python 3.8+
- pillow
- numpy
- pymupdf

Install dependencies (recommended via virtual environment):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run UI app

- `python app.py` (launches Tkinter GUI)
- `python app.py gui` (explicit GUI mode)

## GUI Workflow

1. Start the app: `python app.py`
2. **Load file** (choose one):
   - Click `Browse...` on Input field
   - **Drag & drop** a PNG/JPEG/PDF directly onto the preview area
3. Click `Load` to display preview and auto-fit scaling
4. **Select redaction area**:
   - Drag a rectangle on the preview canvas (red outline appears)
   - Coordinates auto-populate in the `Coords` field
5. Adjust `Page` index (PDF only) or toggle `Redact all PDF pages`
6. Set output file path (auto-populated by default)
7. Click `Redact` to apply destructive pixel overwrite
8. Output saved at target with metadata stripped

### Zoom & Navigation

- `Zoom +` / `Zoom -` to scale preview (0.1x to 10x)
- Selection box coordinates update automatically relative to original image

## Basic CLI use

### Redact an image

```bash
python app.py redact --input input.png --output out.png --coords 100,100,400,200
```

### Redact one page of PDF

```bash
python app.py redact --input input.pdf --output out.pdf --coords 200,150,400,250 --page 0 --dpi 300
```

### Redact all pages of PDF

```bash
python app.py redact --input input.pdf --output out.pdf --coords 100,100,300,180 --all --dpi 200
```

## Notes

- PDF rasterization means the output is a flattened image-based PDF, with no text layer.
- Coordinates are pixel coordinates after rasterization.
- Output is 1) destructive for pixels in selected rectangle, 2) metadata stripped via in-memory reserialize.

## License
MIT License
