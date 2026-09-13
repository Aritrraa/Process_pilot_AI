# Security Architecture

## Implemented Controls
- **Authentication:** JWT with PyJWT. Passwords hashed via passlib (bcrypt).
- **Authorization:** RBAC (Admin, Manager, Employee) and strict ABAC isolating department data.
- **PII Redaction:** Regex-based scrubbing (pii_redactor.py) for SSNs, credit cards, emails. Presidio is configured as optional but relies on regex primarily.
- **API Key Security:** AES-GCM encryption (crypto.py) for user-provided LLM keys.
- **Database:** Supabase Row Level Security (RLS) enabled on all 18 tables to block direct PostgREST access.