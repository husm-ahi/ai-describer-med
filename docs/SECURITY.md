# セキュリティ

## セキュリティ機能

- **ユーザーIDの匿名化**: HMAC-SHA256でユーザーIDをハッシュ化してログに記録
- **監査ログ**: すべての管理操作を自動記録（改ざん防止のため読み取り専用）
- **セッション管理**: タイムアウト設定可能（デフォルト3時間）
- **CSRF保護**: Django標準のCSRF対策
- **認証**: django-allauthによる堅牢な認証システム

## 本番環境での注意事項

1. `.env`ファイルの `DEBUG=False` に設定
2. `HMAC_SECRET` を強力なランダム文字列に設定（必須）
3. `DJANGO_SECRET_KEY` を強力なランダム文字列に設定
4. データベースパスワードを強力なものに変更
5. HTTPS/TLSを有効化（本番環境では必須）

## SSL/TLS証明書の設定

本システムはNginxリバースプロキシでTLS終端を行います。証明書は以下の2つの方法で用意できます。

### オプション1: 自己署名証明書を自動生成（デフォルト）

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

### オプション2: 組織の認証局（CA）を使用（本番環境推奨）

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

### 証明書の更新

**自己署名証明書の場合:**
- CA証明書: 10年間有効
- サーバ証明書: 1年間有効
- 再生成する場合は `certs/` 内のファイルを削除して再起動

**組織CA証明書の場合:**
- 証明書の有効期限に応じてCA管理者に更新を依頼
- 更新後のファイルを `certs/` に配置して再起動
