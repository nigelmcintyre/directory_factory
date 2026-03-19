from django import template
from django.utils.safestring import mark_safe
import markdown

register = template.Library()

@register.filter
def markdownify(text):
    """Converts Markdown text to HTML."""
    return mark_safe(markdown.markdown(text, extensions=["extra", "codehilite", "nl2br", "sane_lists"]))
