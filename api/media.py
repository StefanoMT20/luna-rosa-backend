from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image


def save_resized_image(file, path: str, max_size: int = 1200, quality: int = 82) -> str:
    """Redimensiona, comprime a JPEG y guarda en el storage activo (R2 o disco).

    Misma transformacion que ProductPhoto.save(): lado maximo max_size,
    JPEG calidad quality. Se usa para fotos que no son de Product (por
    ejemplo, items de un pedido al mayorista) y por eso no pasan por un
    ImageField propio; el resultado es la URL final, ya en el storage.
    """
    img = Image.open(file)
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    buffer.seek(0)

    saved_path = default_storage.save(path, ContentFile(buffer.read()))
    return default_storage.url(saved_path)
