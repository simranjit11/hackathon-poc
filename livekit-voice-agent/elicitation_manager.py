"""
Elicitation Manager for Redis State Management
===============================================
Manages elicitation state, queue, and lifecycle in Redis.
"""

import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import redis
from dotenv import load_dotenv
import os

from schemas.elicitation import (
    ElicitationState,
    ElicitationSchema,
    ElicitationStatus,
    ElicitationContext,
    create_otp_elicitation,
    create_confirmation_elicitation,
)

load_dotenv()

logger = logging.getLogger(__name__)


class ElicitationManager:
    """Manages elicitation state and queue in Redis."""

    def __init__(self):
        """Initialize Redis connection for elicitation management."""
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
            logger.info("Elicitation manager connected to Redis")
        except redis.ConnectionError as e:
            logger.error(f"Could not connect to Redis: {e}")
            raise

        # Default timeout for elicitations (5 minutes)
        self.default_timeout_seconds = int(
            os.getenv("ELICITATION_TIMEOUT_SECONDS", "300")
        )

    def create_elicitation(
        self,
        tool_call_id: str,
        mcp_endpoint: str,
        user_id: str,
        session_id: str,
        room_name: str,
        schema: ElicitationSchema,
        suspended_tool_arguments: Dict[str, Any],
        timeout_seconds: Optional[int] = None,
    ) -> ElicitationState:
        """
        Create a new elicitation and store in Redis.

        Args:
            tool_call_id: ID of the suspended tool call
            mcp_endpoint: MCP endpoint that created this elicitation
            user_id: User identifier
            session_id: Session identifier
            room_name: LiveKit room name
            schema: Elicitation schema
            suspended_tool_arguments: Arguments to resume tool with
            timeout_seconds: Timeout in seconds (default: 300)

        Returns:
            ElicitationState object
        """
        elicitation_id = schema.elicitation_id
        timeout = timeout_seconds or self.default_timeout_seconds
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=timeout)

        state = ElicitationState(
            elicitation_id=elicitation_id,
            tool_call_id=tool_call_id,
            mcp_endpoint=mcp_endpoint,
            user_id=user_id,
            session_id=session_id,
            room_name=room_name,
            status=ElicitationStatus.PENDING,
            schema=schema,
            created_at=now,
            expires_at=expires_at,
            suspended_tool_arguments=suspended_tool_arguments,
        )

        # Store in Redis
        self._store_elicitation(state, timeout)

        # Add to queue
        self._add_to_queue(session_id, elicitation_id)

        logger.info(
            f"Created elicitation {elicitation_id} for session {session_id}, "
            f"expires at {expires_at.isoformat()}"
        )

        return state

    def _store_elicitation(self, state: ElicitationState, ttl_seconds: int):
        """Store elicitation state in Redis with TTL."""
        key = f"elicitation:{state.elicitation_id}"

        # Convert to dict for Redis storage
        data = {
            "elicitation_id": state.elicitation_id,
            "tool_call_id": state.tool_call_id,
            "mcp_endpoint": state.mcp_endpoint,
            "user_id": state.user_id,
            "session_id": state.session_id,
            "room_name": state.room_name,
            "status": state.status.value,
            "schema": state.schema.model_dump_json(),
            "created_at": state.created_at.isoformat(),
            "expires_at": state.expires_at.isoformat(),
            "suspended_tool_arguments": json.dumps(state.suspended_tool_arguments),
        }

        try:
            self.redis_client.hset(key, mapping=data)
            self.redis_client.expire(key, ttl_seconds + 60)  # Extra 60s buffer
            logger.debug(f"Stored elicitation {state.elicitation_id} in Redis")
        except redis.RedisError as e:
            logger.error(f"Error storing elicitation: {e}")
            raise

    def get_elicitation(self, elicitation_id: str) -> Optional[ElicitationState]:
        """
        Retrieve elicitation state from Redis.

        Args:
            elicitation_id: Elicitation identifier

        Returns:
            ElicitationState or None if not found
        """
        key = f"elicitation:{elicitation_id}"

        try:
            data = self.redis_client.hgetall(key)
            if not data:
                logger.warning(f"Elicitation {elicitation_id} not found")
                return None

            # Parse stored data
            schema_data = json.loads(data["schema"])
            schema = ElicitationSchema(**schema_data)

            state = ElicitationState(
                elicitation_id=data["elicitation_id"],
                tool_call_id=data["tool_call_id"],
                mcp_endpoint=data["mcp_endpoint"],
                user_id=data["user_id"],
                session_id=data["session_id"],
                room_name=data["room_name"],
                status=ElicitationStatus(data["status"]),
                schema=schema,
                created_at=datetime.fromisoformat(data["created_at"]),
                expires_at=datetime.fromisoformat(data["expires_at"]),
                suspended_tool_arguments=json.loads(data["suspended_tool_arguments"]),
            )

            return state

        except (redis.RedisError, KeyError, ValueError) as e:
            logger.error(f"Error retrieving elicitation {elicitation_id}: {e}")
            return None

    def update_elicitation_status(
        self, elicitation_id: str, status: ElicitationStatus
    ) -> bool:
        """
        Update elicitation status in Redis.

        Args:
            elicitation_id: Elicitation identifier
            status: New status

        Returns:
            True if successful, False otherwise
        """
        key = f"elicitation:{elicitation_id}"

        try:
            # Check if exists
            if not self.redis_client.exists(key):
                logger.warning(f"Cannot update non-existent elicitation {elicitation_id}")
                return False

            self.redis_client.hset(key, "status", status.value)
            logger.info(f"Updated elicitation {elicitation_id} status to {status.value}")
            return True

        except redis.RedisError as e:
            logger.error(f"Error updating elicitation status: {e}")
            return False

    def delete_elicitation(self, elicitation_id: str) -> bool:
        """
        Delete elicitation from Redis.

        Args:
            elicitation_id: Elicitation identifier

        Returns:
            True if deleted, False otherwise
        """
        key = f"elicitation:{elicitation_id}"

        try:
            deleted = self.redis_client.delete(key)
            if deleted:
                logger.info(f"Deleted elicitation {elicitation_id}")
            return deleted > 0
        except redis.RedisError as e:
            logger.error(f"Error deleting elicitation: {e}")
            return False

    def _add_to_queue(self, session_id: str, elicitation_id: str):
        """Add elicitation to sequential queue for session."""
        queue_key = f"elicitation_queue:{session_id}"

        try:
            # Add to left of list (FIFO queue when popping from right)
            self.redis_client.lpush(queue_key, elicitation_id)
            # Set expiration on queue (1 hour)
            self.redis_client.expire(queue_key, 3600)
            logger.debug(f"Added elicitation {elicitation_id} to queue for session {session_id}")
        except redis.RedisError as e:
            logger.error(f"Error adding to queue: {e}")
            raise

    def get_next_in_queue(self, session_id: str) -> Optional[str]:
        """
        Get next elicitation from queue without removing it.

        Args:
            session_id: Session identifier

        Returns:
            Elicitation ID or None if queue is empty
        """
        queue_key = f"elicitation_queue:{session_id}"

        try:
            # Get from right of list without removing (index -1)
            elicitation_id = self.redis_client.lindex(queue_key, -1)
            return elicitation_id
        except redis.RedisError as e:
            logger.error(f"Error getting next in queue: {e}")
            return None

    def remove_from_queue(self, session_id: str, elicitation_id: str) -> bool:
        """
        Remove elicitation from queue.

        Args:
            session_id: Session identifier
            elicitation_id: Elicitation to remove

        Returns:
            True if removed, False otherwise
        """
        queue_key = f"elicitation_queue:{session_id}"

        try:
            # Remove all occurrences of this elicitation_id
            removed = self.redis_client.lrem(queue_key, 0, elicitation_id)
            if removed:
                logger.debug(f"Removed elicitation {elicitation_id} from queue")
            return removed > 0
        except redis.RedisError as e:
            logger.error(f"Error removing from queue: {e}")
            return False

    def get_queue_length(self, session_id: str) -> int:
        """Get number of elicitations in queue for session."""
        queue_key = f"elicitation_queue:{session_id}"

        try:
            return self.redis_client.llen(queue_key)
        except redis.RedisError as e:
            logger.error(f"Error getting queue length: {e}")
            return 0

    def cancel_elicitation(self, elicitation_id: str, reason: str = "Cancelled") -> bool:
        """
        Cancel an elicitation.

        Args:
            elicitation_id: Elicitation identifier
            reason: Cancellation reason

        Returns:
            True if cancelled, False otherwise
        """
        state = self.get_elicitation(elicitation_id)
        if not state:
            return False

        # Update status
        if not self.update_elicitation_status(elicitation_id, ElicitationStatus.CANCELLED):
            return False

        # Remove from queue
        self.remove_from_queue(state.session_id, elicitation_id)

        logger.info(f"Cancelled elicitation {elicitation_id}: {reason}")
        return True

    def find_expired_elicitations(self) -> List[str]:
        """
        Find all expired elicitations.

        Returns:
            List of expired elicitation IDs
        """
        expired = []
        now = datetime.utcnow()

        try:
            # Scan for all elicitation keys
            for key in self.redis_client.scan_iter("elicitation:*"):
                data = self.redis_client.hgetall(key)
                if not data:
                    continue

                status = data.get("status")
                expires_at_str = data.get("expires_at")

                if status == ElicitationStatus.PENDING.value and expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if now > expires_at:
                        elicitation_id = data.get("elicitation_id")
                        if elicitation_id:
                            expired.append(elicitation_id)

        except redis.RedisError as e:
            logger.error(f"Error finding expired elicitations: {e}")

        return expired

    def mark_expired(self, elicitation_id: str) -> bool:
        """
        Mark elicitation as expired and clean up.

        Args:
            elicitation_id: Elicitation identifier

        Returns:
            True if marked expired, False otherwise
        """
        state = self.get_elicitation(elicitation_id)
        if not state:
            return False

        # Update status
        if not self.update_elicitation_status(elicitation_id, ElicitationStatus.EXPIRED):
            return False

        # Remove from queue
        self.remove_from_queue(state.session_id, elicitation_id)

        logger.info(f"Marked elicitation {elicitation_id} as expired")
        return True


# Global elicitation manager instance
_elicitation_manager: Optional[ElicitationManager] = None


def get_elicitation_manager() -> ElicitationManager:
    """Get or create the global elicitation manager instance."""
    global _elicitation_manager
    if _elicitation_manager is None:
        _elicitation_manager = ElicitationManager()
    return _elicitation_manager

