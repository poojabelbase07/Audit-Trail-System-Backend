"""
Security Module - Handles password hashing and JWT token generation/validation
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Password hashing context - bcrypt with configurable cost factor
pwd_context = CryptContext(
    schemes=["bcrypt"],  # Use bcrypt algorithm (industry standard)
    deprecated="auto",  # Automatically upgrade old hashes
    bcrypt__rounds=settings.BCRYPT_ROUNDS  # Cost factor (higher = more secure but slower)
)

def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    
    Security notes:
    - Never store passwords in plaintext
    - bcrypt automatically adds salt (prevents rainbow table attacks)
    - Cost factor of 12 takes ~0.3 seconds (acceptable UX, strong security)
    
    Args:
        password: Plaintext password from user input
        
    Returns:
        Hashed password string (safe to store in database)
        
    Example:
        hashed = hash_password("MySecurePass123!")
        # Returns: $2b$12$abc...xyz (60 characters)
    """
    return pwd_context.hash(password)  # Generate bcrypt hash with salt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.
    
    Args:
        plain_password: Password provided by user during login
        hashed_password: Stored hash from database
        
    Returns:
        True if password matches, False otherwise
        
    Security:
        - Timing-safe comparison (prevents timing attacks)
        - Works even if hash format changes (passlib handles migrations)
        
    Example:
        is_valid = verify_password("UserInput123", stored_hash)
        if is_valid:
            # Allow login
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)  # Constant-time comparison
    except Exception as e:
        logger.error(f"❌ Password verification error: {str(e)}")
        return False  # If hash is corrupted, deny access

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token for authentication.
    
    JWT Structure:
        Header: {alg: HS256, typ: JWT}
        Payload: {sub: user_id, exp: timestamp, ...custom data}
        Signature: HMAC(header + payload, SECRET_KEY)
        
    Args:
        data: Dictionary to encode in token (typically {"sub": user_id})
        expires_delta: Optional custom expiration time
        
    Returns:
        Signed JWT token string
        
    Security:
        - Token is signed (not encrypted) - don't put secrets in payload
        - Anyone can decode payload, but can't forge signature
        - Verify signature on each request to ensure authenticity
        
    Example:
        token = create_access_token({"sub": str(user.id)})
        # Returns: eyJhbGc...xyz (long JWT string)
    """
    to_encode = data.copy()  # Don't modify original dict
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta  # Custom expiration
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)  # Default: 24 hours
    
    to_encode.update({"exp": expire})  # Add expiration claim to payload
    
    # Create signed token
    encoded_jwt = jwt.encode(
        to_encode,  # Payload data
        settings.SECRET_KEY,  # Signing key (must be kept secret)
        algorithm=settings.ALGORITHM  # HS256 (HMAC-SHA256)
    )
    
    logger.debug(f"✅ Created access token expiring at {expire}")
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT string from Authorization header
        
    Returns:
        Decoded payload dict if valid, None if invalid/expired
        
    Verification checks:
        1. Signature is valid (token not tampered with)
        2. Token not expired
        3. Algorithm matches expected (prevents algorithm confusion attacks)
        
    Example:
        payload = verify_token(token_from_header)
        if payload:
            user_id = payload["sub"]
            # Proceed with authenticated request
        else:
            # Return 401 Unauthorized
    """
    try:
        # Decode and verify token
        payload = jwt.decode(
            token,  # Token string
            settings.SECRET_KEY,  # Verify signature with this key
            algorithms=[settings.ALGORITHM]  # Only accept HS256 (prevent algorithm switching)
        )
        return payload  # Token is valid, return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("⚠️  Token expired")  # Token was valid but expired
        return None
        
    except JWTError as e:
        logger.warning(f"⚠️  Invalid token: {str(e)}")  # Signature invalid or malformed
        return None
        
    except Exception as e:
        logger.error(f"❌ Token verification error: {str(e)}")  # Unexpected error
        return None

def decode_token(token: str) -> Optional[str]:
    """
    Extract user ID from JWT token.
    
    Args:
        token: JWT string
        
    Returns:
        User ID if token valid, None otherwise
        
    Usage:
        user_id = decode_token(token)
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
    """
    payload = verify_token(token)  # Verify and decode
    if payload:
        return payload.get("sub")  # "sub" (subject) claim contains user ID
    return None