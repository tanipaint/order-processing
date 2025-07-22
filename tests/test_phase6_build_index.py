import pickle

import pytest

from src.phase6.build_rag_index import load_docs, main
from src.phase6.vector_store import VectorStore


@pytest.fixture(autouse=True)
def prepare_docs(tmp_path, monkeypatch):
    # Create products.md and customers.md in cwd
    p1 = tmp_path / "products.md"
    p1.write_text("A\nB")
    p2 = tmp_path / "customers.md"
    p2.write_text("X\nY")
    monkeypatch.chdir(tmp_path)
    yield


def test_load_docs(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("a\n\nb", encoding="utf-8")
    lines = load_docs(str(f))
    assert lines == ["a", "b"]


def test_main_creates_index(tmp_path, monkeypatch):
    # Ensure embedding returns fixed vector
    class DummyEmbed:
        def embed_text(self, text):
            return [0.1] * 4

    monkeypatch.setenv("RAG_INDEX_PATH", str(tmp_path / "out.pkl"))
    # Patch embedder class
    import src.phase6.build_rag_index as bi

    monkeypatch.setattr(bi, "OpenAIEmbedder", lambda: DummyEmbed())
    main()
    out = tmp_path / "out.pkl"
    assert out.exists()
    vs = pickle.loads(out.read_bytes())
    assert isinstance(vs, VectorStore)
