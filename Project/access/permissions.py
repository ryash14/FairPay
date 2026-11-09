"""The sign-in and access guard every protected endpoint sits behind.

The service decides what each role may reach; the dashboard hiding a page is
a courtesy, not the control.
"""
from typing import Annotated, Optional

from fastapi import Header, HTTPException, Request

from config import config
from persistence import repository
from persistence.database import session_factory
from persistence.models import UserAccount
from tools.messages import fill_template


def resolve_area(path, method):
    """The area a request belongs to: a POST ending in the decision path is the decision area."""
    if method.upper() == "POST" and path.rstrip("/").endswith(config.DECISION_PATH_ENDING):
        return config.AREA_DECISION
    for prefix, area in config.AREA_BY_PATH_START.items():
        if path.startswith(prefix):
            return area
    return None


def authorize_request(request: Request,
                      session_token: Annotated[Optional[str], Header(alias=config.SESSION_TOKEN_HEADER)] = None):
    """Who is asking, and whether their role reaches this area; 401 or 403 before the endpoint runs."""
    account = None
    if session_token:
        with session_factory() as session:
            account = repository.fetch_user_account(session, UserAccount.session_token == session_token)
    if account is None:
        raise HTTPException(status_code=401, detail=config.SIGN_IN_REQUIRED_MESSAGE)
    area = resolve_area(request.url.path, request.method)
    if area not in config.ROLE_AREA_ACCESS.get(account["role"], []):
        raise HTTPException(status_code=403, detail=fill_template(
            config.AREA_REFUSED_MESSAGE, account["role"], area, role=account["role"], role_name=account["role"],
            area=area, area_name=area))
    return account
