# ==================== src/api/auth_router.py ====================

"""
Authentication Router

Handles user authentication, JWT token management, and user operations.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr
import jwt
import bcrypt

logger = logging.getLogger("ai_receptionist.auth_router")

router = APIRouter()
security = HTTPBearer()

# JWT Configuration (move to settings in production)
SECRET_KEY = "your-secret-key-change-in-production"  # TODO: Move to env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# ============ Request/Response Models ============

class UserCreate(BaseModel):
    """Request model for user creation"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password (min 8 chars)")
    full_name: str = Field(..., description="User's full name")
    role: str = Field(default="user", description="User role (user/admin)")


class UserLogin(BaseModel):
    """Request model for user login"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Response model for token"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class UserResponse(BaseModel):
    """Response model for user data"""
    user_id: str
    email: str
    full_name: str
    role: str
    created_at: str
    is_active: bool


class PasswordChange(BaseModel):
    """Request model for password change"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


# ============ Utility Functions ============

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# ============ Dependency Injection ============

def get_services():
    """Get services from main.py"""
    from main import services
    return services


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    services=Depends(get_services)
) -> dict:
    """
    Dependency to get current authenticated user.
    
    Use this in protected endpoints:
    @router.get("/protected")
    async def protected_endpoint(current_user=Depends(get_current_user)):
        return {"user": current_user}
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    # Get user from database
    user = await services.db_service.db.users.find_one({"user_id": user_id})
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )
    
    return user


async def get_current_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to get current admin user.
    
    Use this in admin-only endpoints:
    @router.get("/admin-only")
    async def admin_endpoint(admin_user=Depends(get_current_admin_user)):
        return {"admin": admin_user}
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


# ============ Endpoints ============

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    services=Depends(get_services)
):
    """
    Register a new user.
    
    Creates a new user account with hashed password.
    """
    logger.info(f"👤 New user registration: {user_data.email}")
    
    try:
        # Check if user already exists
        existing_user = await services.db_service.db.users.find_one(
            {"email": user_data.email}
        )
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user document
        import uuid
        user = {
            "user_id": str(uuid.uuid4()),
            "email": user_data.email,
            "password_hash": hash_password(user_data.password),
            "full_name": user_data.full_name,
            "role": user_data.role,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True
        }
        
        # Insert into database
        await services.db_service.db.users.insert_one(user)
        
        logger.info(f"✅ User registered: {user['user_id']}")
        
        # Return user data (without password hash)
        return UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            created_at=user["created_at"],
            is_active=user["is_active"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Registration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    services=Depends(get_services)
):
    """
    Login and receive access token.
    
    Returns JWT token for authenticated requests.
    """
    logger.info(f"🔐 Login attempt: {credentials.email}")
    
    try:
        # Get user from database
        user = await services.db_service.db.users.find_one(
            {"email": credentials.email}
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["user_id"], "email": user["email"], "role": user["role"]},
            expires_delta=access_token_expires
        )
        
        logger.info(f"✅ Login successful: {user['user_id']}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current user information.
    
    Requires authentication token.
    """
    return UserResponse(
        user_id=current_user["user_id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        created_at=current_user["created_at"],
        is_active=current_user["is_active"]
    )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: dict = Depends(get_current_user),
    services=Depends(get_services)
):
    """
    Change user password.
    
    Requires authentication token and current password verification.
    """
    logger.info(f"🔑 Password change request: {current_user['user_id']}")
    
    try:
        # Verify current password
        if not verify_password(password_data.current_password, current_user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_password_hash = hash_password(password_data.new_password)
        
        # Update in database
        await services.db_service.db.users.update_one(
            {"user_id": current_user["user_id"]},
            {"$set": {"password_hash": new_password_hash}}
        )
        
        logger.info(f"✅ Password changed: {current_user['user_id']}")
        
        return {
            "success": True,
            "message": "Password changed successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Password change failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password change failed: {str(e)}"
        )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout (token invalidation handled client-side).
    
    In a stateless JWT system, logout is handled by the client
    discarding the token. For token blacklisting, implement a
    token revocation list in Redis.
    """
    logger.info(f"👋 Logout: {current_user['user_id']}")
    
    return {
        "success": True,
        "message": "Logged out successfully. Please discard your token."
    }


@router.get("/verify-token")
async def verify_token_endpoint(current_user: dict = Depends(get_current_user)):
    """
    Verify if token is valid.
    
    Returns 200 if token is valid, 401 if invalid/expired.
    """
    return {
        "valid": True,
        "user_id": current_user["user_id"],
        "email": current_user["email"]
    }