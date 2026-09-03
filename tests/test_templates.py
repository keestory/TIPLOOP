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


@pytest.mark.no_db
def test_empty_state_link_color_does_not_override_primary_button():
    root = Path(__file__).resolve().parents[1]
    css = (root / "static" / "tipping.css").read_text(encoding="utf-8")

    assert ".empty a:not(.btn)" in css
    assert ".empty a {" not in css


@pytest.mark.no_db
def test_research_form_dismisses_mobile_keyboard_without_blocking_interactions():
    root = Path(__file__).resolve().parents[1]
    javascript = (root / "static" / "research-form.js").read_text(encoding="utf-8")

    assert "function isKeyboardInput" in javascript
    assert "if (!isKeyboardInput(event.target)) dismissKeyboard()" in javascript
    assert "deltaY >= 48 && deltaY > Math.abs(deltaX)" in javascript
    assert "document.addEventListener('pointerdown'" in javascript
    assert "document.addEventListener('touchend'" in javascript
    assert javascript.count("{ passive: true }") >= 4


@pytest.mark.no_db
def test_research_share_native_share_does_not_append_copy_to_url():
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "research_share.html").read_text(
        encoding="utf-8"
    )

    assert "navigator.share({ title: title, url: url })" in template
    assert "함께 보고 싶은 서비스 분석이에요." not in template
