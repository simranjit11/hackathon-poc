"""
Redis Session Manager for LiveKit Voice Agent

Manages user sessions in Redis, storing user identity, session metadata,
and conversation context for the voice assistant.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import redis
from dotenv import load_dotenv

load_dotenv()


class SessionManager:
    """Manages Redis sessions for voice assistant users."""

    def __init__(self):
        """Initialize Redis connection."""
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD")
        redis_db = int(os.getenv("REDIS_DB", "0"))

        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            db=redis_db,
            decode_responses=True,
        )

        # Test connection
        try:
            self.redis_client.ping()
        except redis.ConnectionError as e:
            print(f"Warning: Could not connect to Redis: {e}")
            print("Session management will be disabled.")

    def create_session(
        self,
        user_id: str,
        email: str,
        roles: list[str],
        permissions: list[str],
        room_name: str,
        platform: str = "web",
    ) -> str:
        """
        Create a new session in Redis.

        Args:
            user_id: User identifier
            email: User email address
            roles: List of user roles
            permissions: List of user permissions
            room_name: LiveKit room name
            platform: Platform type ("web" or "mobile")

        Returns:
            Session key
        """
        session_key = f"session:{room_name}:{user_id}"
        session_start = datetime.utcnow().isoformat()

        session_data = {
            "user_id": user_id,
            "email": email,
            "roles": json.dumps(roles),
            "permissions": json.dumps(permissions),
            "session_start": session_start,
            "room_name": room_name,
            "platform": platform,
        }

        # Set session with 1 hour TTL
        try:
            self.redis_client.hset(session_key, mapping=session_data)
            self.redis_client.expire(session_key, 3600)  # 1 hour
            print(f"Created session: {session_key}")
            return session_key
        except redis.RedisError as e:
            print(f"Error creating session: {e}")
            raise

    def get_session(self, room_name: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data from Redis.

        Args:
            room_name: LiveKit room name
            user_id: User identifier

        Returns:
            Session data dictionary or None if not found
        """
        session_key = f"session:{room_name}:{user_id}"

        try:
            session_data = self.redis_client.hgetall(session_key)
            if not session_data:
                return None

            # Parse JSON fields
            session_data["roles"] = json.loads(session_data.get("roles", "[]"))
            session_data["permissions"] = json.loads(
                session_data.get("permissions", "[]")
            )

            return session_data
        except redis.RedisError as e:
            print(f"Error retrieving session: {e}")
            return None

    def update_session(
        self, room_name: str, user_id: str, updates: Dict[str, Any]
    ) -> bool:
        """
        Update session data in Redis.

        Args:
            room_name: LiveKit room name
            user_id: User identifier
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        session_key = f"session:{room_name}:{user_id}"

        try:
            # Convert lists to JSON strings if needed
            processed_updates = {}
            for key, value in updates.items():
                if isinstance(value, (list, dict)):
                    processed_updates[key] = json.dumps(value)
                else:
                    processed_updates[key] = value

            self.redis_client.hset(session_key, mapping=processed_updates)
            return True
        except redis.RedisError as e:
            print(f"Error updating session: {e}")
            return False

    def delete_session(self, room_name: str, user_id: str) -> bool:
        """
        Delete a session from Redis.

        Args:
            room_name: LiveKit room name
            user_id: User identifier

        Returns:
            True if successful, False otherwise
        """
        session_key = f"session:{room_name}:{user_id}"

        try:
            deleted = self.redis_client.delete(session_key)
            return deleted > 0
        except redis.RedisError as e:
            print(f"Error deleting session: {e}")
            return False

    def extend_session_ttl(self, room_name: str, user_id: str, seconds: int = 3600) -> bool:
        """
        Extend the TTL of a session.

        Args:
            room_name: LiveKit room name
            user_id: User identifier
            seconds: Number of seconds to extend TTL (default: 1 hour)

        Returns:
            True if successful, False otherwise
        """
        session_key = f"session:{room_name}:{user_id}"

        try:
            return self.redis_client.expire(session_key, seconds)
        except redis.RedisError as e:
            print(f"Error extending session TTL: {e}")
            return False


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager

