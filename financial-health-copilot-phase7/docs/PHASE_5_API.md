# Phase 5 API

All routes require a bearer token.

## Create a session

`POST /api/v1/chat/sessions`

Returns the new `session_id`, optional title, and creation time.

## Send a message

`POST /api/v1/chat/sessions/{session_id}/messages`

```json
{"message":"Can I afford a ₹30000 laptop next week?"}
```

The response includes `answer_text`, `intent`, labeled claims, validated tool-call summaries, missing information, provider name, and groundedness status.

## Read history

`GET /api/v1/chat/sessions/{session_id}/messages`

Only the session owner can read or write its messages. A non-owner receives the same not-found response as an unknown session.
