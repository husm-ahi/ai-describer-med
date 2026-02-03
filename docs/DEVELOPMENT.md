# Development Guide

このドキュメントは開発に参加する方向けの開発環境ガイドです。Docker Composeの開発用構成を前提としています。

## 前提条件

- Docker 20.10+ & Docker Compose 2.0+
- AmiVoice APIキー
- LLM APIキー（AWS Bedrock / OpenAI / Anthropic のいずれか）

## クイックスタート

### リポジトリのセットアップ

```bash
# 1. リポジトリをクローン
git clone https://github.com/husm-ahi/ai-describer-med.git
cd ai-describer-med

# 2. 環境変数を設定
cp .env.example .env
nano .env  # APIキーなど必須項目を設定
```

### 開発環境の起動

```bash
# 開発用コンテナの起動
docker compose -f docker-compose.dev.yml up -d

# ログの確認
docker compose -f docker-compose.dev.yml logs -f backend

# コンテナの停止
docker compose -f docker-compose.dev.yml down
```

Makefileを使う場合：

```bash
make dev-up
make dev-logs
make dev-down
```

### 初回セットアップ

```bash
# データベースマイグレーション
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate

# スーパーユーザーの作成
docker compose -f docker-compose.dev.yml exec backend python manage.py createsuperuser

# 静的ファイルの収集
docker compose -f docker-compose.dev.yml exec backend python manage.py collectstatic --noinput
```

## 便利なコマンド

```bash
# Djangoシェルの起動
docker compose -f docker-compose.dev.yml exec backend python manage.py shell

# 管理画面へのアクセス
open http://localhost:8000/admin

# データベースへの接続
docker compose -f docker-compose.dev.yml exec db psql -U aimedical -d aimedical_db

# Redisへの接続
docker compose -f docker-compose.dev.yml exec redis redis-cli

# マイグレーションファイルの作成
docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations

# コンテナ内でシェルを開く
docker compose -f docker-compose.dev.yml exec backend bash
```

Makefile版：

```bash
make dev-shell
make dev-migrate
make dev-makemigrations
make dev-test
make db-shell
make redis-cli
```

## 開発環境の特徴

- **ホットリロード**: ローカルのコードがコンテナ内にマウントされる
- **ポート公開**: すべてのサービスポートが localhost に公開される
  - Backend: http://localhost:8000
  - PostgreSQL: localhost:5432
  - Redis: localhost:6379
- **開発用依存関係**: デバッグツールやテストライブラリが含まれる

## ディレクトリ構造

```
ai-describer-med/
├── backend/                    # Djangoアプリケーション
│   ├── config/                # Django設定
│   │   ├── settings.py        # プロジェクト設定
│   │   ├── urls.py            # URLルーティング
│   │   └── asgi.py            # ASGI設定（Channels用）
│   ├── core/                  # コアアプリケーション
│   │   ├── models.py          # データベースモデル（SystemPrompt, LLMLog, AuditLog）
│   │   ├── views.py           # ビュー（メイン画面、管理画面）
│   │   ├── consumers.py       # WebSocketコンシューマー（AmiVoiceプロキシ）
│   │   ├── middleware.py      # カスタムミドルウェア
│   │   ├── services/          # ビジネスロジック
│   │   │   └── llm_service.py # LLM統合サービス
│   │   └── migrations/        # データベースマイグレーション
│   ├── templates/             # HTMLテンプレート
│   │   └── core/
│   │       ├── index.html              # メイン画面
│   │       ├── setup.html              # 初回セットアップ
│   │       ├── admin_dashboard.html    # 管理ダッシュボード
│   │       ├── manage_prompts.html     # プロンプト管理
│   │       ├── view_logs.html          # ログ閲覧
│   │       └── manage_users.html       # ユーザー管理
│   └── static/                # 静的ファイル
│       └── js/
├── amivoice-api-client-library/ # AmiVoice APIライブラリ
├── prototype_for_poc/          # プロトタイプコード（参考用）
├── nginx/                      # Nginx設定
│   ├── nginx.conf
│   └── default.conf
├── certs/                      # SSL/TLS証明書
├── docs/                       # ドキュメント
│   ├── DEVELOPMENT.md
│   ├── ARCHITECTURE.md
│   └── SECURITY.md
├── docker-compose.yml          # 本番用Docker Compose
├── docker-compose.dev.yml      # 開発用Docker Compose
├── Dockerfile                  # 本番用Dockerfile
├── Dockerfile.dev              # 開発用Dockerfile
├── Makefile                    # タスク自動化
├── pyproject.toml              # Python依存関係
├── uv.lock                     # uvロックファイル
├── .env.example                # 環境変数テンプレート
├── REQUIREMENTS.md             # 詳細要件定義書
├── CONTRIBUTING.md             # コントリビューションガイド
└── README.md                   # プロジェクト概要
```

## 環境変数の設定

[.env.example](../.env.example)ファイルをコピーして`.env`を作成し、各項目を設定してください。

主な設定項目：
- **Django設定**: ALLOWED_HOSTS, DJANGO_SECRET_KEY（自動生成可能）
- **データベース**: PostgreSQL接続情報
- **SSL/TLS**: 証明書の自動生成または組織CA証明書の設定
- **AmiVoice API**: APIキー、エンドポイント、文法設定
- **LLM設定**: AWS Bedrock, OpenAI, Anthropicのいずれかを選択
- **セキュリティ**: HMAC秘密鍵（ユーザーID匿名化用）
- **セッション**: タイムアウト時間（デフォルト3時間）

詳細は[.env.example](../.env.example)を参照してください。

## テスト

```bash
# すべてのテストを実行
docker compose -f docker-compose.dev.yml exec backend python manage.py test

# 特定のアプリのテストを実行
docker compose -f docker-compose.dev.yml exec backend python manage.py test backend.core

# カバレッジ付きでテスト実行
docker compose -f docker-compose.dev.yml exec backend coverage run manage.py test
docker compose -f docker-compose.dev.yml exec backend coverage report
```

Makefile版：

```bash
make dev-test
```

## トラブルシューティング

### ポートが既に使用されている

```bash
# ポート使用状況の確認
lsof -i :8000
lsof -i :5432
lsof -i :6379

# プロセスの停止
kill -9 <PID>
```

### データベース接続エラー

```bash
# データベースコンテナの再起動
docker compose -f docker-compose.dev.yml restart db

# データベースログの確認
docker compose -f docker-compose.dev.yml logs db
```

### マイグレーションエラー

```bash
# マイグレーションをリセット
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate --fake-initial

# または、ボリュームを削除して最初から
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
```
