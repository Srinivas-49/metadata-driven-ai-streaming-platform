"""Offline job DAG and notebook syntax, not Azure runtime execution."""
import ast
from pathlib import Path

def test_governance_and_validation_notebooks_are_python():
    for path in ("deployment/00_bootstrap_workspace.py", "deployment/90_validate_retrieval.py"):
        ast.parse(Path(path).read_text(encoding="utf-8"))

def test_paused_and_sequential_dag():
    text = Path("databricks.yml").read_text(encoding="utf-8")
    assert "pause_status: PAUSED" in text
    assert "new_cluster:" not in text and "existing_cluster_id:" not in text
    for task in ("bootstrap", "document_ingestion", "rank_and_evaluate", "validate_and_audit"):
        assert f"task_key: {task}" in text
    assert text.index("task_key: bootstrap") < text.index("task_key: document_ingestion")
    assert text.index("task_key: document_ingestion") < text.index("task_key: rank_and_evaluate")
    assert text.index("task_key: rank_and_evaluate") < text.index("task_key: validate_and_audit")
