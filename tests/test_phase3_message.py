from src.phase3.message import build_order_notification


def test_build_order_notification_in_stock():
    original = "テスト注文原文"
    extracted = {
        "customer_name": "A商店",
        "product_id": "P001",
        "quantity": 3,
        "delivery_date": "2025-08-01",
    }
    payload = build_order_notification(original, extracted, in_stock=True)
    blocks = payload.get("blocks", [])
    # 見出しセクションを確認
    assert blocks[0]["text"]["text"].startswith(":package:"), "見出しが不正です"
    # 原文セクションにoriginal含む
    assert original in blocks[1]["text"]["text"], "原文が含まれていません"
    # 在庫ステータスが✅在庫あり
    assert "✅ 在庫あり" in blocks[2]["text"]["text"], "在庫状態が不正です"
    # ボタン要素が2つあること
    actions = blocks[3]["elements"]
    texts = [el["text"]["text"] for el in actions]
    assert texts == ["✅ 承認", "❌ 差し戻し"], "ボタンテキストが不正です"


def test_build_order_notification_out_of_stock():
    payload = build_order_notification(
        "x",
        {
            "customer_name": "B店",
            "product_id": "X",
            "quantity": 1,
            "delivery_date": "2025-12-31",
        },
        in_stock=False,
    )
    assert "❌ 在庫不足" in payload["blocks"][2]["text"]["text"]
