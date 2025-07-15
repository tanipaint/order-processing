"""Phase6: RAG パイプラインと表記揺れ補正ロジック"""
import os
from typing import Any, List

import openai


class RAGPipeline:
    """Retrieval-Augmented Generation を使った正規化パイプライン"""

    def __init__(self, vector_store: Any, llm_model: str = "gpt-3.5-turbo"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY environment variable")
        openai.api_key = api_key
        self.vector_store = vector_store
        self.llm_model = llm_model

    def _format_prompt(
        self, template: str, retrieved: List[str], user_input: str
    ) -> str:
        docs = "\n".join(retrieved)
        return template.format(retrieved_docs=docs, user_input=user_input)

    def correct_product_name(self, user_input: str) -> str:
        """ユーザー入力の商品名を正規化し、商品IDを返す"""
        retrieved = self.vector_store.query(user_input, top_k=5)
        template = (
            "以下の商品マスタ辞書を参考に、ユーザー入力の商品名を正規化してください。\n"
            "商品リスト:\n{retrieved_docs}\n"
            "ユーザー入力: {user_input}\n"
            "正規化された商品IDを返してください。"
        )
        prompt = self._format_prompt(template, retrieved, user_input)
        resp = openai.ChatCompletion.create(
            model=self.llm_model,
            messages=[{"role": "system", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()

    def correct_customer_name(self, user_input: str) -> str:
        """ユーザー入力の顧客名を正規化し、顧客マスタの名前を返す"""
        retrieved = self.vector_store.query(user_input, top_k=5)
        template = (
            "以下の顧客マスタ辞書を参考に、ユーザー入力の顧客名を正規化してください。\n"
            "顧客リスト:\n{retrieved_docs}\n"
            "ユーザー入力: {user_input}\n"
            "正規化された顧客名を返してください。"
        )
        prompt = self._format_prompt(template, retrieved, user_input)
        resp = openai.ChatCompletion.create(
            model=self.llm_model,
            messages=[{"role": "system", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()
