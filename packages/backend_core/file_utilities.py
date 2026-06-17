from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps
from PIL import UnidentifiedImageError

import fitz
import pillow_heif


pillow_heif.register_heif_opener()


_SUPPORTED_OUTPUTS = {
    "jpeg": ("JPEG", ".jpg", "image/jpeg"),
    "jpg": ("JPEG", ".jpg", "image/jpeg"),
    "png": ("PNG", ".png", "image/png"),
    "webp": ("WEBP", ".webp", "image/webp"),
}


@dataclass(frozen=True)
class ProcessedImage:
    content: bytes
    filename: str
    media_type: str
    metadata_removed: bool
    bytes_saved: int
    output_count: int = 1


def _infer_output(filename: str, output_format: str | None) -> tuple[str, str, str]:
    if output_format:
        key = output_format.strip().lower().lstrip(".")
    else:
        key = Path(filename).suffix.lower().lstrip(".") or "png"
    if key not in _SUPPORTED_OUTPUTS:
        raise ValueError("Unsupported output format. Use png, jpg, jpeg, or webp.")
    return _SUPPORTED_OUTPUTS[key]


def _clean_filename(filename: str, extension: str) -> str:
    stem = Path(filename or "image").stem or "image"
    return f"{stem}.cleaned{extension}"


def _render_svg_to_png(content: bytes, filename: str) -> ProcessedImage:
    document = fitz.open(stream=content, filetype="svg")
    if document.page_count == 0:
        raise ValueError("SVG has no drawable page")
    pixmap = document[0].get_pixmap(alpha=False)
    output = pixmap.tobytes("png")
    document.close()
    return ProcessedImage(
        content=output,
        filename=_clean_filename(filename, ".png"),
        media_type="image/png",
        metadata_removed=True,
        bytes_saved=0,
    )


def _render_pdf_to_png_zip(content: bytes, filename: str) -> ProcessedImage:
    document = fitz.open(stream=content, filetype="pdf")
    if document.page_count == 0:
        raise ValueError("PDF has no pages")

    stem = Path(filename or "document").stem or "document"
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            zf.writestr(f"{stem}-page-{index}.png", pixmap.tobytes("png"))
    document.close()
    archive.seek(0)

    return ProcessedImage(
        content=archive.getvalue(),
        filename=f"{stem}.png-pages.zip",
        media_type="application/zip",
        metadata_removed=True,
        bytes_saved=0,
        output_count=index,
    )


def process_image_file(
    content: bytes,
    filename: str,
    *,
    output_format: str | None = None,
    quality: int = 82,
) -> ProcessedImage:
    if not content:
        raise ValueError("Empty image file")

    extension = Path(filename or "").suffix.lower()
    if extension == ".svg":
        return _render_svg_to_png(content, filename)
    if extension == ".pdf":
        return _render_pdf_to_png_zip(content, filename)

    try:
        image = Image.open(io.BytesIO(content))
    except UnidentifiedImageError as exc:
        raise ValueError("Unsupported image file. Use PNG, JPG, WEBP, HEIC, SVG, or PDF.") from exc

    image.load()
    image = ImageOps.exif_transpose(image)

    pillow_format, extension, media_type = _infer_output(filename, output_format)
    normalized_quality = max(1, min(int(quality or 82), 95))

    if pillow_format in {"JPEG", "WEBP"} and image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")
    else:
        image = image.copy()

    output = io.BytesIO()
    save_kwargs: dict[str, object] = {}
    if pillow_format in {"JPEG", "WEBP"}:
        save_kwargs.update({"quality": normalized_quality, "optimize": True, "exif": b""})
    elif pillow_format == "PNG":
        save_kwargs.update({"optimize": True})

    image.save(output, format=pillow_format, **save_kwargs)
    processed = output.getvalue()

    return ProcessedImage(
        content=processed,
        filename=_clean_filename(filename, extension),
        media_type=media_type,
        metadata_removed=True,
        bytes_saved=max(len(content) - len(processed), 0),
    )
