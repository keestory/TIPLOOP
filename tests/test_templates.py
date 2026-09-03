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
    assert "clearLocalAuthState" in rendered
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
def test_question_picker_uses_modal_sheet_without_in_flow_details_reflow():
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "post_write.html").read_text(encoding="utf-8")
    javascript = (root / "static" / "research-form.js").read_text(encoding="utf-8")
    css = (root / "static" / "tipping.css").read_text(encoding="utf-8")

    assert '<dialog class="question-sheet" id="question-picker"' in template
    assert '<details class="question-picker"' not in template
    assert "picker.showModal()" in javascript
    assert "syncSelectedCount()" in javascript
    assert "picker.addEventListener('close'" in javascript
    assert ".question-sheet[open] { display: flex; }" in css
    assert ".ta, .field select, .searchbar input, .share-url { font-size: 16px; }" in css


@pytest.mark.no_db
def test_research_form_restores_legacy_application_draft():
    root = Path(__file__).resolve().parents[1]
    javascript = (root / "static" / "research-form.js").read_text(encoding="utf-8")

    assert "field.dataset.questionId === 'ref.next_action'" in javascript
    assert "draft.values['실제로 적용할 것']" in javascript


@pytest.mark.no_db
def test_research_share_native_share_does_not_append_copy_to_url():
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "research_share.html").read_text(
        encoding="utf-8"
    )

    assert "navigator.share({ title: title, url: url })" in template
    assert "함께 보고 싶은 서비스 분석이에요." not in template


@pytest.mark.no_db
def test_app_store_account_controls_and_legal_pages_are_present():
    root = Path(__file__).resolve().parents[1]
    profile = (root / "templates" / "profile.html").read_text(encoding="utf-8")
    privacy = (root / "templates" / "legal_privacy.html").read_text(encoding="utf-8")
    service = (root / "templates" / "legal_service.html").read_text(encoding="utf-8")
    support = (root / "templates" / "support.html").read_text(encoding="utf-8")

    assert 'id="open-delete-account"' in profile
    assert "계정과 데이터 삭제" in profile
    assert "스크린샷·영상" in profile
    assert "/account/delete" in profile
    assert "/support" in privacy
    assert "운영자명]" not in privacy
    assert "운영자명]" not in service
    assert "계정 삭제" in support


@pytest.mark.no_db
def test_native_auth_uses_tiploop_callback_scheme_consistently():
    root = Path(__file__).resolve().parents[1]
    login = (root / "templates" / "login.html").read_text(encoding="utf-8")
    bridge = (root / "static" / "native-auth.js").read_text(encoding="utf-8")
    info_plist = (root / "mobile" / "ios" / "App" / "App" / "Info.plist").read_text(
        encoding="utf-8"
    )

    assert "tiploop://auth-callback" in login
    assert 'parsed.protocol === "tiploop:"' in bridge
    assert "<string>tiploop</string>" in info_plist
    assert "tipping://auth-callback" not in login


@pytest.mark.no_db
def test_login_does_not_offer_removed_kakao_provider():
    root = Path(__file__).resolve().parents[1]
    login = (root / "templates" / "login.html").read_text(encoding="utf-8")

    assert "카카오" not in login
    assert "login('kakao')" not in login
    assert 'id="kakao"' not in login


@pytest.mark.no_db
def test_native_auth_uses_pkce_session_exchange_and_cold_start_callback():
    root = Path(__file__).resolve().parents[1]
    login = (root / "templates" / "login.html").read_text(encoding="utf-8")
    mobile = (root / "templates" / "mobile.html").read_text(encoding="utf-8")

    assert "flowType: 'pkce'" in login
    assert "sb.auth.exchangeCodeForSession(code)" in login
    assert "params.get('code')" in login
    assert "flowType: 'implicit'" not in login
    assert "appPlugin.getLaunchUrl()" in login
    assert "tiploop.authLaunchUrlChecked" in login
    assert "tiploop:auth-url" in login
    assert '/static/native-auth.js?v=2' in mobile


@pytest.mark.no_db
def test_account_delete_dialog_has_pre_ios_15_4_fallback():
    root = Path(__file__).resolve().parents[1]
    profile = (root / "templates" / "profile.html").read_text(encoding="utf-8")
    css = (root / "static" / "tipping.css").read_text(encoding="utf-8")

    assert "typeof dialog.showModal === 'function'" in profile
    assert "dialog.setAttribute('open', '')" in profile
    assert 'id="close-delete-account"' in profile
    assert ".account-delete-dialog.fallback-open" in css


@pytest.mark.no_db
def test_account_delete_clears_only_this_projects_local_auth_state():
    root = Path(__file__).resolve().parents[1]
    profile = (root / "templates" / "profile.html").read_text(encoding="utf-8")
    bridge = (root / "static" / "native-auth.js").read_text(encoding="utf-8")

    assert "clearLocalAuthState" in profile
    assert 'localStorage.removeItem("sb-" + projectRef + "-auth-token")' in bridge
    assert "localStorage.clear" not in bridge
