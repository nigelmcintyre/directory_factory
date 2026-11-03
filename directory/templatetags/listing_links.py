from django import template

from directory import links

register = template.Library()

register.filter("link_type", links.link_type)
register.filter("with_utm", links.with_utm)
