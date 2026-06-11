# Mahakosh Omnichannel Communication Layer

**ज्ञान से निर्णय तक** — Users interact with Mahakosh from any channel; the intelligence layer stays the same.

## Architecture

```
User
  ↓
Communication Gateway
  ↓
Channel Adapter (Telegram / WhatsApp / Email / WebChat / Voice / Mobile)
  ↓
Channel Router (tenant, user, permissions, intent, assistant mode)
  ↓
Chat Orchestrator (ChatGateway)
  ↓
Agent Swarm
  ↓
Knowledge Base
  ↓
Response (+ Transparency Manifest)
```

## Folder Structure

```
backend/channels/
├── base/           # BaseChannelAdapter, types, registry
├── telegram/       # Phase 8A — Telegram Bot API
├── whatsapp/       # Phase 8B — Meta Cloud API
├── email/          # SMTP send, IMAP/webhook receive
├── webchat/        # In-app chat bridge
├── future_voice/   # STT/TTS ready (Hindi, English, Hinglish, regional)
├── future_mobile/  # Push notification stub
├── gateway/        # CommunicationGateway — single entry point
├── routing/        # ChannelRouter, rate limiter
├── templates/      # Notification message templates
├── file_processor.py
├── session_sync.py
├── approval_actions.py
└── notification_center.py
```

## Supported Channels

| Channel   | Phase | Capabilities |
|-----------|-------|--------------|
| Telegram  | 8A    | Chat, documents, images, PDF, voice notes, workflow notifications, approval actions |
| WhatsApp  | 8B    | Chat, uploads, approvals, reports, notifications |
| Email     | 8     | Inbox monitoring, attachments, OCR, report delivery, approval requests |
| Web Chat  | 8     | Enterprise UI integrated in Mahakosh dashboard |
| Voice     | Future| Hindi, English, Hinglish, regional languages |
| Mobile    | Future| Push notifications |

## Database Tables (Migration 010)

- `communication_channels` — tenant channel configurations
- `channel_users` — links external IDs to Mahakosh users
- `channel_sessions` — per-channel sessions, linked to `chat_sessions` for cross-channel memory
- `channel_messages` — inbound/outbound message history
- `channel_attachments` — file metadata and storage paths
- `channel_notifications` — delivery tracking for workflow/OCR/sync events

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/channels/dashboard` | Channel dashboard stats |
| GET | `/api/v1/channels/health` | Adapter health checks |
| POST | `/api/v1/channels/connect` | Register channel (admin) |
| POST | `/api/v1/channels/link` | Link external user to Mahakosh account |
| POST | `/api/v1/channels/send` | Outbound message |
| POST | `/api/v1/channels/receive` | Inbound message (web chat / testing) |
| GET | `/api/v1/channels/sessions` | List channel sessions |
| GET | `/api/v1/channels/messages` | Message history |
| POST | `/api/v1/channels/webhook/telegram` | Telegram webhook |
| GET/POST | `/api/v1/channels/webhook/whatsapp` | WhatsApp verification + webhook |
| POST | `/api/v1/channels/webhook/email` | Email inbound webhook |

## Configuration

Add to `.env`:

```env
TELEGRAM_BOT_TOKEN=your-bot-token
WHATSAPP_ACCESS_TOKEN=your-meta-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-id
WHATSAPP_VERIFY_TOKEN=mahakosh-whatsapp-verify
EMAIL_SMTP_HOST=smtp.example.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=notifications@example.com
EMAIL_SMTP_PASSWORD=secret
EMAIL_IMAP_HOST=imap.example.com
EMAIL_IMAP_PORT=993
EMAIL_IMAP_USER=inbox@example.com
EMAIL_IMAP_PASSWORD=secret
EMAIL_FROM_ADDRESS=mahakosh@example.com
CHANNEL_WEBHOOK_BASE_URL=https://your-domain.com
CHANNEL_RATE_LIMIT_MESSAGES_PER_MINUTE=30
CHANNEL_RATE_LIMIT_UPLOADS_PER_HOUR=20
```

## Multi-Tenant Setup

1. Admin connects channel via `POST /channels/connect` with tenant-scoped config.
2. User links external identity via `POST /channels/link`.
3. `ChannelRouter` resolves tenant, user, permissions, and assistant mode from message content.
4. `SessionSync` shares `chat_session_id` across channels for the same user.

## Telegram Setup (Phase 8A)

1. Create bot via [@BotFather](https://t.me/BotFather).
2. Set `TELEGRAM_BOT_TOKEN` in environment.
3. Connect channel with webhook URL pointing to your deployment.
4. Users link account: `POST /channels/link` with their Telegram user ID and chat ID.

Webhook: `POST {BASE_URL}/api/v1/channels/webhook/telegram`

## WhatsApp Setup (Phase 8B)

1. Configure Meta Business Cloud API.
2. Set `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`.
3. Register webhook URL for verification and message events.

## Cross-Channel Conversation Sync

When a user starts on Web Chat and continues on Telegram:

1. Both channels share the same `chat_session_id` via `SessionSync.find_shared_session`.
2. Message history is stored per channel in `channel_messages`.
3. Agent context and memory persist through the linked `chat_sessions` record.

## Workflow Notifications

`NotificationCenter` fans out events to Web, Email, Telegram, and WhatsApp:

- OCR completed
- Approval required (with inline approve/reject buttons on Telegram/WhatsApp)
- Workflow failed / completed
- Report ready
- Sync complete

Workflow events (`WORKFLOW_COMPLETED`, `WORKFLOW_FAILED`, `APPROVAL_REQUIRED`) are automatically forwarded from `WorkflowTracker`.

## File Processing

Supported uploads: PDF, images, Excel, CSV, ZIP, Word documents.

Flow: Channel attachment → MinIO storage → OCR workflow trigger → Knowledge Base indexing.

## Security

- RBAC on all channel APIs
- Tenant isolation on sessions, messages, and notifications
- Audit logging on connect, link, and message actions
- Redis-backed rate limiting (messages/minute, uploads/hour)

## Frontend

Channel Center at `/channels` — connected channels, health, sessions, notifications, web chat test.

## Voice-Ready Architecture

`future_voice/adapter.py` defines interfaces for:

- Speech-to-text (Hindi, English, Hinglish, regional Indian languages)
- Text-to-speech responses
- Voice workflow triggers

Voice interactions route through the same `CommunicationGateway` → `ChatGateway` → Agent Swarm pipeline.
