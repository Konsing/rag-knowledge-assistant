import importlib.util
from pathlib import Path


backend_root = Path(__file__).parents[1]
eval_path = backend_root / "eval" / "eval_retrieval.py"
if not eval_path.exists():
    eval_path = backend_root.parent / "eval" / "eval_retrieval.py"
spec = importlib.util.spec_from_file_location("eval_retrieval", eval_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_check_hit_is_case_insensitive():
    results = [{"text": "A HUMAN study", "metadata": {"section_title": "Results"}}]
    assert module.check_hit(results, ["human"])


def test_check_hit_does_not_count_unrelated_results():
    results = [{"text": "Optimization details", "metadata": {"section_title": "Methods"}}]
    assert not module.check_hit(results, ["human", "annotator"])
