# GitHub Copilot プロジェクト設定

## 基本ルール

### 破壊的操作の制限
- ファイルの削除、上書き、データベースの変更など破壊的な操作を行う前に、必ずユーザーの承認を得ること
- `rm`、`DROP`、`DELETE`、`TRUNCATE` などのコマンドは確認なしに実行しない

### 権限制限
- `sudo` コマンドの使用は禁止
- root権限が必要な操作は行わない

### 要件定義の参照
- 実装や設計の判断を行う際は、`REQUIREMENTS.md` を適宜参照すること
- 要件定義書に記載された仕様に従って実装を行う

### 確認が必要なケース
以下の場合は、実装を進める前にユーザーに確認すること：
- 要件定義書と矛盾する実装が必要な場合
- 要件定義書に記載がなく、判断が曖昧な場合
- 複数の実装方法が考えられ、どちらが適切か不明な場合

### 開発環境での注意
- 変更を行った際、`docker compose -f docker-compose.dev.yml restart` を実行してコンテナを再起動し、変更が反映されることを確認すること。

### コードフォーマット
- Pythonコードのフォーマッターには `autopep8` を使用すること

## プロジェクト概要

このプロジェクトは医療向け音声認識・QRコード生成システムです。

### 技術スタック
- バックエンド: Django + Django Channels
- 認証: django-allauth
- データベース: PostgreSQL
- キャッシュ: Redis
- インフラ: Docker Compose

### 重要なファイル
- `REQUIREMENTS.md` - 要件定義書（必ず参照）
- `docker-compose.yml` - Docker構成
- `.env` - 環境変数設定
- `amivoice-api-client-library/` - AmiVoice APIクライアントライブラリ。サンプルコードが含まれる。
- `prototype_for_poc/` - PoC用プロトタイプコード。参考用。
