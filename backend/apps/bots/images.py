"""Validation and normalization of bot avatar/banner uploads."""

from __future__ import annotations

import io

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}
SIZES = {
    "avatar": (128, 128),
    "banner": (600, 240),
}


def normalize_image(upload, kind: str) -> ContentFile:
    if upload.size > MAX_UPLOAD_BYTES:
        raise serializers.ValidationError("Image must be 2 MB or smaller")
    if kind not in SIZES:
        raise serializers.ValidationError("Unknown image kind")
    try:
        image = Image.open(upload)
        image.verify()
        upload.seek(0)
        image = Image.open(upload)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise serializers.ValidationError("Unsupported image file") from exc
    if image.format not in ALLOWED_FORMATS:
        raise serializers.ValidationError("Only PNG, JPEG and WebP images are allowed")
    if image.width < 32 or image.height < 32:
        raise serializers.ValidationError("Image is too small")
    image = ImageOps.exif_transpose(image)
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGBA")
    image = ImageOps.fit(image, SIZES[kind], method=Image.Resampling.LANCZOS)
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return ContentFile(output.getvalue(), name=f"{kind}.png")


def set_bot_image(bot, kind: str, upload) -> None:
    field_name = kind
    old_file = getattr(bot, field_name)
    if old_file:
        old_file.delete(save=False)
    normalized = normalize_image(upload, kind)
    getattr(bot, field_name).save(normalized.name, normalized, save=False)
    bot.save(update_fields=[field_name, "updated_at"])


def clear_bot_image(bot, kind: str) -> None:
    field_name = kind
    old_file = getattr(bot, field_name)
    if old_file:
        old_file.delete(save=False)
    setattr(bot, field_name, None)
    bot.save(update_fields=[field_name, "updated_at"])
