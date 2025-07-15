import pytest

from src.phase6.embedding import OpenAIEmbedder
from src.phase6.rag_pipeline import RAGPipeline
from src.phase6.vector_store import VectorStore


class DummyEmbedder:
    """文字数をベクトルとして返すダミー埋め込み器"""

    def embed_text(self, text: str) -> list[float]:
        # 1次元ベクトルとして文字数を用いる
        return [float(len(text))]


class DummyLLM:
    @staticmethod
    def create(model, messages):
        # モック ChatCompletion.create
        class Choice:
            class Message:
                def __init__(self, content):
                    self.content = content

            def __init__(self):
                self.message = Choice.Message("normalized")

        return type("Resp", (), {"choices": [Choice()]})


@pytest.fixture(autouse=True)
def patch_openai(monkeypatch):
    # モック embedder はテスト内で置き換えるため、OpenAIEmbedder.embed_text は呼ばれない
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(OpenAIEmbedder, "embed_text", lambda self, t: [float(len(t))])
    monkeypatch.setattr(
        __import__("openai").ChatCompletion,
        "create",
        DummyLLM.create,
    )


def test_vector_store_query():
    docs = ["aaa", "bb", "c"]
    store = VectorStore(embedder=DummyEmbedder())
    store.build(docs)
    # クエリ "dddd" は長さ4 -> 最も近い長さを持つ "aaa" を返す
    res = store.query("dddd", top_k=1)
    assert res == ["aaa"]


def test_rag_pipeline_correct_product_name(monkeypatch):
    # モック VectorStore.query
    vs = VectorStore(embedder=DummyEmbedder())
    monkeypatch.setattr(vs, "query", lambda text, top_k=5: ["A001"])
    rag = RAGPipeline(vector_store=vs, llm_model="dummy-model")
    result = rag.correct_product_name("ノートPC")
    assert result == "normalized"


def test_rag_pipeline_correct_customer_name(monkeypatch):
    vs = VectorStore(embedder=DummyEmbedder())
    monkeypatch.setattr(vs, "query", lambda text, top_k=5: ["山田商店"])
    rag = RAGPipeline(vector_store=vs, llm_model="dummy-model")
    result = rag.correct_customer_name("Yamada Store")
    assert result == "normalized"
