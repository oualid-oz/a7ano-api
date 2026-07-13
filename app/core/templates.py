from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _base_context() -> dict[str, object]:
    return {
        "app_name": settings.app_name,
        "app_url": settings.app_url,
        "year": datetime.now(UTC).year,
    }


def render_verify_email(full_name: str, link: str) -> str:
    template = _env.get_template("verify_email.html")
    return template.render(**_base_context(), full_name=full_name, link=link)


def render_reset_password(full_name: str, link: str) -> str:
    template = _env.get_template("reset_password.html")
    return template.render(**_base_context(), full_name=full_name, link=link)


def render_welcome(full_name: str) -> str:
    template = _env.get_template("welcome.html")
    return template.render(**_base_context(), full_name=full_name)


def render_organization_invitation(
    inviter_name: str,
    organization_name: str,
    role_name: str,
    link: str,
) -> str:
    template = _env.get_template("organization_invitation.html")
    return template.render(
        **_base_context(),
        inviter_name=inviter_name,
        organization_name=organization_name,
        role_name=role_name,
        link=link,
    )
