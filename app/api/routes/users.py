"""
Mash Voice - User Routes

REST API endpoints for user management and phone number linking.
Links Google accounts to WhatsApp phone numbers for data privacy.
"""

import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr

from app.core.state import get_state_manager
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/users", tags=["users"])

# Redis key patterns:
# user:phones:{email} → JSON list of phone numbers linked to this user
# phone:owner:{phone_number} → email of the user who owns this phone number


class LinkPhoneRequest(BaseModel):
    """Request to link a phone number to a user."""
    email: str
    phone_number: str


class UnlinkPhoneRequest(BaseModel):
    """Request to unlink a phone number from a user."""
    email: str
    phone_number: str


class UserPhones(BaseModel):
    """Response with user's linked phone numbers."""
    email: str
    phone_numbers: List[str]


class PhoneOwner(BaseModel):
    """Response with who owns a phone number."""
    phone_number: str
    owner_email: Optional[str] = None


@router.get("/phones", response_model=UserPhones)
async def get_user_phones(
    email: str = Query(..., description="User's Google email address"),
):
    """
    Get all phone numbers linked to a user's Google account.
    """
    try:
        state_manager = get_state_manager()
        redis = await state_manager._get_redis()

        key = f"user:phones:{email}"
        data = await redis.get(key)
        phone_numbers = json.loads(data) if data else []

        return UserPhones(email=email, phone_numbers=phone_numbers)

    except Exception as e:
        logger.error(f"Error getting user phones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/phones/link", response_model=UserPhones)
async def link_phone_number(request: LinkPhoneRequest):
    """
    Link a WhatsApp phone number to a user's Google account.
    
    A phone number can only be owned by one user at a time.
    If the number is already linked to another user, it will be unlinked first.
    """
    try:
        state_manager = get_state_manager()
        redis = await state_manager._get_redis()

        email = request.email
        phone = request.phone_number.strip()

        # Check if this phone is already owned by someone else
        owner_key = f"phone:owner:{phone}"
        current_owner = await redis.get(owner_key)

        if current_owner and current_owner != email:
            # Unlink from the previous owner
            prev_key = f"user:phones:{current_owner}"
            prev_data = await redis.get(prev_key)
            prev_phones = json.loads(prev_data) if prev_data else []
            if phone in prev_phones:
                prev_phones.remove(phone)
                await redis.set(prev_key, json.dumps(prev_phones))
            logger.info(f"Unlinked phone {phone} from previous owner {current_owner}")

        # Link to new owner
        user_key = f"user:phones:{email}"
        data = await redis.get(user_key)
        phone_numbers = json.loads(data) if data else []

        if phone not in phone_numbers:
            phone_numbers.append(phone)
            await redis.set(user_key, json.dumps(phone_numbers))

        # Set owner mapping
        await redis.set(owner_key, email)

        logger.info(f"Linked phone {phone} to user {email}")
        return UserPhones(email=email, phone_numbers=phone_numbers)

    except Exception as e:
        logger.error(f"Error linking phone: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/phones/unlink", response_model=UserPhones)
async def unlink_phone_number(request: UnlinkPhoneRequest):
    """
    Unlink a WhatsApp phone number from a user's Google account.
    """
    try:
        state_manager = get_state_manager()
        redis = await state_manager._get_redis()

        email = request.email
        phone = request.phone_number.strip()

        # Remove from user's phone list
        user_key = f"user:phones:{email}"
        data = await redis.get(user_key)
        phone_numbers = json.loads(data) if data else []

        if phone in phone_numbers:
            phone_numbers.remove(phone)
            await redis.set(user_key, json.dumps(phone_numbers))

        # Remove owner mapping
        owner_key = f"phone:owner:{phone}"
        current_owner = await redis.get(owner_key)
        if current_owner == email:
            await redis.delete(owner_key)

        logger.info(f"Unlinked phone {phone} from user {email}")
        return UserPhones(email=email, phone_numbers=phone_numbers)

    except Exception as e:
        logger.error(f"Error unlinking phone: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/phones/available", response_model=List[str])
async def get_available_phones(
    email: str = Query(..., description="User's email to check ownership"),
):
    """
    Get all WhatsApp phone numbers that have active conversations 
    but are NOT yet linked to any user. These can be claimed.
    Also includes numbers already owned by this user.
    """
    try:
        state_manager = get_state_manager()
        redis = await state_manager._get_redis()

        # Get all phone numbers from active sessions
        all_phones = set()
        async for key in redis.scan_iter("session:state:*"):
            try:
                state_data = await redis.get(key)
                if not state_data:
                    continue
                state = json.loads(state_data)
                phone = state.get("phone_number")
                if phone and phone != "unknown":
                    all_phones.add(phone)
            except Exception:
                continue

        # Filter out phones owned by OTHER users
        available = []
        for phone in all_phones:
            owner_key = f"phone:owner:{phone}"
            owner = await redis.get(owner_key)
            if owner is None or owner == email:
                available.append(phone)

        return sorted(available)

    except Exception as e:
        logger.error(f"Error getting available phones: {e}")
        raise HTTPException(status_code=500, detail=str(e))
