"""
Authentication API - User registration, login, logout endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.database import get_db
from app.schemas import UserCreate, UserLogin, TokenResponse, UserResponse
from app.models import User
from app.core.security import hash_password, verify_password, create_access_token
from app.core.dependencies import get_current_user
from app.utils.audit_logger import log_user_login, log_user_logout, log_user_register

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,  # Validated by Pydantic (email, password, full_name)
    request: Request,  # Request object for audit logging
    db: Session = Depends(get_db)  # Database session
):
    """
    Register new user account.
    
    Process:
        1. Validate input (Pydantic handles this)
        2. Check if email already exists
        3. Hash password
        4. Create user in database
        5. Generate JWT token
        6. Log registration in audit trail
        
    Returns:
        TokenResponse with JWT and user info
        
    Raises:
        409: Email already registered
        500: Database error
    """
    logger.info(f"➡️  Registration attempt for email: {user_data.email}")
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        logger.warning(f"⚠️  Registration failed - email already exists: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered. Please use a different email or login."
        )
    
    # Hash password before storing
    hashed_password = hash_password(user_data.password)
    
    # Create new user
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        # role defaults to USER (set in model)
        # is_active defaults to True
    )
    
    try:
        db.add(new_user)  # Add to session
        db.commit()  # Save to database
        db.refresh(new_user)  # Refresh to get generated ID
        logger.info(f"✅ User registered successfully: {new_user.email}")
        
        # Log registration in audit trail
        log_user_register(db=db, user=new_user, request=request)
        
        # Generate JWT token
        access_token = create_access_token(data={"sub": str(new_user.id)})
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.from_orm(new_user)
        )
        
    except Exception as e:
        db.rollback()  # Rollback on error
        logger.error(f"❌ Registration failed for {user_data.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again later."
        )

@router.post("/login", response_model=TokenResponse)
def login(
    credentials: UserLogin,  # Validated by Pydantic (email, password)
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token.
    
    Process:
        1. Validate input
        2. Find user by email
        3. Verify password
        4. Update last_login timestamp
        5. Generate JWT token
        6. Log successful login
        
    Returns:
        TokenResponse with JWT and user info
        
    Raises:
        401: Invalid credentials
        403: Account inactive
        500: Database error
    """
    logger.info(f"➡️  Login attempt for email: {credentials.email}")
    
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        logger.warning(f"⚠️  Login failed - user not found: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        logger.warning(f"⚠️  Login failed - incorrect password: {credentials.email}")
        # Log failed login attempt
        try:
            log_user_login(db=db, user=user, request=request, success=False)
        except:
            pass  # Don't fail login if audit log fails
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if account is active
    if not user.is_active:
        logger.warning(f"⚠️  Login failed - inactive account: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact administrator."
        )
    
    # Update last_login timestamp
    try:
        user.last_login = datetime.utcnow()
        db.commit()
    except Exception as e:
        logger.error(f"⚠️  Failed to update last_login: {str(e)}")
        db.rollback()
        # Continue anyway - login should succeed even if timestamp update fails
    
    # Generate JWT token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Log successful login
    try:
        log_user_login(db=db, user=user, request=request, success=True)
    except Exception as e:
        logger.error(f"⚠️  Failed to log login: {str(e)}")
        # Continue - login should succeed even if audit log fails
    
    logger.info(f"✅ Login successful: {user.email}")
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),  # Require authentication
    db: Session = Depends(get_db)
):
    """
    Logout current user.
    
    Note: JWT tokens are stateless - we can't invalidate them server-side.
    Client should delete token from storage.
    
    This endpoint just logs the logout action in audit trail.
    
    Returns:
        Success message
    """
    logger.info(f"➡️  Logout request from: {current_user.email}")
    
    # Log logout in audit trail
    try:
        log_user_logout(db=db, user=current_user, request=request)
    except Exception as e:
        logger.error(f"⚠️  Failed to log logout: {str(e)}")
        # Continue - logout should succeed even if audit log fails
    
    logger.info(f"✅ User logged out: {current_user.email}")
    
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)  # Require authentication
):
    """
    Get current user's profile information.
    
    Used by frontend to verify token and get user data.
    
    Returns:
        UserResponse with current user's info
    """
    logger.debug(f"➡️  Profile request from: {current_user.email}")
    return UserResponse.from_orm(current_user)