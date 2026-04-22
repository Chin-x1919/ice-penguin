#!/usr/bin/env python3
"""IcePenguin - Pixel-Level Redactor

Usage:
  python app.py redact --input input.pdf --output output.pdf --coords 100,100,500,300 --page 0
  python app.py redact --input input.png --output output-redacted.png --coords 30,30,200,120
  python app.py redact --input input.pdf --output output.pdf --coords 100,100,500,300 --all --dpi 200

Coordinates are in pixels after rasterization. For PDFs, you can adjust DPI with --dpi.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox

try:
    from PIL import Image, ImageTk
except ImportError:
    raise SystemExit("Missing dependency pillow. Install with: pip install pillow")

try:
    import numpy as np
except ImportError:
    raise SystemExit("Missing dependency numpy. Install with: pip install numpy")

try:
    import fitz  # PyMuPDF
except ImportError:
    raise SystemExit("Missing dependency PyMuPDF. Install with: pip install pymupdf")

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES, DND_TEXT
    TK_ROOT = TkinterDnD.Tk
except ImportError:
    DND_FILES = None
    DND_TEXT = None
    TK_ROOT = tk.Tk


def parse_coords(value: str) -> Tuple[int, int, int, int]:
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("coords must be 4 comma-separated ints: x1,y1,x2,y2")
    try:
        nums = tuple(int(p) for p in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("coords must all be integers") from exc
    x1, y1, x2, y2 = nums
    if x2 <= x1 or y2 <= y1:
        raise argparse.ArgumentTypeError("coords must satisfy x2>x1 and y2>y1")
    return x1, y1, x2, y2


def strip_image_metadata(img: Image.Image) -> Image.Image:
    # Use get_flattened_data() instead of deprecated getdata()
    arr = np.array(img)
    clean = Image.fromarray(arr, mode=img.mode)
    return clean


def redact_numpy(img: Image.Image, rect: Tuple[int, int, int, int]) -> Image.Image:
    x1, y1, x2, y2 = rect
    arr = np.array(img)

    if img.mode == "RGBA":
        arr[y1:y2, x1:x2, 0:3] = 0
        arr[y1:y2, x1:x2, 3] = 255
    elif img.mode == "RGB":
        arr[y1:y2, x1:x2, :] = 0
    elif img.mode == "L":
        arr[y1:y2, x1:x2] = 0
    else:
        arr = arr.astype(np.uint8)
        arr[y1:y2, x1:x2, :] = 0

    return Image.fromarray(arr, mode=img.mode)


def rasterize_pdf_page(doc: fitz.Document, page_number: int, dpi: int = 150) -> Image.Image:
    page = doc.load_page(page_number)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    data = pix.tobytes()
    mode = "RGB" if pix.n < 4 else "RGBA"
    img = Image.frombytes(mode, (pix.width, pix.height), data)
    return img


def save_images_as_pdf(images: List[Image.Image], output_path: str) -> None:
    if not images:
        raise ValueError("No images to save")
    first, rest = images[0], images[1:]
    first.save(output_path, "PDF", resolution=100.0, save_all=True, append_images=rest)


def redact_image_file(input_path: str, output_path: str, coords: Tuple[int, int, int, int]) -> None:
    img = Image.open(input_path)
    img = strip_image_metadata(img)
    redacted = redact_numpy(img, coords)
    redacted = strip_image_metadata(redacted)

    fmt = "PNG" if output_path.lower().endswith(".png") else img.format or "PNG"
    redacted.save(output_path, fmt)


def redact_pdf_file(input_path: str, output_path: str, coords: Tuple[int, int, int, int], page: int | None, all_pages: bool, dpi: int) -> None:
    doc = fitz.open(input_path)
    target_pages = list(range(len(doc))) if all_pages else [page if page is not None else 0]
    target_pages = [p for p in target_pages if 0 <= p < len(doc)]

    redacted_pages: List[Image.Image] = []

    for idx in range(len(doc)):
        img = rasterize_pdf_page(doc, idx, dpi=dpi)
        img = strip_image_metadata(img)
        if idx in target_pages:
            img = redact_numpy(img, coords)
            img = strip_image_metadata(img)
        redacted_pages.append(img.convert("RGB"))

    save_images_as_pdf(redacted_pages, output_path)


def redact_file_with_options(input_path: str, output_path: str, coords: Tuple[int, int, int, int], page: int, all_pages: bool, dpi: int) -> None:
    input_ext = os.path.splitext(input_path)[1].lower()
    if input_ext == ".pdf":
        redact_pdf_file(input_path, output_path, coords, page, all_pages=all_pages, dpi=dpi)
    elif input_ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
        redact_image_file(input_path, output_path, coords)
    else:
        raise ValueError(f"Unsupported input file type: {input_ext}")


def launch_gui() -> None:
    root = TK_ROOT()
    root.title("IcePenguin Pixel Redactor")
    root.geometry("980x720")

    input_path = tk.StringVar()
    output_path = tk.StringVar()
    all_pages_var = tk.BooleanVar(value=False)

    current_image: Image.Image | None = None
    preview_image: Image.Image | None = None
    tk_preview = None
    zoom_factor = 1.0
    fit_scale = 1.0
    rect_id = None
    select_start = None

    def choose_input():
        path = filedialog.askopenfilename(title="Select input image or PDF", filetypes=[("PDF", "*.pdf"), ("Images", "*.png;*.jpg;*.jpeg;*.tiff;*.bmp"), ("All files", "*.*")])
        if path:
            input_path.set(path)
            if not output_path.get().strip():
                base, ext = os.path.splitext(path)
                output_path.set(base + "-redacted" + ext)

    def choose_output():
        path = filedialog.asksaveasfilename(title="Select output path", defaultextension=".png", filetypes=[("PDF", "*.pdf"), ("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg"), ("All files", "*.*")])
        if path:
            output_path.set(path)
    preview_image: Image.Image | None = None
    tk_preview = None
    zoom_factor = 1.0
    fit_scale = 1.0
    rect_id = None
    select_start = None

    def load_input_image() -> None:
        nonlocal current_image, zoom_factor, fit_scale
        path = input_path.get().strip()
        if not path or not os.path.exists(path):
            return

        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".pdf":
                page_index = int(page_entry.get()) if page_entry.get().strip() else 0
                dpi_num = int(dpi_entry.get()) if dpi_entry.get().strip() else 300
                doc = fitz.open(path)
                page_index = max(0, min(page_index, len(doc) - 1))
                current_image = rasterize_pdf_page(doc, page_index, dpi=dpi_num)
            else:
                current_image = Image.open(path)
            current_image = strip_image_metadata(current_image.convert("RGB"))
            zoom_factor = 1.0
            fit_scale = min(1.0, min(preview_canvas.winfo_width() / max(1, current_image.width), preview_canvas.winfo_height() / max(1, current_image.height)))
            update_preview()
        except Exception as exc:
            status_label.config(text=f"Error loading input: {exc}", fg="red")
            messagebox.showerror("IcePenguin Error", f"Failed to load image: {exc}")

    def update_preview() -> None:
        nonlocal preview_image, tk_preview, fit_scale
        if current_image is None:
            return

        if preview_canvas.winfo_width() <= 1 or preview_canvas.winfo_height() <= 1:
            root.after(50, update_preview)
            return

        w, h = current_image.width, current_image.height
        effective_scale = fit_scale * zoom_factor
        sw = max(1, int(w * effective_scale))
        sh = max(1, int(h * effective_scale))
        preview_image = current_image.resize((sw, sh), Image.LANCZOS)
        tk_preview = ImageTk.PhotoImage(preview_image)

        preview_canvas.delete("all")
        preview_canvas.create_image(0, 0, anchor="nw", image=tk_preview)
        preview_canvas.image = tk_preview

        coords_entry.delete(0, tk.END)
        coords_entry.insert(0, "")

        status_label.config(text=f"Preview size: {sw}x{sh}, original: {w}x{h}, zoom: {zoom_factor:.2f}", fg="black")

    def set_coords_from_canvas(x1: int, y1: int, x2: int, y2: int) -> None:
        if current_image is None:
            return
        effective_scale = fit_scale * zoom_factor
        ix1 = int(min(x1, x2) / effective_scale)
        iy1 = int(min(y1, y2) / effective_scale)
        ix2 = int(max(x1, x2) / effective_scale)
        iy2 = int(max(y1, y2) / effective_scale)
        ix1 = max(0, min(current_image.width - 1, ix1))
        iy1 = max(0, min(current_image.height - 1, iy1))
        ix2 = max(0, min(current_image.width, ix2))
        iy2 = max(0, min(current_image.height, iy2))
        if ix2 <= ix1 or iy2 <= iy1:
            return
        coords_entry.delete(0, tk.END)
        coords_entry.insert(0, f"{ix1},{iy1},{ix2},{iy2}")

    def on_zoom_in():
        nonlocal zoom_factor
        if current_image is None:
            return
        zoom_factor = min(10.0, zoom_factor * 1.25)
        update_preview()

    def on_zoom_out():
        nonlocal zoom_factor
        if current_image is None:
            return
        zoom_factor = max(0.1, zoom_factor / 1.25)
        update_preview()

    def on_canvas_press(event):
        nonlocal select_start, rect_id
        select_start = (event.x, event.y)
        if rect_id is not None:
            preview_canvas.delete(rect_id)
            rect_id = None

    def on_canvas_drag(event):
        nonlocal rect_id
        if select_start is None:
            return
        x1, y1 = select_start
        x2, y2 = event.x, event.y
        if rect_id is not None:
            preview_canvas.coords(rect_id, x1, y1, x2, y2)
        else:
            rect_id = preview_canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2)

    def on_canvas_release(event):
        if select_start is None:
            return
        x1, y1 = select_start
        x2, y2 = event.x, event.y
        set_coords_from_canvas(x1, y1, x2, y2)

    def on_redact():
        try:
            coords = parse_coords(coords_entry.get())
            page_num = int(page_entry.get()) if page_entry.get().strip() else 0
            dpi_num = int(dpi_entry.get()) if dpi_entry.get().strip() else 300
            in_path = input_path.get().strip()
            out_path = output_path.get().strip()

            if not in_path or not out_path:
                raise ValueError("Input and output paths must be set")

            redact_file_with_options(in_path, out_path, coords, page_num, all_pages_var.get(), dpi_num)
            status_label.config(text=f"Redaction complete: {out_path}", fg="green")
            load_input_image()
        except Exception as exc:
            status_label.config(text=f"Error: {exc}", fg="red")
            messagebox.showerror("IcePenguin Error", str(exc))

    def refresh_output_default(*_):
        path = input_path.get().strip()
        if path and not output_path.get().strip():
            base, ext = os.path.splitext(path)
            output_path.set(base + "-redacted" + ext)

    # layout
    frame = tk.Frame(root)
    frame.pack(fill="both", expand=True, padx=8, pady=8)

    left = tk.Frame(frame)
    left.pack(side="left", fill="both", expand=False)

    right = tk.Frame(frame)
    right.pack(side="right", fill="both", expand=True)

    # controls
    row = 0
    tk.Label(left, text="Input file:").grid(row=row, column=0, sticky="w", pady=4)
    tk.Entry(left, textvariable=input_path, width=48).grid(row=row, column=1, columnspan=2, sticky="w")
    tk.Button(left, text="Browse...", command=lambda: (choose_input(), load_input_image())).grid(row=row, column=3, padx=4)

    row += 1
    tk.Label(left, text="Output file:").grid(row=row, column=0, sticky="w", pady=4)
    tk.Entry(left, textvariable=output_path, width=48).grid(row=row, column=1, columnspan=2, sticky="w")
    tk.Button(left, text="Browse...", command=choose_output).grid(row=row, column=3, padx=4)

    row += 1
    tk.Label(left, text="Coords x1,y1,x2,y2:").grid(row=row, column=0, sticky="w", pady=4)
    coords_entry = tk.Entry(left, width=26)
    coords_entry.grid(row=row, column=1, columnspan=2, sticky="w")

    row += 1
    tk.Label(left, text="Page (PDF, 0-based):").grid(row=row, column=0, sticky="w", pady=4)
    page_entry = tk.Entry(left, width=8)
    page_entry.insert(0, "0")
    page_entry.grid(row=row, column=1, sticky="w")
    tk.Checkbutton(left, text="Redact all PDF pages", variable=all_pages_var).grid(row=row, column=2, columnspan=2, sticky="w")

    row += 1
    tk.Label(left, text="DPI (PDF):").grid(row=row, column=0, sticky="w", pady=4)
    dpi_entry = tk.Entry(left, width=8)
    dpi_entry.insert(0, "300")
    dpi_entry.grid(row=row, column=1, sticky="w")

    row += 1
    tk.Button(left, text="Load", command=load_input_image, width=10).grid(row=row, column=0, pady=10)
    tk.Button(left, text="Zoom +", command=on_zoom_in, width=8).grid(row=row, column=1)
    tk.Button(left, text="Zoom -", command=on_zoom_out, width=8).grid(row=row, column=2)
    tk.Button(left, text="Redact", command=on_redact, width=10, bg="black", fg="white").grid(row=row, column=3)

    row += 1
    status_label = tk.Label(left, text="Ready", fg="black", anchor="w")
    status_label.grid(row=row, column=0, columnspan=4, sticky="we", pady=6)

    # preview
    preview_canvas = tk.Canvas(right, width=780, height=660, bg="gray")
    preview_canvas.pack(fill="both", expand=True)
    preview_canvas.bind("<ButtonPress-1>", on_canvas_press)
    preview_canvas.bind("<B1-Motion>", on_canvas_drag)
    preview_canvas.bind("<ButtonRelease-1>", on_canvas_release)

    # Drag and drop support
    if DND_FILES is not None:
        def on_drop(event):
            try:
                dropped_files = event.data.strip('{}').split()
                if dropped_files:
                    file_path = dropped_files[0]
                    if os.path.exists(file_path):
                        input_path.set(file_path)
                        base, ext = os.path.splitext(file_path)
                        if not output_path.get().strip():
                            output_path.set(base + "-redacted" + ext)
                        load_input_image()
                        status_label.config(text=f"Loaded: {os.path.basename(file_path)}", fg="blue")
            except Exception as exc:
                status_label.config(text=f"Error dropping file: {exc}", fg="red")

        def on_drag_enter(event):
            preview_canvas.config(bg="lightblue")
            return event.action

        def on_drag_leave(event):
            preview_canvas.config(bg="gray")

        preview_canvas.drop_target_register(DND_FILES)
        preview_canvas.bind("<<Drop>>", on_drop)
        preview_canvas.bind("<<DragEnter>>", on_drag_enter)
        preview_canvas.bind("<<DragLeave>>", on_drag_leave)

        root.drop_target_register(DND_FILES)
        root.bind("<<Drop>>", on_drop)

    input_path.trace_add("write", lambda *_: refresh_output_default())

    root.mainloop()


def main() -> None:
    try:
        if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] == "gui"):
            launch_gui()
            return

        parser = argparse.ArgumentParser(description="IcePenguin Pixel-Level Redactor")
        subparsers = parser.add_subparsers(dest="cmd")

        redact_parser = subparsers.add_parser("redact", help="Redact a file")
        redact_parser.add_argument("--input", required=True, help="Input image or PDF path")
        redact_parser.add_argument("--output", required=True, help="Output path")
        redact_parser.add_argument("--coords", required=True, type=parse_coords, help="Redaction bbox x1,y1,x2,y2")
        redact_parser.add_argument("--page", type=int, default=0, help="Page index for PDF to redact (0-based)")
        redact_parser.add_argument("--all", action="store_true", help="Redact the coords on all pages (PDF)")
        redact_parser.add_argument("--dpi", type=int, default=300, help="DPI for PDF rasterization")

        args = parser.parse_args()

        if args.cmd != "redact":
            parser.print_help()
            return

        try:
            redact_file_with_options(args.input, args.output, args.coords, args.page, args.all, args.dpi)
            print(f"Redaction complete: {args.output}")
        except Exception as exc:
            raise SystemExit(f"Error: {exc}")
    except Exception as exc:
        import traceback
        error_msg = f"IcePenguin Error:\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)
        try:
            import tkinter as tk_err
            root_err = tk_err.Tk()
            root_err.withdraw()
            from tkinter import messagebox
            messagebox.showerror("IcePenguin Startup Error", error_msg)
        except:
            pass
        raise SystemExit(1)


if __name__ == "__main__":
    main()
