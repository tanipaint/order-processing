"""Phase2: LLM抽出プロンプト設計＆呼び出しラッパー（スタブ実装）"""
import json
import os
import re

import openai


def extract_order_fields(text: str) -> dict:
    """
    LLM 呼び出し版: メール本文テキストから必須フィールドを JSON で抽出します。
    抽出項目: customer_name, product_id, quantity, delivery_date
    """
    # テスト環境などで API キー未設定の場合は正規表現スタブを利用
    if not os.getenv("OPENAI_API_KEY"):
        # 戻り値フォーマット互換のため旧スタブ実装
        data: dict = {}
        m = re.search(r"顧客[:：]\s*(.+)", text)
        if m:
            data["customer_name"] = m.group(1).strip()
        m = re.search(r"商品[:：]\s*([A-Za-z0-9]+)", text)
        if m:
            data["product_id"] = m.group(1).strip()
        m = re.search(r"数量[:：]\s*(\d+)", text)
        if m:
            data["quantity"] = int(m.group(1))
        m = re.search(r"配送希望日[:：]\s*([\d\-]+)", text)
        if m:
            data["delivery_date"] = m.group(1).strip()
        return data
    openai.api_key = os.getenv("OPENAI_API_KEY")
    prompt = f"""
あなたは注文受付システムのアシスタントです。
以下のメール本文から、必ず JSON で「customer_name, product_id, quantity, delivery_date」の４項目を抽出してください。

【本文】
{text}

例:
入力: 「ご注文者様: 山田屋、商品:A001、個数:3、お届け希望日:2025-07-20」
出力: {{"customer_name":"山田屋","product_id":"A001","quantity":3,"delivery_date":"2025-07-20"}}

---- この形式で JSON を返してください ----
"""
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "JSON 出力専用モード"},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    text_out = resp.choices[0].message.content.strip()
    try:
        # JSON以外の文字列を削除するための正規表現
        json_match = re.search(r"\{.*?\}", text_out, re.DOTALL)
        if json_match:
            cleaned_json = json_match.group(0)
        else:
            raise ValueError("JSON形式が見つかりませんでした")
        # JSON部分のみをパースして返却
        return json.loads(cleaned_json)
    except Exception as e:
        # デバッグ用にLLMレスポンス全体を出力
        print(f"LLM レスポンス全体: {text_out}")
        print(f"整形後のJSON: {cleaned_json}")
        raise ValueError(f"LLM レスポンスの JSON パース失敗: {e}\n>> {cleaned_json}")
