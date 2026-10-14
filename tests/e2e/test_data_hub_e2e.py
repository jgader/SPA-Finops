"""E2E real contra API+worker+SPA rodando (requer os 3 processos ativos — ver
docs/PLANO_EXECUCAO_F1.md seção 'instruções locais' / README de execução). Marcado para
rodar separado da suíte rápida: exige ambiente completo de pé, não roda em CI sem setup."""

import os

import pytest

pytestmark = pytest.mark.e2e

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "..", "packages", "fixtures", "data")
CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


@pytest.fixture
def page():
    pw_sync = pytest.importorskip("playwright.sync_api")
    with pw_sync.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM_PATH)
        pg = browser.new_page()
        yield pg
        browser.close()


def test_happy_path_upload_shows_committed_status_and_dataset_row(page):
    page.goto("http://127.0.0.1:5173/")
    page.wait_for_selector("text=FinOps AI")
    page.set_input_files("input[type=file]", os.path.join(FIXTURES, "focus_clean_baseline.csv"))
    page.wait_for_selector("text=/\\[Comitado\\]/", timeout=20000)
    body = page.inner_text("body")
    assert "azure:demo-sub-0001:cost_and_usage" in body


def test_malformed_upload_shows_rejection_table_with_accessible_text_labels(page):
    page.goto("http://127.0.0.1:5173/")
    page.wait_for_selector("text=FinOps AI")
    page.set_input_files("input[type=file]", os.path.join(FIXTURES, "focus_malformed.csv"))
    page.wait_for_selector("text=/\\[Rejeitado/", timeout=20000)
    body = page.inner_text("body")
    # Acessibilidade: a severidade nunca aparece só como cor — tem texto explícito.
    assert "Erro — bloqueia o commit" in body
    assert "missing_required_field" in body


def test_placeholder_areas_never_show_fake_data(page):
    page.goto("http://127.0.0.1:5173/")
    page.click("text=Cockpit")
    body = page.inner_text("body")
    assert "desenvolvimento" in body.lower()  # inner_text aplica text-transform: uppercase do CSS
    assert "R$" not in body  # nenhum valor monetário inventado
