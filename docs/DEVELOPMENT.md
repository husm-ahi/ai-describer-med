# AI Describer Medical - Development Environment

## Quick Start

### 開発環境の起動

```bash
# 開発用コンテナの起動
docker compose -f docker-compose.dev.yml up -d

# ログの確認
docker compose -f docker-compose.dev.yml logs -f backend

# コンテナの停止
docker compose -f docker-compose.dev.yml down
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

### 開発時の便利なコマンド

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

# コンテナ内でコマンド実行
docker compose -f docker-compose.dev.yml exec backend bash
```

### ホットリロード

ソースコードの変更は自動的にコンテナ内に反映されます：
- `backend/` ディレクトリ内のPythonファイルを編集すると、Daphneが自動的にリロードします
- 変更がすぐに反映されない場合は、コンテナを再起動してください

### 環境変数の設定

`.env` ファイルを編集して環境変数を設定します：

```bash
# .envファイルを編集
nano .env

# コンテナを再起動して変更を反映
docker compose -f docker-compose.dev.yml restart backend
```

### デバッグ

コンテナ内でのデバッグ：

```bash
# バックエンドコンテナのログを表示
docker compose -f docker-compose.dev.yml logs -f backend

# エラー詳細を確認
docker compose -f docker-compose.dev.yml exec backend python manage.py check --deploy
```

### クリーンアップ

```bash
# コンテナ停止と削除
docker compose -f docker-compose.dev.yml down

# ボリュームも含めて削除（データベースデータも削除されます）
docker compose -f docker-compose.dev.yml down -v

# イメージも削除
docker compose -f docker-compose.dev.yml down --rmi all
```

## ディレクトリ構造

```
.
├── backend/              # Djangoアプリケーション（ホットリロード対象）
│   ├── config/          # Django設定
│   └── core/            # コアアプリケーション
├── docker-compose.dev.yml  # 開発用Docker Compose
├── Dockerfile.dev       # 開発用Dockerfile
├── .env                 # 環境変数（Gitには含めない）
└── manage.py            # Django管理スクリプト
```

## ポート

- `8000`: Django Backend (直接アクセス可能)
- `5432`: PostgreSQL (ホストからアクセス可能)
- `6379`: Redis (ホストからアクセス可能)

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
