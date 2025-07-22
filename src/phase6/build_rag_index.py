"""Phase6: 辞書ファイルをベクトル化して Faiss インデックスを構築・保存するスクリプト"""
import os
import pickle

from src.phase6.embedding import OpenAIEmbedder
from src.phase6.vector_store import VectorStore


def load_docs(path: str) -> list[str]:
    """ファイルを読み込み、空行を除く行リストを返す"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dictionary file not found: {path}")
    with open(path, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines


def main():
    # 辞書ファイルとして products.md と customers.md を想定
    docs = []
    for fname in ("products.md", "customers.md"):
        entries = load_docs(fname)
        docs.append("\n".join(entries))

    embedder = OpenAIEmbedder()
    vs = VectorStore(embedder)
    vs.build(docs)
    # Drop embedder before pickling (stub embedder may not be picklable)
    vs.embedder = None

    out_path = os.getenv("RAG_INDEX_PATH", "rag_index.pkl")
    with open(out_path, "wb") as f:
        pickle.dump(vs, f)
    print(f"RAG index saved to {out_path}")


if __name__ == "__main__":
    main()
