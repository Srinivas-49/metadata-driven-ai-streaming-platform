from src.metadata_rag import ingest, answer, evaluate
import json

corpus = ingest("data/config.json")
print(json.dumps(answer("What is the purpose of Delta Lake?", corpus), indent=2))
print(json.dumps(evaluate("data/config.json", "data/evaluation.json"), indent=2))
