# ========================================
# Stage 1: Builder - 依存関係のインストール
# ========================================
FROM python:3.13-slim AS builder

# 環境変数設定
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# 作業ディレクトリ設定
WORKDIR /app

# ビルドに必要なパッケージのインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# uvのインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# プロジェクトファイルのコピー（依存関係定義）
COPY pyproject.toml uv.lock README.md ./

# 依存関係のインストール（仮想環境に）
# プロジェクト自体はインストールせず、依存パッケージのみインストール
RUN uv sync --frozen --no-dev --no-install-project

# アプリケーションコードのコピー
COPY backend ./backend
COPY manage.py ./

# プロジェクト自体のインストール（依存関係のキャッシュは保持）
# editable modeではなく、通常のインストールを行う
RUN uv pip install --no-deps .

# ========================================
# Stage 2: Runtime - 最小限のランタイムイメージ
# ========================================
FROM python:3.13-slim AS runtime

# 環境変数設定
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv

# 作業ディレクトリ設定
WORKDIR /app

# ランタイムに必要な最小限のパッケージのみインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 非rootユーザーの作成（COPY前に実行してchown -Rを回避）
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/staticfiles /app/media && \
    chown -R appuser:appuser /app

# ビルダーステージから仮想環境をコピー（所有権を設定）
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# アプリケーションコードをコピー（所有権を設定）
COPY --from=builder --chown=appuser:appuser /app/backend /app/backend
COPY --from=builder --chown=appuser:appuser /app/manage.py /app/manage.py

USER appuser

# ポート公開
EXPOSE 8000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# デフォルトコマンド（docker-compose.ymlでオーバーライド）
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "backend.config.asgi:application"]
