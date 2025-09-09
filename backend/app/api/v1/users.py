from typing import Any
from fastapi import APIRouter, Depends
from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter()


@router.get("/me", response_model=UserRead)
def read_users_me(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    return current_user