"""Phase3: Slack 注文通知メッセージフォーマット設計"""

import json
import re
from typing import Any, Dict, List


def build_order_notification(
    original_text: str, extracted: Dict[str, Any], in_stock: bool
) -> Dict[str, Any]:
    """
    注文通知用Block Kitメッセージを構築する。

    Args:
        original_text: 受信したメールまたはFAXの原文テキスト
        extracted: LLMで抽出した構造化注文データ（顧客名, 商品ID, 数量, 配送希望日）
        in_stock: 在庫がある場合True、ない場合False

    Returns:
        Slackに投稿するpayload辞書（blocksキーを含む）
    """
    stock_status = "✅ 在庫あり" if in_stock else "❌ 在庫不足"
    # テキストフォールバック用サマリー
    summary_text = f"📦 新しい注文: 顧客 {extracted.get('customer_name')}, 商品 {extracted.get('product_id')}, 数量 {extracted.get('quantity')}"
    # 原文テキストを抽出: dictの場合はbodyのみ使用
    if isinstance(original_text, dict):
        body = original_text.get("body", "")
    elif isinstance(original_text, (bytes, bytearray)):
        body = ""
    else:
        body = original_text or ""
    # 本文の長さ制限（最大2000文字）
    max_len = 2000
    if len(body) > max_len:
        truncated = body[:max_len] + "...（以下省略）"
    else:
        truncated = body

    # 受信テキストからメールアドレスを抽出してペイロードに含める
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", truncated)
    if email_match:
        extracted["email"] = email_match.group(0)
    # ボタン押下時のハンドラで使用するため、抽出データをJSONでvalueに埋め込む
    # Slackアクションのvalueに渡すペイロード
    # 押下時ハンドラで使用する抽出データをJSONで埋め込む
    date_val = extracted.get("delivery_date")
    # 文字列化（dateオブジェクト対応）
    date_str = None
    if date_val:
        date_str = (
            date_val.isoformat() if hasattr(date_val, "isoformat") else str(date_val)
        )
    if "items" in extracted:
        # 複数商品の場合
        order_payload = {
            "customer_name": extracted.get("customer_name"),
            "items": extracted.get("items"),
        }
    else:
        order_payload = {
            "customer_name": extracted.get("customer_name"),
            "product_id": extracted.get("product_id"),
            "quantity": extracted.get("quantity"),
        }
    # 配送希望日を含める場合のみ追加
    if date_str:
        order_payload["delivery_date"] = date_str
    blocks: List[Dict[str, Any]] = []
    # 見出し
    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": ":package: 新しい注文が届きました"},
        }
    )
    # 原文（トランケート済み）
    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*原文：*```{truncated}```"},
        }
    )
    # 抽出内容
    detail_lines = []
    # 顧客・日時
    detail_lines.append(f"- 顧客: {extracted.get('customer_name')}")
    detail_lines.append(f"- 配送希望日: {extracted.get('delivery_date')}")
    # 商品一覧
    if "items" in extracted:
        detail_lines.append("- 商品一覧:")
        for item in extracted.get("items", []):
            pid = item.get("product_id")
            qty = item.get("quantity")
            detail_lines.append(f"  • 商品: {pid} × {qty}")
    else:
        detail_lines.append(f"- 商品: {extracted.get('product_id')}")
        detail_lines.append(f"- 数量: {extracted.get('quantity')}")
    # 在庫状況
    detail_lines.append(f"- 在庫: {stock_status}")
    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*抽出内容：*\n" + "\n".join(detail_lines)},
        }
    )
    # ボタン
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "action_id": "approve",
                    "value": json.dumps(order_payload),
                    "text": {"type": "plain_text", "text": "✅ 承認"},
                },
                {
                    "type": "button",
                    "action_id": "reject",
                    "value": json.dumps(order_payload),
                    "text": {"type": "plain_text", "text": "❌ 差し戻し"},
                },
            ],
        }
    )
    # 戻り値にtextを含めることでプッシュ通知等での表示をフォールバック
    return {"text": summary_text, "blocks": blocks}
