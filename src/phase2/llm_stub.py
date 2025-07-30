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
    # PDF請求書の表形式明細を先に解析: 複数商品明細対応
    data: dict = {}
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if "商品" in line and "数量" in line:
            items = []
            for row in lines[idx + 1 :]:  # noqa: E203
                row_s = row.strip()
                if not row_s or row_s.startswith("合計"):
                    break
                cols = row_s.split()
                if len(cols) < 2:
                    continue
                pid, qty_str = cols[0], cols[1]
                try:
                    qty = int(qty_str)
                except ValueError:
                    continue
                items.append({"product_id": pid, "quantity": qty})
            if items:
                # 顧客名抽出
                m = re.search(r"顧客[:：]\s*(.+)", text)
                if m:
                    data["customer_name"] = m.group(1).strip()
                # 配送希望日抽出
                m = re.search(r"配送希望日[:：]\s*([\d\-]+)", text)
                if m:
                    data["delivery_date"] = m.group(1).strip()
                data["items"] = items
                return data
    # 日本語ヘッダーで抽出できない場合の汎用テーブル抽出 (英語PDF対応)
    # 各行を「コード 数量」の2トークンで解析
    generic_items = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) == 2 and parts[0].isalnum() and parts[1].isdigit():
            generic_items.append({"product_id": parts[0], "quantity": int(parts[1])})
    if generic_items:
        return {"items": generic_items}
    # テーブル抽出対象でない場合、環境変数で切り替え
    if not os.getenv("OPENAI_API_KEY"):
        # 戻り値フォーマット互換のため旧スタブ実装
        data: dict = {}
        # PDF請求書テーブル形式対応: ヘッダー行「商品名 数量」以降をパース
        lines = text.splitlines()
        for idx, line in enumerate(lines):
            if "商品名" in line and "数量" in line:
                items = []
                for row in lines[idx + 1 :]:  # noqa: E203
                    if row.strip().startswith("合計"):
                        break
                    cols = row.strip().split()
                    if len(cols) >= 2:
                        pid = cols[0]
                        try:
                            qty = int(cols[1])
                        except ValueError:
                            continue
                        items.append({"product_id": pid, "quantity": qty})
                if items:
                    data["items"] = items
                    return data
        # 抽出: 顧客名, 配送希望日
        m = re.search(r"顧客[:：]\s*(.+)", text)
        if m:
            data["customer_name"] = m.group(1).strip()
        m = re.search(r"配送希望日[:：]\s*([\d\-]+)", text)
        if m:
            data["delivery_date"] = m.group(1).strip()
        # 複数商品の場合は items リストを返却
        products = re.findall(r"商品[:：]\s*([A-Za-z0-9]+)", text)
        quantities = re.findall(r"数量[:：]\s*(\d+)", text)
        if len(products) > 1 and len(quantities) == len(products):
            items = []
            for pid, qty in zip(products, quantities):
                items.append({"product_id": pid.strip(), "quantity": int(qty)})
            data["items"] = items
            return data
        # 単一商品の場合: 既存フォーマット
        # product_id, quantity を一つずつ抽出
        m = re.search(r"商品[:：]\s*([A-Za-z0-9]+)", text)
        if m:
            data["product_id"] = m.group(1).strip()
        m = re.search(r"数量[:：]\s*(\d+)", text)
        if m:
            data["quantity"] = int(m.group(1))
        return data
    openai.api_key = os.getenv("OPENAI_API_KEY")
    prompt = f"""
あなたは注文受付システムのアシスタントです。
以下のメール本文から、必ず JSON で抽出結果を返してください。
商品が複数ある場合は、`items` リストとして
  [{{"product_id":string,"quantity":number}}, ...]
として返却し、`customer_name` と `delivery_date` も含めてください。

【本文】
{text}

例1: 単一商品
入力: 「ご注文者様: 山田屋、商品:A001、個数:3、お届け希望日:2025-07-20」
出力: {{"customer_name":"山田屋","items":[{{"product_id":"A001","quantity":3}}],"delivery_date":"2025-07-20"}}

例2: 複数商品
入力:
  商品:A001 数量:2
  商品:B002 数量:1
  配送希望日:2025-07-20
出力: {{"customer_name":"","items":[{{"product_id":"A001","quantity":2}},{{"product_id":"B002","quantity":1}}],"delivery_date":"2025-07-20"}}

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
