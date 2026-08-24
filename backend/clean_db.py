import sqlite3

conn = sqlite3.connect('processpilot.db')
cur = conn.cursor()

# Delete all users so seed_demo.py can re-register them with correct passwords
cur.execute('DELETE FROM users')
cur.execute('DELETE FROM tasks')
cur.execute('DELETE FROM meetings')
cur.execute('DELETE FROM documents')
cur.execute('DELETE FROM document_chunks')
cur.execute('DELETE FROM user_settings')

tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
for t in ['agent_logs', 'memories', 'audit_logs', 'llm_usage', 'conversations', 'conversation_messages', 'ai_failures']:
    if t in tables:
        cur.execute(f'DELETE FROM {t}')

conn.commit()
print('Database cleaned. Ready for fresh seed.')
conn.close()
