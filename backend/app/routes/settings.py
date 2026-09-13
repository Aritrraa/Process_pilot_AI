from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..auth import get_current_user
from ..database import get_db
from ..models import User, UserSetting
from ..schemas import UserSettingsResponse, UserSettingsUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch User Setting (for system_prompt)
    result = await db.execute(select(UserSetting).filter(UserSetting.user_id == current_user.id))
    setting = result.scalars().first()
    if not setting:
        setting = UserSetting(
            user_id=current_user.id,
            llm_provider="simulation",
            system_prompt=""
        )
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
        
    session = current_user.current_session
    
    # Merge them into the response
    return UserSettingsResponse(
        id=setting.id,
        user_id=setting.user_id,
        gemini_api_key_set=bool(session.gemini_api_key),
        groq_api_key_set=bool(session.groq_api_key),
        openai_api_key_set=bool(session.openai_api_key),
        llm_provider=session.llm_provider,
        system_prompt=setting.system_prompt,
        updated_at=setting.updated_at
    )

@router.put("/", response_model=UserSettingsResponse)
async def update_settings(
    settings_in: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(UserSetting).filter(UserSetting.user_id == current_user.id))
    setting = result.scalars().first()
    if not setting:
        setting = UserSetting(user_id=current_user.id)
        db.add(setting)
        
    session = current_user.current_session
    from app.crypto import encrypt_key
    
    # API Keys are Session Scoped!
    if settings_in.gemini_api_key is not None:
        session.gemini_api_key = encrypt_key(settings_in.gemini_api_key)
    if settings_in.groq_api_key is not None:
        session.groq_api_key = encrypt_key(settings_in.groq_api_key)
    if settings_in.openai_api_key is not None:
        session.openai_api_key = encrypt_key(settings_in.openai_api_key)
    if settings_in.llm_provider is not None:
        session.llm_provider = settings_in.llm_provider
        
    # System prompt remains global for the user account
    if settings_in.system_prompt is not None:
        setting.system_prompt = settings_in.system_prompt
        
    await db.commit()
    await db.refresh(setting)
    
    return UserSettingsResponse(
        id=setting.id,
        user_id=setting.user_id,
        gemini_api_key_set=bool(session.gemini_api_key),
        groq_api_key_set=bool(session.groq_api_key),
        openai_api_key_set=bool(session.openai_api_key),
        llm_provider=session.llm_provider,
        system_prompt=setting.system_prompt,
        updated_at=setting.updated_at
    )

@router.delete("/api-key")
async def remove_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    session = current_user.current_session
    session.gemini_api_key = None
    session.groq_api_key = None
    session.openai_api_key = None
    session.llm_provider = "simulation"
    await db.commit()
    return {"detail": "API keys removed from current session."}
