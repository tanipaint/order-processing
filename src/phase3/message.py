"""Phase3: Slack 注文通知メッセージフォーマット設計"""

import json
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

    # ボタン押下時のハンドラで使用するため、抽出データをJSONでvalueに埋め込む
    order_payload = {
        "customer_name": extracted.get("customer_name"),
        "product_id": extracted.get("product_id"),
        "quantity": extracted.get("quantity"),
        "delivery_date": str(extracted.get("delivery_date")),
    }
    blocks: List[Dict[str, Any]] = []
    # 見出し
    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": ":package: 新しい注文が届きました"},
        }
    )
    # 原文
    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*原文：*```{original_text}```"},
        }
    )
    # 抽出内容
    detail_lines = [
        f"- 顧客: {extracted.get('customer_name')}",
        f"- 商品: {extracted.get('product_id')}",
        f"- 数量: {extracted.get('quantity')}",
        f"- 配送希望日: {extracted.get('delivery_date')}",
        f"- 在庫: {stock_status}",
    ]
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
    return {"blocks": blocks}
