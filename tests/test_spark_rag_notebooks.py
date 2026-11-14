"""Validate offline syntax and presence of retrieval boundaries."""
import ast
from pathlib import Path

def test_pyspark_rag_notebook_syntax():
    for name in ("01_spark_document_ingestion.py", "02_spark_retrieval_evaluation.py"):
        ast.parse((Path("notebooks") / name).read_text(encoding="utf-8"))

def test_acls_and_citations_in_training_notebook():
    content = (Path("notebooks") / "02_spark_retrieval_evaluation.py").read_text()
    for required in ("authorized = corpus.filter", "gold_retrieval_evaluation",
                     "citation", "unauthorized_result", "false_positive",
                     "assert retrieve(\"Delta Lake\", set()) == []"):
        assert required in content
