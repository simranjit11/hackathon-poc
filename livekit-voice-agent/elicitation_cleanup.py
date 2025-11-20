"""
Elicitation Cleanup Background Task
====================================
Periodically checks for expired elicitations and cleans them up.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from elicitation_manager import get_elicitation_manager, ElicitationStatus

logger = logging.getLogger(__name__)


class ElicitationCleanupTask:
    """Background task to clean up expired elicitations."""

    def __init__(self, check_interval_seconds: int = 30):
        """
        Initialize cleanup task.

        Args:
            check_interval_seconds: How often to check for expired elicitations
        """
        self.check_interval = check_interval_seconds
        self.manager = get_elicitation_manager()
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the cleanup task."""
        if self._running:
            logger.warning("Cleanup task already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info(
            f"Started elicitation cleanup task (interval: {self.check_interval}s)"
        )

    async def stop(self):
        """Stop the cleanup task."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped elicitation cleanup task")

    async def _run(self):
        """Main cleanup loop."""
        while self._running:
            try:
                await self._cleanup_expired()
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

            # Wait for next check
            await asyncio.sleep(self.check_interval)

    async def _cleanup_expired(self):
        """Find and clean up expired elicitations."""
        try:
            # Find expired elicitations
            expired_ids = self.manager.find_expired_elicitations()

            if not expired_ids:
                return

            logger.info(f"Found {len(expired_ids)} expired elicitations")

            # Mark each as expired and notify
            for elicitation_id in expired_ids:
                try:
                    # Get state before marking expired
                    state = self.manager.get_elicitation(elicitation_id)
                    if not state:
                        continue

                    # Mark as expired
                    success = self.manager.mark_expired(elicitation_id)
                    if success:
                        logger.info(
                            f"Marked elicitation {elicitation_id} as expired "
                            f"(session: {state.session_id})"
                        )

                        # TODO: Notify client via LiveKit data channel
                        # This would require access to the LiveKit room/participant
                        # await self._notify_client_expired(state)

                except Exception as e:
                    logger.error(
                        f"Error marking elicitation {elicitation_id} as expired: {e}"
                    )

        except Exception as e:
            logger.error(f"Error finding expired elicitations: {e}")

    async def _notify_client_expired(self, state):
        """
        Notify client that elicitation has expired.

        This would send a message via LiveKit data channel to the client.
        Implementation depends on having access to the room/participant.

        Args:
            state: ElicitationState object
        """
        # TODO: Implement notification via LiveKit data channel
        # Example:
        # message = {
        #     "type": "elicitation_expired",
        #     "elicitation_id": state.elicitation_id,
        #     "message": "Elicitation has expired. Please try again."
        # }
        # await room.local_participant.publish_data(
        #     json.dumps(message),
        #     destination_sids=[state.participant_sid]
        # )
        pass


# Global cleanup task instance
_cleanup_task: Optional[ElicitationCleanupTask] = None


def get_cleanup_task(check_interval_seconds: int = 30) -> ElicitationCleanupTask:
    """Get or create the global cleanup task instance."""
    global _cleanup_task
    if _cleanup_task is None:
        _cleanup_task = ElicitationCleanupTask(check_interval_seconds)
    return _cleanup_task


async def start_cleanup_task(check_interval_seconds: int = 30):
    """Start the global cleanup task."""
    task = get_cleanup_task(check_interval_seconds)
    await task.start()


async def stop_cleanup_task():
    """Stop the global cleanup task."""
    if _cleanup_task:
        await _cleanup_task.stop()

