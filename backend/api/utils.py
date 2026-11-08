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
