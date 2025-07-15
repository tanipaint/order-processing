"""Phase6: FAISSベースのベクトルストア実装"""
from typing import Any, List

import numpy as np

try:
    import faiss
except ImportError:
    faiss = None


class VectorStore:
    """テキストコレクションからベクトルインデックスを構築し、類似検索を行うクラス"""

    def __init__(self, embedder: Any):
        """
        :param embedder: embed_text(text: str) -> List[float] を提供する埋め込み器
        """
        self.embedder = embedder
        self.index = None
        self.docs: List[str] = []
        self.embeddings: List[np.ndarray] = []

    def build(self, docs: List[str]) -> None:
        """ドキュメントリストを受け取り、FAISSインデックスを構築する"""
        self.docs = docs
        if not docs:
            self.index = None
            self.docs = []
            self.embeddings = []
            return
        # 埋め込み取得
        raw_embs = [self.embedder.embed_text(d) for d in docs]
        arr = np.array(raw_embs, dtype="float32")
        self.embeddings = [arr[i] for i in range(arr.shape[0])]
        if faiss:
            dim = arr.shape[1]
            self.index = faiss.IndexFlatL2(dim)
            self.index.add(arr)
        else:
            self.index = None

    def query(self, text: str, top_k: int = 1) -> List[str]:
        """クエリテキストとの類似度検索を行い、上位 top_k のドキュメントを返す"""
        qvec_raw = self.embedder.embed_text(text)
        query_vec = np.array(qvec_raw, dtype="float32")
        if self.index is not None:
            vec = np.array([query_vec], dtype="float32")
            _, idxs = self.index.search(vec, top_k)
            idxs = idxs[0]
        else:
            # brute-force search
            dists = [np.linalg.norm(query_vec - emb) for emb in self.embeddings]
            idxs = np.argsort(dists)[:top_k]
        results: List[str] = []
        for i in idxs:
            if 0 <= i < len(self.docs):
                results.append(self.docs[i])
        return results
