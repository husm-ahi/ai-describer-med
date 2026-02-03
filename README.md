# AI Describer Medical

医療向け音声認識・QRコード生成システム


[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Django 5.0+](https://img.shields.io/badge/django-5.0+-green.svg)](https://www.djangoproject.com/)

## 📋 概要

AI Describer Medicalは、医療従事者向けの音声入力システムです。音声認識（AmiVoice API）とLLM（AWS Bedrock/OpenAI/Anthropic）を組み合わせて、医療面接・カルテ入力を効率化します。

### 主な機能

- 🎤 **音声認識**: AmiVoice APIによる高精度な医療用語認識（WebSocket経由）
- 🤖 **LLM構造化**: AWS Bedrock/OpenAI/Anthropicによる自然言語処理
- 📱 **QRコード生成**: 構造化データのQRコード化（分割対応）
- 🔐 **ユーザー認証**: django-allauthによる堅牢な認証システム
- 📊 **カスタム管理画面**: ユーザー管理、ログ閲覧、プロンプト編集
- 📝 **監査ログ**: すべての管理操作を自動記録

## 🚀 クイックスタート

### 前提条件

- Docker 20.10+ & Docker Compose 2.0+
- AmiVoice APIキー
- LLM APIキー（AWS Bedrock / OpenAI / Anthropic のいずれか）

### 最速で起動

#### パターン1: スタンドアロン環境（TLS終端あり）

```bash
# 1. リポジトリをクローン
git clone https://github.com/husm-ahi/ai-describer-med.git
cd ai-describer-med

# 2. 環境変数を設定
cp .env.example .env
nano .env  # APIキーなど必須項目を設定

# 3. 起動（本番環境 - TLS終端あり）
docker compose up -d

# 4. ブラウザでアクセス
# https://localhost/
```

#### パターン2: 外部ロードバランサー環境（TLS終端なし）

外部のロードバランサー（AWS ALB/NLB、GCP Load Balancer、Cloudflare等）でTLS終端を行う場合：

```bash
# 1. リポジトリをクローン
git clone https://github.com/husm-ahi/ai-describer-med.git
cd ai-describer-med

# 2. 環境変数を設定
cp .env.example .env
nano .env  # APIキーなど必須項目を設定

# 3. 起動（TLS終端なし版を使用）
docker compose -f docker-compose.notls.yml up -d

# 4. ロードバランサーからHTTPでアクセス
# http://localhost/ (内部通信)
# 外部からはロードバランサー経由でHTTPSアクセス
```

**重要な注意事項（TLS終端なし版使用時）**:
- ロードバランサーが `X-Forwarded-Proto: https` ヘッダーを設定することを確認してください
- nginxコンテナは内部ネットワークでのみアクセス可能にし、直接インターネットに公開しないでください
- Django の `SECURE_PROXY_SSL_HEADER` 設定が有効になっていることを確認してください（デフォルトで有効）

#### Docker Composeファイルの使い分け

| ファイル名 | 用途 | TLS終端 | ポート公開 |
|-----------|------|---------|-----------|
| `docker-compose.yml` | スタンドアロン本番環境 | Nginx内で実施 | 80, 443 |
| `docker-compose.notls.yml` | ロードバランサー背後 | 外部で実施 | 80のみ |
| `docker-compose.dev.yml` | 開発環境 | なし | 8000, 5432, 6379 |

### 初回セットアップ

1. ブラウザで https://localhost/ にアクセス
2. 自己署名証明書の警告が表示される場合は、`certs/ca.crt`をクライアント端末に配布して信頼させる
3. ログインページから自動的に `/setup/` にリダイレクトされる
4. 管理者アカウントを作成（自動ログイン後、管理画面に遷移）
5. 管理画面でシステムプロンプトを登録
6. 一般ユーザーでログインして音声入力機能を利用開始

## � システム構成

```
┌─────────────────┐
│  ブラウザ       │
│ (スマートフォン) │
└────────┬────────┘
         │ HTTPS/WebSocket
         ▼
┌─────────────────────────────┐
│   Nginx (リバースプロキシ)   │
│   TLS終端                    │
└────────┬────────────────────┘
         │ HTTP/WebSocket
         ▼
┌─────────────────────────────┐
│   Django + Channels         │
│   (Daphne ASGI Server)      │
│                             │
│  ┌──────────────────────┐  │
│  │  HTTP Views          │  │  ← 認証、管理画面、API
│  └──────────────────────┘  │
│  ┌──────────────────────┐  │
│  │  WebSocket Consumer  │  │  ← AmiVoiceプロキシ
│  └──────────────────────┘  │
└────────┬──────────┬─────────┘
         │          │
    ┌────┴──┐   ┌──┴────┐
    ▼       │   ▼       │
┌─────────┐ │ ┌───────┐ │
│PostgreSQL│ │ │ Redis │ │
│   DB    │ │ │Channel│ │
└─────────┘ │ │ Layer │ │
            │ └───────┘ │
            ▼           ▼
    ┌──────────────────────┐
    │  外部APIサービス      │
    │  ・AmiVoice API      │
    │  ・AWS Bedrock       │
    │  ・OpenAI API        │
    │  ・Anthropic API     │
    └──────────────────────┘
```

## �📚 ドキュメント

- [要件定義書](REQUIREMENTS.md) - システムの詳細仕様
- [開発環境ガイド](docs/DEVELOPMENT.md) - 開発環境のセットアップと使い方

## 🛠️ 開発

開発に参加される方は、以下の手順で開発環境をセットアップしてください。

### 開発環境セットアップ

```bash
# 1. リポジトリをクローン
git clone https://github.com/husm-ahi/ai-describer-med.git
cd ai-describer-med

# 2. 環境変数を設定
cp .env.example .env
nano .env  # APIキーなど必須項目を設定

# 3. 開発環境を起動
docker compose -f docker-compose.dev.yml up -d

# または Makefileを使用
make dev-up

# 4. ログを確認
docker compose -f docker-compose.dev.yml logs -f backend

# または
make dev-logs
```

### 便利なコマンド

```bash
# 開発環境の起動
docker compose -f docker-compose.dev.yml up -d
# または
make dev-up

# ログの表示（リアルタイム）
docker compose -f docker-compose.dev.yml logs -f backend
# または
make dev-logs

# コンテナ内でシェルを開く
docker compose -f docker-compose.dev.yml exec backend bash
# または
make dev-shell

# マイグレーション実行
docker compose -f docker-compose.dev.yml exec backend uv run python manage.py migrate
# または
make dev-migrate

# マイグレーション作成
docker compose -f docker-compose.dev.yml exec backend uv run python manage.py makemigrations

# Django管理コマンド実行
docker compose -f docker-compose.dev.yml exec backend uv run python manage.py <command>

# テスト実行
docker compose -f docker-compose.dev.yml exec backend uv run python manage.py test
# または
make dev-test
```

### 開発環境の特徴

- **ホットリロード**: ローカルのコードがコンテナ内にマウントされる
- **ポート公開**: すべてのサービスポートが localhost に公開される
  - Backend: http://localhost:8000
  - PostgreSQL: localhost:5432
  - Redis: localhost:6379
- **開発用依存関係**: デバッグツールやテストライブラリが含まれる

### ディレクトリ構造

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
│   └── DEVELOPMENT.md
├── docker-compose.yml          # 本番用Docker Compose
├── docker-compose.dev.yml      # 開発用Docker Compose ⭐
├── Dockerfile                  # 本番用Dockerfile
├── Dockerfile.dev              # 開発用Dockerfile ⭐
├── Makefile                    # タスク自動化
├── pyproject.toml              # Python依存関係（uv形式）
├── uv.lock                     # uvロックファイル
├── .env.example                # 環境変数テンプレート
├── REQUIREMENTS.md             # 詳細要件定義書
└── README.md                   # このファイル
```

### 環境変数の設定

[.env.example](.env.example)ファイルをコピーして`.env`を作成し、各項目を設定してください。

主な設定項目：
- **Django設定**: ALLOWED_HOSTS, DJANGO_SECRET_KEY（自動生成可能）
- **データベース**: PostgreSQL接続情報
- **SSL/TLS**: 証明書の自動生成または組織CA証明書の設定
- **AmiVoice API**: APIキー、エンドポイント、文法設定
- **LLM設定**: AWS Bedrock, OpenAI, Anthropicのいずれかを選択
- **セキュリティ**: HMAC秘密鍵（ユーザーID匿名化用）
- **セッション**: タイムアウト時間（デフォルト3時間）

詳細は[.env.example](.env.example)を参照してください。

### テスト

```bash
# すべてのテストを実行
docker compose -f docker-compose.dev.yml exec backend uv run python manage.py test

# 特定のアプリのテストを実行
docker compose -f docker-compose.dev.yml exec backend uv run python manage.py test backend.core

# カバレッジ付きでテスト実行
docker compose -f docker-compose.dev.yml exec backend uv run coverage run manage.py test
docker compose -f docker-compose.dev.yml exec backend uv run coverage report
```

## 🔒 セキュリティ

### セキュリティ機能

- **ユーザーIDの匿名化**: HMAC-SHA256でユーザーIDをハッシュ化してログに記録
- **監査ログ**: すべての管理操作を自動記録（改ざん防止のため読み取り専用）
- **セッション管理**: タイムアウト設定可能（デフォルト3時間）
- **CSRF保護**: Django標準のCSRF対策
- **認証**: django-allauthによる堅牢な認証システム

### 本番環境での注意事項

1. `.env`ファイルの `DEBUG=False` に設定
2. `HMAC_SECRET` を強力なランダム文字列に設定（必須）
3. `DJANGO_SECRET_KEY` を強力なランダム文字列に設定
4. データベースパスワードを強力なものに変更
5. HTTPS/TLSを有効化（本番環境では必須）

### SSL/TLS証明書の設定

本システムはNginxリバースプロキシでTLS終端を行います。証明書は以下の2つの方法で用意できます。

#### オプション1: 自己署名証明書を自動生成（デフォルト）

**推奨: 開発・検証環境、またはCA証明書がない環境向け**

初回起動時に自己署名証明書が自動生成されます。設定不要で即座に使用開始できます。

```bash
# .envファイルを編集（SSL_CERT_PATHとSSL_KEY_PATHは空のままでOK）
# docker-compose起動時に自動的に証明書が生成される
docker compose up -d
```

**自動生成される証明書ファイル:**
- `certs/ca.crt` - CA証明書（クライアント端末に配布）
- `certs/ca.key` - CA秘密鍵（厳重に保管）
- `certs/server.crt` - サーバ証明書（Nginxで使用）
- `certs/server.key` - サーバ秘密鍵（Nginxで使用）

**カスタマイズオプション（`.env`ファイル）:**

```bash
# サーバのホスト名を指定（デフォルト: localhost）
SERVER_NAME=ai-med.example.com

# 追加するIPアドレス（カンマ区切り）
SERVER_IPS=192.168.1.100,10.0.0.50
```

#### オプション2: 組織の認証局（CA）を使用（本番環境推奨）

**推奨: 社内ネットワーク・本番環境向け**

組織のCA証明書が既にクライアント端末に信頼されている場合、そのCAに署名されたサーバ証明書を使用できます。

**メリット:**
- クライアント端末への証明書配布が不要
- 既存のPKI（公開鍵基盤）を活用
- より高い信頼性

**手順:**

1. **組織のCA管理者にサーバ証明書を依頼**
   - CSR（証明書署名要求）を生成するか、管理者に依頼
   - SubjectAltNameに必要なホスト名・IPアドレスを含める

2. **発行された証明書を配置**
   ```bash
   # 発行された証明書をcerts/ディレクトリにコピー
   cp /path/to/your/server.crt certs/server.crt
   cp /path/to/your/server.key certs/server.key
   chmod 644 certs/server.crt
   chmod 600 certs/server.key
   ```

3. **環境変数で証明書パスを指定**
   ```bash
   # .envファイルに追加
   SSL_CERT_PATH=/path/to/your/server.crt
   SSL_KEY_PATH=/path/to/your/server.key
   ```

4. **起動**
   ```bash
   docker compose up -d
   ```

この方法では`ca.crt`の配布は不要です（組織のCA証明書が既にインストールされているため）。

#### 証明書の更新

**自己署名証明書の場合:**
- CA証明書: 10年間有効
- サーバ証明書: 1年間有効
- 再生成する場合は `certs/` 内のファイルを削除して再起動

**組織CA証明書の場合:**
- 証明書の有効期限に応じてCA管理者に更新を依頼
- 更新後のファイルを `certs/` に配置して再起動

## 🤝 コントリビューション

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。

## 📝 ライセンス

このプロジェクトはAGPLライセンスの下でライセンスされています。詳細は[LICENSE](LICENSE)ファイルを参照してください。
