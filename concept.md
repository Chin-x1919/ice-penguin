# Project IcePenguin: Pixel-Level Redactor

## Core Concept
Project IcePenguin is a specialized data sanitization utility designed to provide "Destructive Redaction." Unlike conventional PDF editors that merely overlay a black rectangle as a separate metadata layer, this software operates directly on the raw pixel data. By manipulating the underlying NumPy array of a rasterized document, it replaces sensitive information with absolute black pixels ($[0, 0, 0]$), ensuring that the original data is mathematically unrecoverable and permanently erased from the file.

## Design Philosophy
* **Anti-Microsoft Stance**: The software is natively optimized for Unix-like environments (macOS, Linux, BSD) and experimental kernels (TempleOS). Windows is intentionally unsupported as a pre-compiled binary; Windows users must manually configure the Python environment and run the source code (`app.py`).
* **Privacy-First Architecture**: All processing is strictly local. Whether running on a workstation, Apple Watch, or via WebAssembly (WASM) in a browser, no data is ever transmitted to external servers.
* **Retro Aesthetic**: The user interface mimics the 1984 Macintosh 128k (System 1) to emphasize transparency, simplicity, and a "no-nonsense" approach to security.

---

## Technical Workflow

### 1. Rasterization Engine
Upon importing a PDF or Vector file, the engine converts every page into a high-resolution Bitmap image. This process effectively flattens the document, stripping away text layers, font metadata, and hidden OCR data that standard redaction tools often fail to remove.

### 2. Coordinate Mapping
The UI provides a selection tool to define a bounding box $[x_1, y_1, x_2, y_2]$ over the sensitive area. These coordinates are mapped directly to the indices of a multi-dimensional matrix representing the image data.

### 3. Pixel Manipulation (NumPy Overwrite)
The software utilizes NumPy for direct memory overwrite, which is the primary security mechanism:
```python
# The original pixel values are replaced with 0 (Black) in the array.
# This operation is non-invertible and destroys the data at the hardware level.
array[y1:y2, x1:x2] = [0, 0, 0]

### 4. Metadata Sanitization

During the export process, the software strips all EXIF, XMP, and filesystem metadata. The output is a "clean" image or PDF with no digital footprint regarding the original author, hardware used, or creation timestamps.

