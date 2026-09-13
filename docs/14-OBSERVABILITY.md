# Observability

## Implemented Tracking
- **agent_logs:** Tracks multi-agent decision steps.
- **llm_usage:** Tracks token counts and estimated costs.
- **ai_failures:** Logs API timeouts or model errors.
- **Timezone Handling:** Strictly normalizes Postgres timezone-aware datetimes to UTC.