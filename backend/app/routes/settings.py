from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database import get_db
from ..models import User, UserSetting
from ..schemas import UserSettingsUpdate, UserSettingsResponse
from ..auth import get_current_user

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(UserSetting).filter(UserSetting.user_id == current_user.id))
    setting = result.scalars().first()
    if not setting:
        # Auto-create if missing
        setting = UserSetting(
            user_id=current_user.id,
            gemini_api_key="",
            groq_api_key="",
            openai_api_key="",
            llm_provider="simulation",
            system_prompt=""
        )
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
    return UserSettingsResponse.from_settings(setting)

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
        
    if settings_in.gemini_api_key is not None:
        setting.gemini_api_key = settings_in.gemini_api_key
    if settings_in.groq_api_key is not None:
        setting.groq_api_key = settings_in.groq_api_key
    if settings_in.openai_api_key is not None:
        setting.openai_api_key = settings_in.openai_api_key
    if settings_in.llm_provider is not None:
        setting.llm_provider = settings_in.llm_provider
    if settings_in.system_prompt is not None:
        setting.system_prompt = settings_in.system_prompt
        
    await db.commit()
    await db.refresh(setting)
    return UserSettingsResponse.from_settings(setting)
