from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models import Memory

class MemoryAgent:
    async def get_memories(self, user_id: int, query: str, db: AsyncSession) -> str:
        # Get past conversation memories
        r = await db.execute(select(Memory).filter(Memory.user_id == user_id))
        memories = r.scalars().all()
        if not memories:
            return "No previous long-term memories stored."
        
        memory_str = "\n".join([f"- {m.key}: {m.value}" for m in memories])
        return memory_str

    async def save_memory(self, user_id: int, key: str, value: str, db: AsyncSession):
        # Update or create memory
        r = await db.execute(select(Memory).filter(Memory.user_id == user_id, Memory.key == key))
        existing = r.scalars().first()
        if existing:
            existing.value = value
        else:
            new_memory = Memory(user_id=user_id, key=key, value=value)
            db.add(new_memory)
        await db.commit()
