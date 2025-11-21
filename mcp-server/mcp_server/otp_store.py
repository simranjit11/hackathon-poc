"""
OTP Storage and Management
===========================
In-memory OTP storage for testing. In production, use Redis or database.
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)


class OTPStore:
    """
    In-memory OTP storage for payment verification.
    Stores OTP with expiry time for each order.
    """
    
    # Hardcoded OTP for testing
    TEST_OTP = "123456"
    
    # OTP expiry time in minutes
    OTP_EXPIRY_MINUTES = 10
    
    def __init__(self):
        """Initialize OTP store."""
        # Format: {order_id: {"otp": "123456", "expires_at": datetime, "phone": "9999999999"}}
        self._store: Dict[str, Dict] = {}
        logger.info("OTP Store initialized")
    
    def generate_otp(self, order_id: str, phone_number: str, use_test_otp: bool = True) -> str:
        """
        Generate and store OTP for an order.
        
        Args:
            order_id: Cashfree order ID
            phone_number: Customer phone number
            use_test_otp: If True, use hardcoded TEST_OTP, else generate random
            
        Returns:
            Generated OTP string
        """
        if use_test_otp:
            otp = self.TEST_OTP
            logger.info(f"Using hardcoded TEST OTP: {otp} for order: {order_id}")
        else:
            otp = str(random.randint(100000, 999999))
            logger.info(f"Generated random OTP for order: {order_id}")
        
        expires_at = datetime.now() + timedelta(minutes=self.OTP_EXPIRY_MINUTES)
        
        self._store[order_id] = {
            "otp": otp,
            "expires_at": expires_at,
            "phone": phone_number,
            "created_at": datetime.now()
        }
        
        logger.info(
            f"OTP stored for order: {order_id}, phone: {phone_number}, "
            f"expires at: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return otp
    
    def verify_otp(self, order_id: str, otp: str) -> bool:
        """
        Verify OTP for an order.
        
        Args:
            order_id: Cashfree order ID
            otp: OTP to verify
            
        Returns:
            True if OTP is valid and not expired, False otherwise
        """
        if order_id not in self._store:
            logger.warning(f"No OTP found for order: {order_id}")
            return False
        
        otp_data = self._store[order_id]
        stored_otp = otp_data["otp"]
        expires_at = otp_data["expires_at"]
        
        # Check if expired
        if datetime.now() > expires_at:
            logger.warning(f"OTP expired for order: {order_id}")
            return False
        
        # Check if OTP matches
        if otp != stored_otp:
            logger.warning(f"Invalid OTP for order: {order_id}")
            return False
        
        logger.info(f"OTP verified successfully for order: {order_id}")
        return True
    
    def get_otp_info(self, order_id: str) -> Optional[Dict]:
        """
        Get OTP information for an order (for debugging).
        
        Args:
            order_id: Cashfree order ID
            
        Returns:
            OTP data dict or None if not found
        """
        return self._store.get(order_id)
    
    def delete_otp(self, order_id: str) -> bool:
        """
        Delete OTP for an order (after successful payment).
        
        Args:
            order_id: Cashfree order ID
            
        Returns:
            True if deleted, False if not found
        """
        if order_id in self._store:
            del self._store[order_id]
            logger.info(f"OTP deleted for order: {order_id}")
            return True
        return False
    
    def cleanup_expired(self) -> int:
        """
        Remove expired OTPs from store.
        
        Returns:
            Number of expired OTPs removed
        """
        now = datetime.now()
        expired_orders = [
            order_id for order_id, data in self._store.items()
            if data["expires_at"] < now
        ]
        
        for order_id in expired_orders:
            del self._store[order_id]
        
        if expired_orders:
            logger.info(f"Cleaned up {len(expired_orders)} expired OTPs")
        
        return len(expired_orders)


# Global OTP store instance
otp_store = OTPStore()
