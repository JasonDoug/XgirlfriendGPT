import time
import hmac
import hashlib
import json
import base64
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Header

SECRET_KEY = "xgirlfriendgpt_secret_jwt_key_change_in_prod"

def create_access_token(user_id: str, expires_in: int = 86400) -> str:
    """
    Generates a cryptographically signed JWT token for user authentication.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "exp": int(time.time()) + expires_in,
        "iat": int(time.time())
    }
    
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    
    signature_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(SECRET_KEY.encode(), signature_input, hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Verifies JWT token signature and expiration.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        
        header_b64, payload_b64, signature_b64 = parts
        
        signature_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(SECRET_KEY.encode(), signature_input, hashlib.sha256).digest()
        
        rem = len(signature_b64) % 4
        if rem > 0:
            signature_b64 += "=" * (4 - rem)
        actual_sig = base64.urlsafe_b64decode(signature_b64.encode())
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Invalid signature")
            
        rem_p = len(payload_b64) % 4
        if rem_p > 0:
            payload_b64 += "=" * (4 - rem_p)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
        
        if payload.get("exp", 0) < time.time():
            raise ValueError("Token expired")
            
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {str(e)}"
        )
