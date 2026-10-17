from rest_framework.permissions import BasePermission

from .services import AGENT_GROUP, may, method_of, role_of

__all__ = ["AGENT_GROUP", "AgentPermission"]


class AgentPermission(BasePermission):
    """Who may do what. This is the SERVER's rule: it holds even if a client misbehaves.

    The rule the lab asks for:
      - a person (user with is_staff) can do anything;
      - a member of the group «agente» can read, create and modify, but NEVER delete;
      - anybody else who is logged in can only read;
      - an unknown method is denied (deny by default).

    The table itself lives in services.METHODS_BY_ROLE, so a future interface asks the same
    question and cannot answer it differently. Anonymous users are not decided here: DRF's
    IsAuthenticated already answers them with a 401, never a 403.
    """

    def has_permission(self, request, view):
        return may(role_of(getattr(request, "user", None)), method_of(request, view))