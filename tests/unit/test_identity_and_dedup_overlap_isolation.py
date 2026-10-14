"""Garante, por inspeção de módulo (não só por execução), que dedup.py e overlap.py nunca
compartilham código — requisito explícito do plano (seção 11: 'auditável lendo o diff do
PR', aqui formalizado como teste que falha se alguém importar um módulo de dentro do outro)."""

import ast
import inspect

from app.domains.ingestion import dedup, overlap


def _imported_names(module) -> set[str]:
    source = inspect.getsource(module)
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
    return names


def _code_without_docstrings(module) -> str:
    """Código real, sem comentários/docstrings — para não confundir prosa explicativa
    (que cita os dois conceitos para documentar a separação) com acoplamento real."""
    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body[0] = ast.Pass()
    return ast.unparse(tree)


def test_dedup_and_overlap_never_import_each_other():
    assert "app.domains.ingestion.overlap" not in _imported_names(dedup)
    assert "app.domains.ingestion.dedup" not in _imported_names(overlap)


def test_dedup_only_touches_import_batch():
    code = _code_without_docstrings(dedup)
    assert "Dataset" not in code
    assert "ImportBatch" in code


def test_overlap_never_references_sha256_or_import_batch_table():
    code = _code_without_docstrings(overlap)
    assert "sha256" not in code
    assert "ImportBatch" not in code
