"""
Cashfree Payment Gateway Integration (HTTP-based)
=================================================
Service for handling Cashfree payment operations using direct HTTP requests.
This implementation bypasses SDK compatibility issues with Python 3.14.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
import uuid

from mcp_server.config import settings
from mcp_server.otp_store import otp_store

logger = logging.getLogger(__name__)


class CashfreePaymentService:
    """
    Service class for Cashfree Payment Gateway operations using HTTP API.
    
    Provides methods for:
    - Creating payment orders
    - Verifying payment status
    - Getting payment details
    - Processing refunds
    """
    
    BASE_URL_TEST = "https://sandbox.cashfree.com/pg"
    BASE_URL_PROD = "https://api.cashfree.com/pg"
    API_VERSION = "2023-08-01"
    
    def __init__(self):
        """Initialize Cashfree Payment Gateway client."""
        self.app_id = settings.CASHFREE_APP_ID
        self.secret_key = settings.CASHFREE_SECRET_KEY
        self.environment = settings.CASHFREE_ENV
        
        self.base_url = self.BASE_URL_TEST if self.environment == "TEST" else self.BASE_URL_PROD
        
        logger.info(f"Cashfree Payment Service initialized in {self.environment} mode")
        logger.info(f"Using base URL: {self.base_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Cashfree API requests."""
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-version": self.API_VERSION,
            "x-client-id": self.app_id,
            "x-client-secret": self.secret_key,
        }
    
    async def create_order(
        self,
        amount: float,
        customer_id: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        order_currency: str = "INR",
        order_note: Optional[str] = None,
        return_url: Optional[str] = None,
        notify_url: Optional[str] = None,
        order_tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a Cashfree payment order.
        
        Args:
            amount: Order amount (minimum 1.00 INR)
            customer_id: Unique customer identifier
            customer_name: Customer name
            customer_email: Customer email
            customer_phone: Customer phone number
            order_currency: Currency code (default: INR)
            order_note: Optional order note/description
            return_url: URL to redirect after payment
            notify_url: Webhook URL for payment notifications
            order_tags: Additional metadata tags
            
        Returns:
            Dict containing:
                - success: True if order created successfully
                - order_id: Cashfree order ID
                - payment_session_id: Session ID for payment
                - order_status: Current order status
                - order_amount: Order amount
                - order_currency: Order currency
                
        Raises:
            Exception: If order creation fails
        """
        try:
            # Generate unique order ID
            order_id = f"order_{customer_id}_{int(datetime.now().timestamp())}"
            
            # Prepare order request
            order_data = {
                "order_id": order_id,
                "order_amount": amount,
                "order_currency": order_currency,
                "customer_details": {
                    "customer_id": customer_id,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                },
            }
            
            # Add optional fields
            if order_note:
                order_data["order_note"] = order_note
            
            if return_url:
                order_data["order_meta"] = {
                    "return_url": return_url
                }
                if notify_url:
                    order_data["order_meta"]["notify_url"] = notify_url
            
            if order_tags:
                order_data["order_tags"] = order_tags
            
            logger.info(f"Creating Cashfree order: {order_id} for amount: {amount} {order_currency}")
            
            # Make API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/orders",
                    json=order_data,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                logger.info(f"Cashfree API response status: {response.status_code}")
                
                if response.status_code in [200, 201]:
                    response_data = response.json()
                    
                    logger.info(f"Order created successfully: {order_id}")
                    
                    return {
                        "success": True,
                        "order_id": response_data.get("order_id"),
                        "payment_session_id": response_data.get("payment_session_id"),
                        "order_status": response_data.get("order_status"),
                        "order_amount": response_data.get("order_amount"),
                        "order_currency": response_data.get("order_currency"),
                        "created_at": datetime.now().isoformat(),
                    }
                else:
                    error_data = response.json() if response.text else {}
                    error_message = error_data.get("message", "Unknown error")
                    logger.error(f"Failed to create order: {error_message}")
                    
                    return {
                        "success": False,
                        "error": error_message,
                        "error_code": error_data.get("code"),
                        "status_code": response.status_code,
                    }
        
        except Exception as e:
            logger.error(f"Error creating Cashfree order: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get Cashfree order status and details.
        
        Args:
            order_id: Cashfree order ID
            
        Returns:
            Dict containing:
                - success: True if status retrieved successfully
                - order_id: Order ID
                - order_status: Current order status
                - order_amount: Order amount
                - order_currency: Order currency
                - customer_details: Customer information
                - payment_details: Payment information (if paid)
                
        Raises:
            Exception: If status check fails
        """
        try:
            logger.info(f"Fetching Cashfree order status for: {order_id}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/orders/{order_id}",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    order_data = response.json()
                    
                    logger.info(f"Order status retrieved: {order_data.get('order_status')}")
                    
                    return {
                        "success": True,
                        "order_id": order_data.get("order_id"),
                        "order_status": order_data.get("order_status"),
                        "order_amount": order_data.get("order_amount"),
                        "order_currency": order_data.get("order_currency"),
                        "customer_details": order_data.get("customer_details"),
                        "order_note": order_data.get("order_note"),
                        "created_at": order_data.get("created_at"),
                    }
                else:
                    error_data = response.json() if response.text else {}
                    error_message = error_data.get("message", "Unknown error")
                    logger.error(f"Failed to get order status: {error_message}")
                    
                    return {
                        "success": False,
                        "error": error_message,
                        "status_code": response.status_code,
                    }
        
        except Exception as e:
            logger.error(f"Error getting Cashfree order status: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def get_payment_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get payment details for an order.
        
        Args:
            order_id: Cashfree order ID
            
        Returns:
            Dict containing payment details and status
        """
        try:
            logger.info(f"Fetching payment status for order: {order_id}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/orders/{order_id}/payments",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    payments = response.json()
                    
                    logger.info(f"Payment status retrieved for order: {order_id}")
                    
                    return {
                        "success": True,
                        "order_id": order_id,
                        "payments": payments,
                    }
                else:
                    error_data = response.json() if response.text else {}
                    return {
                        "success": False,
                        "error": error_data.get("message", "Unknown error"),
                        "status_code": response.status_code,
                    }
        
        except Exception as e:
            logger.error(f"Error getting payment status: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def verify_payment(self, order_id: str, order_amount: float) -> Dict[str, Any]:
        """
        Verify payment status and amount.
        
        Args:
            order_id: Cashfree order ID
            order_amount: Expected order amount
            
        Returns:
            Dict containing verification result
        """
        try:
            # Get order status
            order_status = await self.get_order_status(order_id)
            
            if not order_status.get("success"):
                return order_status
            
            # Verify amount matches
            actual_amount = order_status.get("order_amount")
            if abs(actual_amount - order_amount) > 0.01:  # Allow small floating point differences
                return {
                    "success": False,
                    "error": "Amount mismatch",
                    "expected_amount": order_amount,
                    "actual_amount": actual_amount,
                }
            
            # Check payment status
            payment_status = order_status.get("order_status")
            
            return {
                "success": True,
                "verified": payment_status == "PAID",
                "order_id": order_id,
                "order_status": payment_status,
                "order_amount": actual_amount,
            }
        
        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def initiate_payment(
        self,
        order_id: str,
        payment_method: str,
        phone_number: str,
        upi_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Initiate payment - Step 1: Generate OTP for payment verification.
        
        This generates a hardcoded OTP (123456) for testing.
        In production, this would integrate with SMS gateway to send real OTP.
        
        Args:
            order_id: Cashfree order ID
            payment_method: Payment method (UPI, CARD, NETBANKING)
            phone_number: Customer phone number (10 digits)
            upi_id: Optional UPI ID
            
        Returns:
            Dict with OTP sent confirmation
        """
        try:
            logger.info(f"Initiating payment with OTP for order: {order_id}")
            
            # Verify order exists
            order_status = await self.get_order_status(order_id)
            if not order_status.get("success"):
                return {
                    "success": False,
                    "error": "Order not found or invalid"
                }
            
            # Generate OTP (hardcoded for testing)
            otp = otp_store.generate_otp(order_id, phone_number, use_test_otp=True)
            
            logger.info(f"OTP generated for order: {order_id}, phone: {phone_number}")
            
            # In production, send SMS here:
            # await sms_service.send_otp(phone_number, otp)
            
            return {
                "success": True,
                "order_id": order_id,
                "phone_number": phone_number,
                "otp_sent": True,
                "message": f"OTP has been sent to {phone_number}. Please enter the OTP to complete payment.",
                "test_otp": otp,  # Only for testing! Remove in production
                "otp_expires_in_minutes": otp_store.OTP_EXPIRY_MINUTES,
                "initiated_at": datetime.now().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"Error initiating payment: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
    
    async def confirm_payment(
        self,
        order_id: str,
        otp: str,
        payment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Confirm payment - Step 2: Verify OTP and complete payment.
        
        This verifies the OTP entered by customer and marks payment as complete.
        In production, this would also call Cashfree's payment API.
        
        Args:
            order_id: Cashfree order ID
            otp: OTP entered by customer
            payment_id: Optional payment ID (not used currently)
            
        Returns:
            Dict with payment confirmation status
        """
        try:
            logger.info(f"Confirming payment with OTP for order: {order_id}")
            
            # Verify OTP
            is_valid = otp_store.verify_otp(order_id, otp)
            
            if not is_valid:
                logger.warning(f"Invalid or expired OTP for order: {order_id}")
                return {
                    "success": False,
                    "error": "Invalid or expired OTP",
                    "message": "The OTP you entered is incorrect or has expired. Please try again.",
                }
            
            # OTP verified successfully
            logger.info(f"OTP verified successfully for order: {order_id}")
            
            # Get order details
            order_status = await self.get_order_status(order_id)
            order_amount = order_status.get("order_amount", 0.0)
            
            # In production, would call Cashfree payment API here
            # For now, simulate successful payment
            
            # Delete OTP after successful verification
            otp_store.delete_otp(order_id)
            
            return {
                "success": True,
                "payment_status": "SUCCESS",
                "order_id": order_id,
                "payment_amount": order_amount,
                "payment_time": datetime.now().isoformat(),
                "message": "Payment completed successfully!",
                "confirmed_at": datetime.now().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"Error confirming payment: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
