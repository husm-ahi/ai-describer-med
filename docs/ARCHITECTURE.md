# システム構成

AI Describer Medicalの全体構成と主要コンポーネントの概要です。

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

## 主なコンポーネント

- **Nginx**: TLS終端とリバースプロキシ
- **Django + Channels**: 認証・管理画面・API・WebSocket制御
- **PostgreSQL**: データ永続化（ユーザー、ログ、設定）
- **Redis**: Channel Layer（WebSocketメッセージ）
- **外部API**: AmiVoiceとLLMサービス
