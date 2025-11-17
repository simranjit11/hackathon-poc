"""
Utility script to generate JWT tokens for testing MCP server.

Usage:
    python generate_jwt.py
    python generate_jwt.py --user-id 67890
    python generate_jwt.py --user-id 12345 --scopes read transact
"""

import os
import sys
from datetime import datetime, timedelta, timezone

# Default values matching mcp_server/config.py defaults
DEFAULT_SECRET_KEY = "your-secret-key-change-in-production"
DEFAULT_ISSUER = "orchestrator"
DEFAULT_ALGORITHM = "HS256"

try:
    from jose import jwt
    JOSE_AVAILABLE = True
except ImportError:
    JOSE_AVAILABLE = False
    print("Warning: python-jose not installed. Install with: pip install python-jose[cryptography]")
    print("Or use uv: uv pip install python-jose[cryptography]")
    print()


def generate_jwt_token(
    user_id: str = "12345",
    scopes: list[str] = ["read"],
    secret_key: str = DEFAULT_SECRET_KEY,
    issuer: str = DEFAULT_ISSUER,
    algorithm: str = DEFAULT_ALGORITHM,
    expires_in_minutes: int = 15
) -> str:
    """
    Generate a JWT token for MCP server authentication.
    
    Args:
        user_id: User identifier (default: "12345")
        scopes: List of scopes (default: ["read"])
        secret_key: JWT secret key
        issuer: JWT issuer
        algorithm: JWT algorithm
        expires_in_minutes: Token expiration in minutes
        
    Returns:
        JWT token string
    """
    if not JOSE_AVAILABLE:
        raise ImportError("python-jose is required to generate JWT tokens")
    
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_in_minutes)
    
    payload = {
        "iss": issuer,
        "sub": user_id,
        "scopes": scopes,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": f"test-{int(now.timestamp())}"
    }
    
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    return token


def main():
    """Generate and print a JWT token."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate JWT token for MCP server")
    parser.add_argument(
        "--user-id",
        default="12345",
        help="User ID (default: 12345)"
    )
    parser.add_argument(
        "--scopes",
        nargs="+",
        default=["read"],
        help="Scopes (default: read)"
    )
    parser.add_argument(
        "--secret-key",
        default=os.getenv("MCP_JWT_SECRET_KEY", DEFAULT_SECRET_KEY),
        help="JWT secret key (default: from env or config default)"
    )
    parser.add_argument(
        "--issuer",
        default=os.getenv("MCP_JWT_ISSUER", DEFAULT_ISSUER),
        help="JWT issuer (default: orchestrator)"
    )
    parser.add_argument(
        "--expires",
        type=int,
        default=15,
        help="Expiration in minutes (default: 15)"
    )
    
    args = parser.parse_args()
    
    if not JOSE_AVAILABLE:
        print("\n" + "=" * 80)
        print("ERROR: Cannot generate token - python-jose is not installed")
        print("=" * 80)
        print("\nTo install:")
        print("  pip install python-jose[cryptography]")
        print("  or")
        print("  uv pip install python-jose[cryptography]")
        print("\n" + "=" * 80)
        sys.exit(1)
    
    token = generate_jwt_token(
        user_id=args.user_id,
        scopes=args.scopes,
        secret_key=args.secret_key,
        issuer=args.issuer,
        expires_in_minutes=args.expires
    )
    
    print("=" * 80)
    print("JWT Token for MCP Server")
    print("=" * 80)
    print(f"\nToken:\n{token}\n")
    print("=" * 80)
    print("\nToken Details:")
    print(f"  User ID: {args.user_id}")
    print(f"  Scopes: {', '.join(args.scopes)}")
    print(f"  Issuer: {args.issuer}")
    print(f"  Secret Key: {args.secret_key[:20]}..." if len(args.secret_key) > 20 else f"  Secret Key: {args.secret_key}")
    print(f"  Expires in: {args.expires} minutes")
    print("=" * 80)
    print("\nTo use this token, pass it as the 'jwt_token' parameter to MCP tools.")
    print("Example: get_balance(jwt_token='<token>', account_type='checking')")
    print("=" * 80)
    
    return token


if __name__ == "__main__":
    main()
