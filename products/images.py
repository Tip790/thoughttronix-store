"""Product images: decoding uploads safely and normalizing what we store.

Shared by ``ProductForm.clean_image`` (employee uploads) and the ``seed``
command, so every stored product image takes the same path: decoded by
Pillow, downscaled, and re-encoded as WebP without its metadata.
"""

import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import IO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

# Pillow format names we accept. MPO is the multi-picture JPEG many
# phone cameras write; it decodes as an ordinary JPEG.
ACCEPTED_FORMATS = {"JPEG", "MPO", "PNG", "WEBP"}

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MIN_SIDE = 400
MAX_SIDE = 1200
WEBP_QUALITY = 85

# ISO base media "ftyp" brands that mean HEIC/HEIF — the iPhone default,
# which Pillow can't open without a plugin we deliberately don't install.
HEIC_BRANDS = {b"heic", b"heix", b"heim", b"heis", b"hevc", b"hevx", b"mif1", b"msf1"}


@contextmanager
def strict_decoding() -> Iterator[None]:
    """Raise Pillow's decompression-bomb warning as an error inside the block.

    Pillow only *warns* about images past its pixel limit (and raises
    ``DecompressionBombError`` at twice it); under this context both stop
    the decode, so a hostile upload can't exhaust memory.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        yield


def sniff_format(file: IO[bytes]) -> str | None:
    """Name a picture format Pillow can't open, from the file's first bytes.

    Returns ``"HEIC"`` or ``"SVG"`` when recognized, else ``None``.
    """
    file.seek(0)
    head = file.read(1024)
    if head[4:8] == b"ftyp" and head[8:12] in HEIC_BRANDS:
        return "HEIC"
    if b"<svg" in head.lower():
        return "SVG"
    return None


def normalize_image(file: IO[bytes], name: str) -> ContentFile:
    """Return ``file`` re-encoded the way the store keeps product images.

    The image is turned upright (per its EXIF orientation), shrunk so its
    longest side is at most ``MAX_SIDE`` pixels (never enlarged), and
    re-encoded as WebP at ``WEBP_QUALITY``. Metadata — EXIF, GPS, XMP,
    ICC profile — is not carried over, and the original is not kept.

    ``file`` should already have passed ``ProductForm.clean_image``'s
    checks; ``name`` supplies the stem of the returned ``.webp`` file name.
    """
    file.seek(0)
    with strict_decoding(), Image.open(file) as source:
        picture = ImageOps.exif_transpose(source)
    picture.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    has_alpha = picture.mode in ("RGBA", "LA", "PA") or (
        picture.mode == "P" and "transparency" in picture.info
    )
    picture = picture.convert("RGBA" if has_alpha else "RGB")
    picture.info = {}  # nothing from the source rides along into the WebP

    buffer = BytesIO()
    picture.save(buffer, "WEBP", quality=WEBP_QUALITY)
    return ContentFile(buffer.getvalue(), name=f"{Path(name).stem}.webp")
