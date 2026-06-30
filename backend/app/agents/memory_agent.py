from sqlalchemy.orm import Session
from ..models import Memory

class MemoryAgent:
    def get_memories(self, user_id: int, query: str, db: Session) -> str:
        # Get past conversation memories
        memories = db.query(Memory).filter(Memory.user_id == user_id).all()
        if not memories:
            return "No previous long-term memories stored."
        
        memory_str = "\n".join([f"- {m.key}: {m.value}" for m in memories])
        return memory_str

    def save_memory(self, user_id: int, key: str, value: str, db: Session):
        # Update or create memory
        existing = db.query(Memory).filter(Memory.user_id == user_id, Memory.key == key).first()
        if existing:
            existing.value = value
        else:
            new_memory = Memory(user_id=user_id, key=key, value=value)
            db.add(new_memory)
        db.commit()
