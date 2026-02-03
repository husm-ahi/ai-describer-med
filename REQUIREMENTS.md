# AI Describer Medical - 要件定義書

**最終更新日**: 2026-01-30
**バージョン**: 4.2
**ステータス**: 開発準備中

---

## 目次

1. [プロジェクト概要](#1-プロジェクト概要)
2. [システムアーキテクチャ](#2-システムアーキテクチャ)
3. [機能要件](#3-機能要件)
4. [データ管理要件](#4-データ管理要件)
5. [QRコード仕様](#5-qrコード仕様)
6. [セキュリティ要件](#6-セキュリティ要件)
7. [非機能要件](#7-非機能要件)
8. [技術スタック](#8-技術スタック)
9. [環境変数設定](#9-環境変数設定)
10. [デプロイ要件](#10-デプロイ要件)
11. [将来の拡張計画](#11-将来の拡張計画)

---

## 1. プロジェクト概要

### 1.1 背景・目的

本システムは、**音声入力を用いて医療面接・カルテ入力を文字起こしし、LLMで構造化してQRコード化するWebアプリケーション**である。

以下を重視して設計・開発される：
- 高精度な音声認識および自然言語処理
- セキュリティ、コスト管理、再現性
- 医療・研究用途にも耐えうる設計
- クライアントをフロントエンドに限定した責務分離

プロトタイプを改良し、**GitHub公開可能な品質とドキュメント**を整備する。

**参考資料**: `prototype_for_poc/` ディレクトリに初期プロトタイプのコードが含まれており、実装の参考にできる。

### 1.2 主要機能

- 🎤 **音声認識**（AmiVoice API / AmiVoice API Private）
- 🤖 **LLM構造化**（AWS Bedrock / OpenAI / Anthropic対応）
- 📱 **QRコード生成**（クライアント側で生成、容量超過時は自動分割）
- 🔐 **ユーザ認証・管理**（django-allauthによる認証、ロールベースアクセス制御）
- 📊 **管理画面**（ユーザ管理、ログ閲覧、プロンプト編集）

### 1.3 対象ユーザ

- **一般ユーザ**: 医療従事者（音声入力のみ使用）
- **管理者**: システム管理者（全機能アクセス可）
- **想定規模**: 最大3,000〜5,000ユーザ

### 1.4 システム全体方針

| 項目 | 方針 |
|---|---|
| クライアント | フロントエンドのみ（音声録音、アップロード、QR表示） |
| 音声認識（STT） | オンプレミスサーバがクラウドAPI（AmiVoice）へプロキシ |
| LLM 処理 | オンプレミスサーバがクラウドLLM（Bedrock/OpenAI/Anthropic）へプロキシ |
| API 直接呼び出し | クライアントからは禁止（オンプレミスサーバ経由必須） |
| 成果物 | QRコード画像（容量超過時は分割） |
| アーキテクチャ | オンプレミス Docker Compose（nginx + Django + PostgreSQL） |

---

## 2. システムアーキテクチャ

### 2.1 全体構成

```
                        オンプレミス環境                              クラウドサービス
┌───────────────────────────────────────────────────────────────┐     ┌───────────────────┐
│                                                              │     │                   │
│  [スマートフォン] --HTTPS--> [リバースプロキシ] ---> [Docker Compose]  │ --> │  AmiVoice API     │
│                             (nginx/Caddy)       ├─ backend    │     │  (STT)            │
│                             HTTPS終端           ├─ frontend  │     │                   │
│                                                └─ db        │ --> │  AWS Bedrock /    │
│                                                              │     │  OpenAI / Anthropic│
│                                                              │     │  (LLM)            │
└───────────────────────────────────────────────────────────────┘     └───────────────────┘
```

**ポイント**:
- オンプレミスサーバーがクラウドAPIへのプロキシとして動作
- APIキーはオンプレミスサーバーのみが保持（クライアントには非公開）
- ユーザーデータはオンプレミスのPostgreSQLに保存

### 2.2 Docker構成

**コンテナ分離スキーム**:

```yaml
services:
  backend:     # Django + Django Channels
               #   - AmiVoice APIへのWebSocketプロキシ（STT） - Django Channels使用
               #   - クラウドLLMへのプロキシ（liteLLM経由）
               #   - django-allauth（ユーザ認証）
               #   - Django Admin（管理画面）
  frontend:    # nginx（静的ファイル配信、HTTPS終端）
  db:          # PostgreSQL（ユーザ、ログ保存）
  redis:       # Redis（Django ChannelsのChannel Layer）

volumes:
  postgres_data:  # PostgreSQLデータの永続化
```

### 2.3 データフロー

```
[ユーザ音声（スマートフォン）]
    ↓ WebSocket / HTTPS
[オンプレミスサーバー（Django）]
    │
    ├──> [AmiVoice API（クラウド）] ─────> 音声認識結果
    │         ↑ Django ChannelsによるWebSocketプロキシ
    │
    ├──> [システムプロンプト読込（DB）]
    │
    ├──> [クラウドLLM（Bedrock/OpenAI/Anthropic）] ─────> 構造化結果（JSON）
    │         ↑ liteLLM経由でプロキシ
    │
    ├──> [ログ保存（PostgreSQL）]
    │
    ↓
[クライアントへ返却（構造化結果JSON）]
    │
    ├──> [QRコード生成（クライアント側）]
    │         - 容量チェック
    │         - 必要に応じて分割
    │
    ↓
[QRコード読み取り（HIDエミュレーション） → 業務用PCへ入力]
```

---

## 3. 機能要件

### 3.1 フロントエンド機能

**メイン画面（index.html）**:
- ✅ 音声入力ボタン
- ✅ QRコード表示エリア
- ✅ 認識結果テキスト
- ✅ システムプロンプト表示（読み取り専用、API経由で取得）
- ✅ 接続状態表示

**管理画面（admin UI）**:
- ✅ ユーザ管理（作成、編集、削除）
- ✅ システムプロンプト編集（API経由）
- ✅ LLMログ閲覧
- ✅ 招待コード管理

**システムプロンプト管理**:
- 管理者権限でのみ編集可能
- REST API経由で取得・更新
- 一般ユーザは現在のプロンプトを参照可能

### 3.2 AmiVoice APIプロキシ化

**現状の問題**: APIキーがクライアント側に露出

**改善策**:
- オンプレミスサーバーでWebSocketプロキシを実装
- クライアント → オンプレミスサーバー（WebSocket） → AmiVoice API（クラウド）
- APIキーはオンプレミスサーバーの環境変数（`.env`）で管理

**実装**:
```python
# backend/consumers/amivoice_consumer.py
import websockets
from channels.generic.websocket import AsyncWebsocketConsumer

class AmiVoiceProxyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        # AmiVoice APIへの接続
        self.amivoice_ws = await websockets.connect(settings.AMIVOICE_API_URL)
        # 認証情報を送信（サーバ側で保持）
        await self.amivoice_ws.send(f"authorization={settings.AMIVOICE_API_KEY}")

    async def receive(self, bytes_data=None):
        # クライアントからの音声データをAmiVoiceへ転送
        if bytes_data:
            await self.amivoice_ws.send(bytes_data)
        # AmiVoiceからの応答をクライアントへ転送
        # ... (省略)
```

### 3.3 LLM処理の抽象化（liteLLM）

オンプレミスサーバーがliteLLMを使用してクラウドLLMへプロキシする。

**対応モデル（クラウド）**:

| プロバイダ | モデル名 | 環境変数 |
|-----------|---------|---------|
| AWS Bedrock | `bedrock/anthropic.claude-3-sonnet-20240229-v1:0` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| OpenAI | `gpt-4o` | `OPENAI_API_KEY` |
| Anthropic | `claude-3-5-sonnet-20241022` | `ANTHROPIC_API_KEY` |

**実装**:
```python
from litellm import completion

response = completion(
    model=os.getenv("LLM_MODEL"),
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
)
```

### 3.4 ユーザ認証・管理

**認証ライブラリ**: django-allauthを使用

#### ユーザロール

- **管理者（admin）**: 全機能アクセス可能
- **一般ユーザ（user）**: 音声入力画面のみ

#### ユーザ識別子

- **username**（必須、ユニーク）でユーザを識別
- Emailは任意（パスワードリセット用に将来対応）

#### ユーザ管理機能

**作成**: 管理者のみ可能
- username（必須、ユニーク）
- 初期パスワードはランダム生成し、管理者に表示
- ユーザは自身でパスワード変更可能（django-allauthのパスワード変更機能を使用）

**無効化**: 削除は不可、無効化のみ
```python
# 64文字のランダムパスワードを生成・設定
random_password = secrets.token_urlsafe(48)
user.set_password(random_password)
user.is_active = False
```

#### セッション管理

- **タイムアウト**: 3時間
- **ストア**: PostgreSQL（セッションテーブル）
- **SECRET_KEY**: 初回起動時に自動生成し`.secret_key`ファイルに保存

### 3.5 管理画面

**Django Adminを活用**：標準の管理画面をカスタマイズして使用

#### `/admin/users` - ユーザ管理

- ✅ ユーザ一覧（ページネーション）
- ✅ ユーザ作成フォーム（username、ランダムパスワード自動生成）
- ✅ ユーザ検索（username）
- ✅ ユーザ無効化ボタン
- ❌ ユーザ削除（実装しない）
- ❌ CSVインポート（将来検討）

#### `/admin/logs` - ログ管理

- ✅ ログ一覧（ページネーション）
- ✅ フィルタ（日時範囲、ユーザハッシュ）
- ✅ 全文検索（プロンプト・応答内容）
- ✅ n日より前のログ一括削除
  - 確認ダイアログ表示（削除件数を事前表示）
  - 削除実行後に監査ログ記録
- ✅ CSVエクスポート
- ❌ 統計ダッシュボード（将来検討）

#### `/admin/settings` - システム設定

- ✅ システムプロンプト編集
- ✅ プロンプトバージョン管理
- ✅ LLMモデル表示（切り替えは`.env`経由）
- ❌ レート制限設定（将来検討）

### 3.6 初回セットアップ

**フロー**:

1. `docker-compose up -d` で起動
2. 初回アクセス時、管理者が未登録の場合 → `/setup` へリダイレクト
3. 管理者情報入力フォーム
   - username
   - パスワード（8文字以上、強度チェック）
4. 管理者作成完了 → `/admin` へリダイレクト

---

## 4. データ管理要件

### 4.1 データ保存ポリシー

| データ種別 | 保存 | 保持期間 |
|-----------|------|---------|
| 音声データ | ❌ 保存しない | 処理完了後即削除 |
| 音声認識結果（プロンプト） | ✅ 保存 | 永続的（管理者が削除可） |
| LLM応答（構造化結果） | ✅ 保存 | 永続的（管理者が削除可） |
| QRコード画像 | ❌ 保存しない | クライアント側のみ（ブラウザ内生成） |

### 4.2 QRコードに含めるデータ

**基本方針**: QRコードには自然文全文を含めず、構造化された最小限の情報のみを含める。

**データ例**:

```json
{
  "v": 1,
  "type": "medical_record",
  "date": "2026-01-29",
  "category": "soap",
  "subjective": "3日前から咳、微熱",
  "objective": "体温37.8度、血圧118/74、右下肺軽度ラ音",
  "assessment": "上気道炎疑い",
  "plan": "クラリスロマイシン、咳止め、解熱鎮痛剤処方"
}
```

### 4.2 データベーススキーマ

#### users テーブル

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'user',  -- 'admin' or 'user'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### llm_logs テーブル

```sql
CREATE TABLE llm_logs (
    id SERIAL PRIMARY KEY,
    user_hash VARCHAR(16) NOT NULL,  -- HMAC-SHA256でハッシュ化
    user_prompt TEXT NOT NULL,       -- 音声認識結果
    llm_response TEXT NOT NULL,      -- 構造化結果
    model_name VARCHAR(100),
    prompt_version VARCHAR(20),
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_hash (user_hash),
    INDEX idx_created_at (created_at)
);
```

#### audit_logs テーブル

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    action VARCHAR(50) NOT NULL,     -- 'user_created', 'user_disabled', 'logs_deleted', etc.
    admin_id INTEGER,
    target_user_id INTEGER,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### system_prompts テーブル

```sql
CREATE TABLE system_prompts (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.3 ユーザIDのハッシュ化

**目的**: ログからユーザを直接特定できないようにしつつ、一意性を保持

**実装**:
```python
import hmac
import hashlib

def hash_user_id(username: str) -> str:
    """
    HMAC-SHA256でユーザIDをハッシュ化
    - 同一ユーザは常に同一ハッシュ値（一意性保持）
    - ハッシュ値だけではユーザ特定不可
    - ユーザDBとの突合で特定可能
    """
    secret = os.getenv("HMAC_SECRET")
    return hmac.new(
        secret.encode(),
        username.encode(),
        hashlib.sha256
    ).hexdigest()[:16]  # 先頭16文字のみ
```

---

## 5. QRコード仕様

### 5.1 QRコード生成要件

- **クライアント側（ブラウザ）で生成**
- 構造化 JSON を QRコードにエンコードする
- QRコード容量制限を考慮する
- 単一または複数の QRコードとして生成可能とする
- PNG または SVG 形式をサポートする
- ユーザーが保存・共有できること

### 5.2 QRコード読み取り方式

- **HIDエミュレーション + Alt入力記法**を使用
- QR Readerを介して業務用PCにキーボード入力として送信
- 読み取り順序は正しい順番で行われることを前提

### 5.3 QRコード分割仕様

**分割処理はクライアント側で実行**

#### 分割条件

- QRコードにエンコードするデータが容量制限を超える場合、データを分割し、複数の QRコードとして生成する

#### 分割時の必須メタデータ

分割された各 QRコードには、以下の情報を必ず含める：

- **スキーマバージョン** (`v`): データ形式のバージョン
- **セッションID** (`session_id`): 全QRコードで共通の一意識別子
- **分割総数** (`total`): 全体で何個のQRコードに分割されたか
- **当該QRのインデックス** (`part`): 現在のQRコードの順序（1始まり）
- **実データ** (`payload`): 分割された構造化データの一部

#### 分割QRコードのデータ例

```json
{
  "v": 1,
  "session_id": "uuid-1234-5678",
  "part": 1,
  "total": 3,
  "payload": {
    "type": "medical_record",
    "date": "2026-01-29",
    "subjective": "3日前から咳、微熱あり..."
  }
}
```

```json
{
  "v": 1,
  "session_id": "uuid-1234-5678",
  "part": 2,
  "total": 3,
  "payload": {
    "objective": "体温37.8度、血圧118/74...",
    "assessment": "上気道炎疑い"
  }
}
```

```json
{
  "v": 1,
  "session_id": "uuid-1234-5678",
  "part": 3,
  "total": 3,
  "payload": {
    "plan": "クラリスロマイシン、咳止め、解熱鎮痛剤処方"
  }
}
```

#### 復元性

- 読み取り側は、全 QRコードを取得することで元の構造化データを復元可能でなければならない
- **読み取り順序は正しい順番で行われることを前提**（ユーザーが順番に読み取る）
- 順序情報（`part`、`total`）は検証用として含める
- 将来の拡張として、QRデータの署名・改ざん検知方式を検討

---

## 6. セキュリティ要件

### 6.1 HTTPS必須

**ブラウザのセキュリティポリシー**: HTTPではマイクアクセス不可

**推奨構成**:
```
[ユーザ] --HTTPS--> [nginxリバースプロキシ] --HTTP--> [Dockerコンテナ]
                    ↑ Let's Encrypt証明書
```

**SSL証明書の取り扱い**:
- `.env`で証明書パスを指定した場合: 指定された証明書を使用
- `.env`で証明書を指定しない場合: **自己署名証明書を自動生成**して使用

**開発環境**: `http://localhost` でのみ動作可（ブラウザの例外扱い）

### 6.2 クライアント側のAPI呼び出し禁止

**重要**: クライアントからクラウドAPI（STT / LLM 等）を直接呼び出すことを禁止する
- APIキーがクライアント側に露出しない
- すべてのクラウドAPI呼び出しはオンプレミスサーバー経由で実行

### 6.3 認証・認可

- パスワード: bcryptでハッシュ化
- セッション: HTTPOnly Cookieで管理
- CSRF対策: トークン検証
- IAM: 最小権限設計（AWS環境）

### 6.4 APIキー管理

- AmiVoice API Key: オンプレミスサーバーの環境変数（`.env`）で管理
- LLM API Key: オンプレミスサーバーの環境変数（`.env`）で管理
- クライアント側には一切露出しない（オンプレミスサーバーのみ保持）

### 6.5 データプライバシー

- QRコードには個人情報を直接含めない
- ユーザIDはハッシュ化してログに記録
- 音声データは処理完了後即削除

### 6.6 レート制限・攻撃対策

- 将来の拡張で実装検討
- ユーザごとの使用量制限
- nginx側でのレート制限設定

---

## 7. 非機能要件

### 7.1 パフォーマンス

- 同時接続数: 100ユーザを想定
- 音声認識レスポンス: リアルタイム（WebSocket）
- LLM処理時間: 5〜15秒を想定

### 7.2 スケーラビリティ

- Docker Compose（標準運用）
- 水平スケーリング: Docker Swarm または Kubernetes への移行が可能な設計
- 将来的にAWSサーバーレスへの移行も検討可能

### 7.3 可用性

- データベースバックアップ: 日次（pg_dumpによる自動バックアップ推奨）
- エラーハンドリング: 全APIエンドポイントで実装
- ログ: すべての処理を記録

### 7.4 コスト管理

- Docker Compose による軽量な運用
- 音声データは処理完了後に即削除
- API 呼び出しにはレート制限を設ける（将来対応）

### 7.5 再現性・監査性

- 使用するモデル、Prompt、Schema はコードとして管理
- 処理フローはシーケンシャルに実行し、各ステップをログ記録
- 処理ログを取得可能とする

### 7.6 監視・ログ

- アプリケーションログ: stdout（Docker Logs）
- 監査ログ: データベースに保存
- メトリクス: 将来検討（Prometheus等）

---

## 8. 技術スタック

### 8.1 バックエンド

| 技術 | バージョン | 用途 |
|------|-----------|------|
| Python | 3.11+ | 言語 |
| uv | 0.1+ | Pythonパッケージマネージャー（高速依存関係管理） |
| Django | 5.0+ | Webフレームワーク |
| Django Channels | 4.0+ | WebSocketサポート（AmiVoiceプロキシ） |
| django-allauth | 0.60+ | ユーザ認証・パスワード管理 |
| Daphne / Uvicorn | - | ASGIサーバー |
| liteLLM | 1.17+ | LLM統合（接続先・キーは.envで設定） |
| PostgreSQL | 15+ | データベース |
| Redis | 7.0+ | Channel Layer（Django Channels） |
| websockets | 12.0+ | AmiVoice API接続 |
| bcrypt | - | パスワードハッシュ |

### 8.2 フロントエンド

| 技術 | 用途 |
|------|------|
| HTML/CSS/JS | 静的ファイル |
| Bootstrap 5.3+ | UIフレームワーク |
| qrcode.js | QRコード生成（ブラウザ側） |
| AmiVoice Client Library | 音声認識クライアント |

### 8.3 インフラ

| 技術 | 用途 |
|------|------|
| Docker | コンテナ化 |
| Docker Compose | オーケストレーション |
| nginx | リバースプロキシ（推奨） |
| Caddy | リバースプロキシ（代替、自動HTTPS） |

---

## 9. 環境変数設定

### 9.1 .env.example

```bash
# ========================================
# Database Configuration
# ========================================
POSTGRES_USER=aimedical
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=aimedical_db
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}

# ========================================
# SSL/TLS Configuration
# ========================================
# 指定しない場合は自己署名証明書を自動生成
SSL_CERT_PATH=
SSL_KEY_PATH=

# ========================================
# AmiVoice Configuration
# ========================================
AMIVOICE_API_URL=wss://acp-api.amivoice.com/v1/nolog/
AMIVOICE_API_KEY=your_amivoice_api_key_here
AMIVOICE_GRAMMAR=-a-medical

# ========================================
# LLM Configuration (liteLLM)
# ========================================
# 使用するモデル（liteLLMのモデル名形式）
LLM_MODEL=bedrock/anthropic.claude-3-sonnet-20240229-v1:0

# liteLLM API Base URL（カスタムエンドポイント使用時）
# LITELLM_API_BASE=https://your-litellm-proxy.com

# AWS Bedrock credentials
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# OpenAI API Key (if using OpenAI)
OPENAI_API_KEY=your_openai_api_key

# Anthropic API Key (if using Anthropic directly)
ANTHROPIC_API_KEY=your_anthropic_api_key

# ========================================
# Security Configuration
# ========================================
# SECRET_KEY is auto-generated on first startup
HMAC_SECRET=your_hmac_secret_key_here_minimum_32_chars

# ========================================
# Session Configuration
# ========================================
SESSION_TIMEOUT_HOURS=3
```

---

## 10. デプロイ要件

### 10.1 システム要件

#### Docker環境（本番・開発共通）

- OS: Linux（Ubuntu 24.04 推奨）
- Docker: 20.10+
- Docker Compose: 2.0+
- メモリ: 最低4GB、推奨8GB
- ストレージ: 最低20GB

#### ローカル開発環境（uv使用）

- OS: Linux / macOS / Windows
- Python: 3.11以上
- uv: 0.1以上（パッケージマネージャー）
- PostgreSQL: 15以上（ローカルまたはDocker）
- メモリ: 最低2GB、推奨4GB
- ストレージ: 最低5GB

### 10.2 セットアップ手順（Docker環境）

```bash
# 1. リポジトリクローン
git clone https://github.com/yourname/ai-describer-med.git
cd ai-describer-med

# 2. 環境変数設定
cp .env.example .env
nano .env  # APIキー等を設定

# 3. 起動（初回はuv lockとuv syncが自動実行されます）
docker-compose up -d

# 4. 初回アクセス
# http://localhost:8080/setup → 管理者作成
```

### 10.2.1 ローカル開発環境セットアップ（uv使用）

**uv（高速Pythonパッケージマネージャー）を使用した開発環境構築**：

```bash
# 1. uvのインストール（初回のみ）
curl -LsSf https://astral.sh/uv/install.sh | sh
# または
pip install uv

# 2. リポジトリクローン
git clone https://github.com/yourname/ai-describer-med.git
cd ai-describer-med

# 3. Python仮想環境の作成
uv venv
source .venv/bin/activate  # Linux/macOS
# または .venv\Scripts\activate  # Windows

# 4. 依存関係の解決とロックファイル生成（初回またはpyproject.toml変更時）
uv lock

# 5. 依存関係のインストール
uv sync

# 6. 環境変数設定
cp .env.example .env
nano .env  # APIキー等を設定

# 7. データベースマイグレーション
python manage.py migrate

# 8. 管理者ユーザー作成
python manage.py createsuperuser

# 9. 開発サーバー起動
python manage.py runserver 0.0.0.0:8000
# またはWebSocket対応の場合
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

**uvの利点**：
- 🚀 従来のpip/pipenvより10-100倍高速
- 📦 依存関係の解決が確実
- 🔒 ロックファイルによる再現性の確保
- 💾 グローバルキャッシュによるディスク節約

### 10.3 本番環境（HTTPS）

**nginx リバースプロキシ例**:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

詳細は [docs/setup-nginx.md](docs/setup-nginx.md) を参照。

---

## 11. 将来の拡張計画

### 初期実装（Docker Compose環境）

- ✅ ユーザ認証・管理機能
- ✅ 音声認識（AmiVoice API）
- ✅ LLM構造化（liteLLM統合）
- ✅ QRコード生成（分割対応）
- ✅ 管理画面（ユーザ管理、ログ閲覧）
- ✅ uv を使用した高速Python環境構築

### 機能拡張（将来検討）

- ⬜ OAuth認証連携
- ⬜ CSVユーザインポート
- ⬜ 統計ダッシュボード
- ⬜ レート制限機能
- ⬜ メール通知（パスワードリセット等）
- ⬜ 自動バックアップ
- ⬜ メトリクス収集（Prometheus等）
- ⬜ A/Bテスト基盤（プロンプト最適化）
- ⬜ QRコードの署名・改ざん検知
- ⬜ QR読み取り側アプリケーション開発
- ⬜ 多言語対応
- ⬜ 医療・研究倫理（IRB）文書との整合

### スケールアウト対応（将来検討）

- ⬜ Docker Swarm / Kubernetes対応
- ⬜ AWS サーバーレス移行（Lambda、API Gateway、DynamoDB等）
- ⬜ AWS WAF によるセキュリティ強化

---

## 12. 今後の検討事項

- AmiVoice API の音声認識精度と医療用語対応の評価
- AmiVoice API Private（AWS Marketplace）のコスト試算と契約手続き
- QRコードデータの署名・改ざん検知方式の設計
- QR読み取り側アプリケーションの仕様策定
- 多言語対応（英語、中国語等）
- 医療・研究倫理審査委員会（IRB）文書との整合性確認

---

## 付録

### A. 関連ドキュメント

- [技術仕様書](TECHNICAL_SPECS.md)
- [セットアップガイド](docs/SETUP.md)
- [AmiVoice APIキー取得方法](docs/amivoice-setup.md)
- [AWS Bedrockセットアップ](docs/aws-bedrock-setup.md)
- [nginxリバースプロキシ設定](docs/setup-nginx.md)
- [Caddyリバースプロキシ設定](docs/setup-caddy.md)
- [プロトタイプコード](prototype_for_poc/) - 初期プロトタイプの実装（HTML/CSS/JavaScript）

### B. 変更履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|----------|
| 2026-01-30 | 4.2 | 複数の仕様変更（django-allauth使用、username識別、QR生成クライアント側、SSL自動生成等） |
| 2026-01-30 | 4.1 | バックエンドをFastAPIからDjango + Django Channelsに変更 |
| 2026-01-30 | 4.0 | Docker Compose運用に統合（Phase分離を廃止、AWSサーバーレスを将来拡張に移動） |
| 2026-01-29 | 3.0 | 2つの要件定義書を統合（AWSサーバーレス＋Docker両対応、QRコード分割仕様追加） |
| 2026-01-29 | 2.0 | プロトタイプ改良版の要件定義（Docker構成、ユーザ管理機能追加） |
| 2025-12-24 | 1.0 | 初期プロトタイプの要件定義（AWSサーバーレス構成） |

### C. AmiVoice API 使用に関する補足

#### AmiVoice API について

- 株式会社アドバンスト・メディアが提供する高精度音声認識 API
- 医療用語を含む専門用語の認識に優れている
- リアルタイム認識とバッチ認識の両方をサポート

#### AmiVoice API Private（AWS Marketplace SaaS）について

- AWS Marketplace から利用可能な SaaS 版
- AWS 環境内で利用でき、セキュリティ要件に適合しやすい
- 利用には AWS Marketplace でのサブスクリプション契約が必要

#### 実装上の考慮事項

- API エンドポイント URL は環境変数で管理する
- 認証情報（API キー等）は `.env` ファイルに格納する
- エラーハンドリング：音声認識失敗時のリトライ処理を実装する
- 音声ファイル形式：AmiVoice API の対応形式（WAV、MP3 等）を確認して使用する

### D. uv（Python パッケージマネージャー）について

#### uvとは

- Rustで書かれた超高速なPythonパッケージマネージャー
- pip、pip-tools、pipenv、poetryの代替として使用可能
- Astral社が開発・メンテナンス

#### uvの主な特徴

- **高速性**: pip/pipenvより10-100倍高速な依存関係解決とインストール
- **信頼性**: 厳密な依存関係解決により環境の再現性を保証
- **互換性**: `requirements.txt`、`pyproject.toml` と完全互換
- **効率性**: グローバルキャッシュでディスク容量とネットワーク帯域を節約

#### 主要コマンド

```bash
# 仮想環境の作成
uv venv

# 依存関係のロック（pyproject.tomlから）
uv lock

# 依存関係のインストール（uv.lockから）
uv sync

# パッケージの追加
uv add package-name

# 開発用パッケージの追加
uv add --dev package-name

# パッケージの削除
uv remove package-name

# 依存関係のアップグレード
uv lock --upgrade
```

#### プロジェクトでの使用方針

- **ローカル開発環境**: uv を使用（高速な開発体験）
- **Docker環境**: uv を使用（ビルド高速化）
- **CI/CD**: uv を使用して高速化
- **依存関係解決**: すべての環境でuvを使用

### E. 用語集

| 用語 | 説明 |
|------|------|
| AmiVoice | 株式会社アドバンスト・メディアの音声認識API |
| liteLLM | 複数のLLMプロバイダを統一インターフェースで扱うライブラリ |
| SOAP | 医療記録の構造化形式（Subjective, Objective, Assessment, Plan） |
| QRコード | 構造化データをエンコードした二次元バーコード |
| Step Functions | AWS のワークフロー管理サービス |
| IAM | Identity and Access Management（AWS のアクセス制御） |

---

**問い合わせ先**: プロジェクト管理者  
**ライセンス**: AGPL-3.0
| 2026-01-29 | 2.0 | プロトタイプ改良版の要件定義 |
| 2025-12-24 | 1.0 | 初期プロトタイプの要件定義 |

### C. 用語集

| 用語 | 説明 |
|------|------|
| AmiVoice | 株式会社アドバンスト・メディアの音声認識API |
| liteLLM | 複数のLLMプロバイダを統一インターフェースで扱うライブラリ |
| SOAP | 医療記録の構造化形式（Subjective, Objective, Assessment, Plan） |
| QRコード | 構造化データをエンコードした二次元バーコード |

---

**問い合わせ先**: [プロジェクト管理者]
**ライセンス**: AGPL-3.0
