# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | ✅ Current Alpha   |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to **security@jason-doug.com**.

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information in your report:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

## Disclosure Policy

- We will acknowledge receipt of your vulnerability report within 48 hours
- We will provide a preliminary assessment of the impact and severity within 5 business days
- We will work with you to understand and validate the vulnerability
- We will coordinate a fix and release timeline with you
- We will publicly disclose the vulnerability after a fix is released, crediting you (if desired)

## Security Best Practices for Users

### Environment Configuration
- **Always** use a strong `JWT_SECRET_KEY` (generate with `openssl rand -hex 32`)
- **Never** commit `.env` files to version control
- Use HTTPS for all production deployments
- Restrict `LLM_BASE_URL` to trusted endpoints only

### Network Security
- Run Ollama and ComfyUI on localhost only (default)
- If exposing to network, use authentication and TLS
- Use firewall rules to restrict access to ports 8005, 8188, 11434

### Data Protection
- Qdrant vector database stores conversation embeddings
- Configure `QDRANT_HOST` with appropriate persistence/encryption
- Regular backups of `data/` directory
- Chat histories stored in `data/chats/` and `data/room_chats/`

### Rate Limiting
The application includes built-in rate limiting:
- Chat endpoints: 60 requests/minute (burst 15)
- Media generation: 10 requests/minute (burst 4)
- Configure via `RateLimiter` in `app/middleware/rate_limiter.py`

### Circuit Breakers
External service calls (Ollama, ComfyUI) are protected by circuit breakers:
- Failure threshold: 3 consecutive failures
- Recovery time: 30 seconds
- States: CLOSED → OPEN → HALF_OPEN → CLOSED

### Input Validation
- `companion_id` validation prevents path traversal (`..`, `/`, `\`)
- All Pydantic models enforce strict schema validation
- JWT tokens validated on protected endpoints

## Known Considerations

### Alpha Software
This is alpha software. Security features are implemented but may not be exhaustive. Use at your own risk in production.

### Third-Party Dependencies
Regularly update dependencies:
```bash
pip install --upgrade -r requirements.txt
pip-audit  # Check for known vulnerabilities
```

### Local-First Design
The platform is designed for local-first deployment:
- No required cloud services
- All data stays on your infrastructure
- Optional Twilio integration for SMS/Voice

## Security Checklist for Deployments

- [ ] Strong `JWT_SECRET_KEY` configured
- [ ] `.env` file not in version control
- [ ] HTTPS/TLS enabled for production
- [ ] Firewall rules restricting ports
- [ ] Regular dependency updates scheduled
- [ ] Backup strategy for `data/` directory
- [ ] Monitoring/alerting on `/health` endpoints
- [ ] Log retention and review policy