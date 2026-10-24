from io import BytesIO
from pathlib import Path
from typing import IO

from PIL import Image


def save_to_jpeg(image_data: IO, filename: str | Path) -> None:
    input_image = Image.open(image_data)

    if input_image.mode in ("RGBA", "P"):
        input_image = input_image.convert("RGB")

    input_image.save(filename, format="JPEG")


def bytes_to_jpeg(image_data: bytes, width: int | None, height: int | None) -> bytes:
    input_buffer = BytesIO(image_data)

    input_image = Image.open(input_buffer)
    original_width, original_height = input_image.size

    if width and height:
        size = (width, height)
    elif width:
        size = (width, int(original_height * width / original_width))
    elif height:
        size = (int(original_width * height / original_height), height)
    else:
        size = (original_width, original_height)

    output_image = input_image.resize(size)

    output_buffer = BytesIO()
    output_image.save(output_buffer, format="JPEG")

    image_data = output_buffer.getvalue()
    return image_data
