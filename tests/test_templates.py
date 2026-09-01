"""Jinja 템플릿의 정적 컴파일 검증."""

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader


@pytest.mark.no_db
def test_all_templates_compile():
    root = Path(__file__).resolve().parents[1]
    env = Environment(loader=FileSystemLoader(root / "templates"), autoescape=True)
    for name in env.list_templates(extensions=("html",)):
        env.get_template(name)


@pytest.mark.no_db
def test_logout_template_clears_supabase_browser_session():
    root = Path(__file__).resolve().parents[1]
    env = Environment(loader=FileSystemLoader(root / "templates"), autoescape=True)
    rendered = env.get_template("logout.html").render(
        current_user=None,
        supabase_url="https://project.supabase.co",
        supabase_anon_key="publishable",
    )
    assert "auth.signOut" in rendered
    assert "location.replace('/login')" in rendered
