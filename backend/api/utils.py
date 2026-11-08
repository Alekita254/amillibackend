from django.utils.text import slugify
from rest_framework.response import Response


def unique_slug(instance, source):
    """slugify(source), suffixed -2, -3... until unique for this model (SlugField max is 50)."""
    base = slugify(source)[:40] or "item"
    slug, n = base, 2
    qs = type(instance).objects.exclude(pk=instance.pk)
    while qs.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug

def custom_response(success=True, message="", data=None, status_code=200):
    return Response(
        {
            "success": success,
            "message": message,
            "data": data
        },
        status=status_code
    )


def first_error(detail):
    """Dig the first human-readable message out of a DRF ValidationError detail."""
    if isinstance(detail, dict):
        detail = next(iter(detail.values()), "")
    if isinstance(detail, (list, tuple)):
        detail = detail[0] if detail else ""
        return first_error(detail) if isinstance(detail, (dict, list, tuple)) else str(detail)
    return str(detail)


def error_response(exc, status_code=400):
    """Turn a ValidationError into the {success, message, data} shape the frontend reads."""
    return custom_response(
        success=False,
        message=first_error(exc.detail) or "Invalid data",
        data=exc.detail,
        status_code=status_code,
    )
