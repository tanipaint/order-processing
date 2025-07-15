"""Phase6: OpenAI Embedding API のラッパー"""
import os

import openai


class OpenAIEmbedder:
    """OpenAI Embedding API を使ってテキストをベクトルに変換するラッパー"""

    def __init__(self, model: str = "text-embedding-ada-002"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY environment variable")
        openai.api_key = api_key
        self.model = model

    def embed_text(self, text: str) -> list[float]:
        resp = openai.Embedding.create(model=self.model, input=text)
        return resp["data"][0]["embedding"]
