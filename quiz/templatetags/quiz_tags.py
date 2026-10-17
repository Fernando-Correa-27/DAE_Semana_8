"""Small helpers the templates need and Django does not provide on its own.

They exist to keep the accessibility wiring in one place: a screen reader only
announces the errors of a field if the input points at them, and an id that the
formset computes per row cannot be hardcoded in the form.
"""
from django import template

register = template.Library()


@register.simple_tag
def render_field(field):
    """Render one field with the ARIA hooks its own errors and help text need.

    ``aria-describedby`` points at the inline error list and at the help text
    when they exist, and ``aria-invalid`` is added only when there is an error.
    """
    described_by = []
    attrs = {}
    if field.help_text:
        described_by.append(f"{field.id_for_label}-help")
    if field.errors:
        described_by.append(f"{field.id_for_label}-error")
        attrs["aria-invalid"] = "true"
    if described_by:
        attrs["aria-describedby"] = " ".join(described_by)
    return field.as_widget(attrs=attrs)