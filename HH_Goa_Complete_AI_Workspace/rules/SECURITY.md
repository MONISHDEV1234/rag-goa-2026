# SECURITY & ETHICS RULES

- Never hardcode API keys, tokens or passwords.
- Never expose provider credentials in frontend code.
- Do not commit `.env` or secrets.
- Use environment variables and document required variables in `.env.example` when appropriate.
- Treat audio, text and external provider responses as untrusted input.
- Avoid logging unnecessary personal/voice data.
- Do not bypass guardrails for a better demo.
- Do not fabricate benchmark, deployment or safety claims.
- Fail safely when provider responses are invalid or context is insufficient.
