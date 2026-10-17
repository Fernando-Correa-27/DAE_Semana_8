"""Access rules and feedback helpers of the web interface.

Identity and authorisation are decided here, once. No view is allowed to grow
its own ``if user.is_staff`` branch.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class StaffRequiredMixin(LoginRequiredMixin):
    """The interface is for the person: a Django session **and** ``is_staff``.

    The order is what matters. An anonymous visitor is nobody, so
    ``LoginRequiredMixin`` redirects it to the login page (302). A logged-in
    user that is not staff is somebody without permission, so it gets a 403.
    Never the other way round.
    """

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and not user.is_staff:
            raise PermissionDenied("Esta interfaz es para el profesorado.")
        return super().dispatch(request, *args, **kwargs)


class SuccessMessageMixin:
    """Tell the user what happened, after the redirect of the POST/redirect pattern."""

    success_message = ""

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message.format(**self.get_success_context()))
        return response

    def get_success_context(self):
        """Words the message may need, e.g. ``title`` of the object just saved."""
        return {}