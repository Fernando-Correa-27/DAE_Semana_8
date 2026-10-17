"""Access rules and feedback helpers of the web interface.

Identity and authorisation are asked to ``quiz.services``, where the role table
lives. No view and no mixin is allowed to grow its own ``if user.is_staff``
branch: that would be a second copy of a rule the API already applies.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from . import services


class StaffRequiredMixin(LoginRequiredMixin):
    """The interface is for the person: a Django session and the «person» role.

    The order is what matters. An anonymous visitor is nobody, so
    ``LoginRequiredMixin`` redirects it to the login page (302). A logged-in
    user that is not the person is somebody without permission, so it gets a 403.
    Never the other way round. Who the person is, is decided by
    ``services.role_of`` and not here.
    """

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and not services.may_use(user, request.method):
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