# AI Describer Medical

医療向け音声認識・QRコード生成システム

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Django 5.0+](https://img.shields.io/badge/django-5.0+-green.svg)](https://www.djangoproject.com/)

## 📋 概要

AI Describer Medicalは、医療従事者向けの音声入力システムです。音声認識（AmiVoice API）とLLM（AWS Bedrock/OpenAI/Anthropic）を組み合わせて、医療面接・カルテ入力を効率化します。

本システムはカルテシステムへの入力にQRコードを用いています。そのため、専用の機器や電子カルテシステムの改変を必要とせずに導入が可能です。

### 主な機能

- 🎤 **音声認識**: AmiVoice APIによる高精度な医療用語認識（WebSocket経由）
- 🤖 **LLM構造化**: AWS Bedrock/OpenAI/Anthropicによる自然言語処理
- 📱 **QRコード生成**: 構造化データのQRコード化（分割対応）
- 🔐 **ユーザー認証**: django-allauthによる堅牢な認証システム
- 📊 **カスタム管理画面**: ユーザー管理、ログ閲覧、プロンプト編集
- 📝 **監査ログ**: すべての管理操作を自動記録

### 対応LLM API

様々なLLM APIに対応しています。

- AWS Bedrock
- Anthropic Claude
- OpenAI

詳細は[litellmのドキュメント](https://docs.litellm.ai/docs/providers)を参照してください。

## 🚀 クイックスタート

### Requirements

- Docker 20.10+ & Docker Compose 2.0+
- AmiVoice APIキー
- LLM APIキー（AWS Bedrock / OpenAI / Anthropic 等）

### パターン1: スタンドアロン環境

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

### パターン2: 外部ロードバランサー環境（TLS終端なし）

外部のロードバランサー（AWS ALB/NLB、GCP Load Balancer、Cloudflare等）やリバースプロキシでTLS終端を行う場合は下記に沿って実行してください。

本アプリはブラウザからマイクAPIを利用するためhttps通信が必須です。

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
- 直接インターネットに公開しないでください
- Django の `SECURE_PROXY_SSL_HEADER` 設定が有効になっていることを確認してください（デフォルトで有効）

### Docker Composeファイルの使い分け

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

## 📚 ドキュメント

- [要件定義書](REQUIREMENTS.md) - システムの詳細仕様
- [システム構成](docs/ARCHITECTURE.md) - 全体構成と主要コンポーネント
- [セキュリティ](docs/SECURITY.md) - セキュリティ設計とTLS運用
- [開発環境ガイド](docs/DEVELOPMENT.md) - contributor向け開発環境セットアップ
- [コントリビューション](CONTRIBUTING.md) - 開発参加の手引き

## 📝 ライセンス

このプロジェクトはAGPLライセンスの下でライセンスされています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## Maintainer

このプロジェクトは浜松医科大学　先端医療情報学講座によりメンテナンスされています。
