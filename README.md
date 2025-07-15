# 注文処理システム プロトタイプ

本リポジトリは、ChatGPT Codexを活用した注文処理システムのプロトタイプ実装です。

## ファイル構成
- `order_processing_spec.md`: システム仕様書（プロトタイプ設計）
- `development_phases_and_tickets.md`: 開発フェーズごとのチケット一覧
- `src/`: 実装コード（後続で追加予定）
- `Dockerfile`, `docker-compose.yml`: ローカル環境構築用
- `requirements.txt`: Python依存パッケージ
- `.env.example`: 環境変数テンプレート

## 開発環境 (Docker)
以下のコマンドでローカル環境を立ち上げます。
```bash
docker-compose build
docker-compose up -d
```  

## 環境変数
各種シークレットは`.env`に設定してください。サンプルは`.env.example`を参照。

## 商品データ登録

サンプル商品データをNotionの`products`テーブルへ一括登録するには、以下の手順を実施してください:

- **事前準備**: Notionのproductsデータベースを対象のIntegrationに共有し、データベースIDを取得。
- `.env`に環境変数を設定:

  ```dotenv
  NOTION_API_KEY=（統合のシークレットキー）
  NOTION_DATABASE_ID_PRODUCTS=（productsデータベースのID）
  NOTION_DATABASE_ID_CUSTOMERS=（customersデータベースのID）
  NOTION_DATABASE_ID_ORDERS=（ordersデータベースのID）
  ```

- サンプル一括登録を実行:

  ```bash
  python3 -m src.phase4.seed_products
  ```

## タスク管理
詳細な開発タスクは`development_phases_and_tickets.md`を参照し、
GitHub Issue等に登録してください。

## コントリビュート
1. Issueを立てる／担当をアサイン
2. ブランチを切る: `feature/XX-yyy`
3. 実装 → `pre-commit run --files ...` → ローカルテスト
4. Pull Requestを作成し、レビュー＆マージ
