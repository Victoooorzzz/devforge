import io
import sys
import unittest
import zipfile
from pathlib import Path

from PIL import Image
from PIL.PngImagePlugin import PngInfo
import fitz
import pillow_heif

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "backend_core"))

from file_utilities import process_image_file


pillow_heif.register_heif_opener()


def _png_with_metadata() -> bytes:
    image = Image.new("RGB", (24, 24), color=(130, 19, 70))
    metadata = PngInfo()
    metadata.add_text("Author", "DevForge")
    metadata.add_text("GPS", "private-location")
    buf = io.BytesIO()
    image.save(buf, format="PNG", pnginfo=metadata)
    return buf.getvalue()


class FileImageToolsTests(unittest.TestCase):
    def test_strips_png_metadata_without_changing_format_by_default(self):
        processed = process_image_file(_png_with_metadata(), "photo.png")

        self.assertEqual(processed.filename, "photo.cleaned.png")
        self.assertEqual(processed.media_type, "image/png")
        self.assertEqual(processed.metadata_removed, True)

        image = Image.open(io.BytesIO(processed.content))
        self.assertEqual(image.format, "PNG")
        self.assertEqual(image.info, {})

    def test_corrupt_tiny_png_returns_actionable_error(self):
        corrupt_tiny_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\rIDATx\xdac\xfc\xcf\xc0P\x0f\x00\x05\x83"
            b"\x02\x7f\x97\xa8\t\xc5\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        with self.assertRaisesRegex(ValueError, "Unsupported or corrupt image file"):
            process_image_file(corrupt_tiny_png, "tiny.png")

    def test_converts_png_to_jpeg_with_rgb_output(self):
        processed = process_image_file(_png_with_metadata(), "photo.png", output_format="jpeg")

        self.assertEqual(processed.filename, "photo.cleaned.jpg")
        self.assertEqual(processed.media_type, "image/jpeg")
        image = Image.open(io.BytesIO(processed.content))
        self.assertEqual(image.format, "JPEG")
        self.assertEqual(image.mode, "RGB")

    def test_compresses_jpeg_when_quality_is_lowered(self):
        source = Image.new("RGB", (700, 700), color=(44, 112, 210))
        raw = io.BytesIO()
        source.save(raw, format="JPEG", quality=100)

        processed = process_image_file(raw.getvalue(), "hero.jpg", quality=45)

        self.assertEqual(processed.media_type, "image/jpeg")
        self.assertLess(len(processed.content), len(raw.getvalue()))
        self.assertGreater(processed.bytes_saved, 0)

    def test_converts_svg_to_png(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="32" height="16"><rect width="32" height="16" fill="#821346"/></svg>'

        processed = process_image_file(svg, "badge.svg")

        self.assertEqual(processed.filename, "badge.cleaned.png")
        self.assertEqual(processed.media_type, "image/png")
        image = Image.open(io.BytesIO(processed.content))
        self.assertEqual(image.format, "PNG")
        self.assertEqual(image.size, (32, 16))

    def test_converts_pdf_pages_to_png_zip(self):
        document = fitz.open()
        page = document.new_page(width=120, height=80)
        page.insert_text((16, 40), "DevForge")
        pdf = document.tobytes()
        document.close()

        processed = process_image_file(pdf, "brief.pdf")

        self.assertEqual(processed.filename, "brief.png-pages.zip")
        self.assertEqual(processed.media_type, "application/zip")
        with zipfile.ZipFile(io.BytesIO(processed.content)) as archive:
            self.assertEqual(archive.namelist(), ["brief-page-1.png"])
            image = Image.open(io.BytesIO(archive.read("brief-page-1.png")))
            self.assertEqual(image.format, "PNG")

    def test_converts_heic_to_jpeg(self):
        image = Image.new("RGB", (20, 20), color=(20, 80, 160))
        raw = io.BytesIO()
        image.save(raw, format="HEIF")

        processed = process_image_file(raw.getvalue(), "photo.heic", output_format="jpeg")

        self.assertEqual(processed.filename, "photo.cleaned.jpg")
        self.assertEqual(processed.media_type, "image/jpeg")
        converted = Image.open(io.BytesIO(processed.content))
        self.assertEqual(converted.format, "JPEG")


if __name__ == "__main__":
    unittest.main()
