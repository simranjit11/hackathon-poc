"""
Stripe Payment Integration
==========================
Handles test payments using Stripe Payment Intents API.
"""

import stripe
from stripe import StripeError, InvalidRequestError
import logging
from typing import Dict, Optional

from mcp_server.config import settings

logger = logging.getLogger(__name__)

# Configure Stripe with test API key
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripePaymentService:
    """Service for handling Stripe test payments."""
    
    # Test card numbers for different scenarios
    TEST_CARDS = {
        "success": "4242424242424242",
        "decline": "4000000000000002",
        "insufficient_funds": "4000000000009995",
        "lost_card": "4000000000009987",
        "stolen_card": "4000000000009979",
        "3ds_required": "4000002500003155",
        "3ds_optional": "4000002760003184"
    }
    
    async def create_payment_intent(
        self,
        amount: float,
        currency: str = "inr",
        description: Optional[str] = None,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create a Payment Intent for test payment.
        
        Args:
            amount: Amount in currency (will be converted to smallest unit)
            currency: Currency code (default: INR)
            description: Payment description
            customer_email: Customer email for receipt
            metadata: Additional metadata
            
        Returns:
            Payment Intent details including client_secret
        """
        try:
            # Convert amount to smallest currency unit (paise for INR)
            amount_smallest_unit = int(amount * 100)
            
            logger.info(
                f"Creating Payment Intent: amount={amount_smallest_unit} {currency}"
            )
            
            # Create Payment Intent
            intent = stripe.PaymentIntent.create(
                amount=amount_smallest_unit,
                currency=currency.lower(),
                description=description,
                receipt_email=customer_email,
                metadata=metadata or {},
                automatic_payment_methods={
                    "enabled": True,
                    "allow_redirects": "never"  # Disable redirect payment methods
                },
            )
            
            logger.info(f"Payment Intent created: {intent.id}")
            
            return {
                "payment_intent_id": intent.id,
                "client_secret": intent.client_secret,
                "amount": amount,
                "currency": currency.upper(),
                "status": intent.status,
                "created": intent.created
            }
            
        except StripeError as e:
            logger.error(f"Stripe error: {e}")
            raise ValueError(f"Payment creation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating payment intent: {e}")
            raise ValueError(f"Failed to create payment: {str(e)}")
    
    async def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method: str = "pm_card_visa"  # Test payment method
    ) -> Dict:
        """
        Confirm a Payment Intent with test payment method.
        
        Args:
            payment_intent_id: Payment Intent ID to confirm
            payment_method: Test payment method ID (default: pm_card_visa)
            
        Returns:
            Updated Payment Intent status
        """
        try:
            logger.info(f"Confirming Payment Intent: {payment_intent_id}")
            
            # Confirm the payment
            intent = stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method=payment_method
            )
            
            logger.info(
                f"Payment Intent confirmed: {intent.id}, status: {intent.status}"
            )
            
            # Extract charges if available
            charges = []
            if hasattr(intent, 'charges') and hasattr(intent.charges, 'data'):
                charges = [
                    {
                        "id": charge.id,
                        "status": charge.status,
                        "paid": charge.paid
                    }
                    for charge in intent.charges.data
                ]
            
            return {
                "payment_intent_id": intent.id,
                "status": intent.status,
                "amount": intent.amount / 100,  # Convert back to major unit
                "currency": intent.currency.upper(),
                "charges": charges
            }
            
        except InvalidRequestError as e:
            logger.warning(f"Invalid request: {e}")
            raise ValueError(f"Payment declined: {str(e)}")
        except StripeError as e:
            logger.error(f"Stripe error: {e}")
            raise ValueError(f"Payment confirmation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error confirming payment: {e}")
            raise ValueError(f"Failed to confirm payment: {str(e)}")
    
    async def get_payment_status(self, payment_intent_id: str) -> Dict:
        """
        Get the current status of a Payment Intent.
        
        Args:
            payment_intent_id: Payment Intent ID
            
        Returns:
            Payment Intent status details
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                "payment_intent_id": intent.id,
                "status": intent.status,
                "amount": intent.amount / 100,
                "currency": intent.currency.upper(),
                "created": intent.created,
                "description": intent.description
            }
            
        except StripeError as e:
            logger.error(f"Stripe error: {e}")
            raise ValueError(f"Failed to retrieve payment: {str(e)}")
    
    async def simulate_test_payment(
        self,
        amount: float,
        scenario: str = "success",
        currency: str = "inr",
        description: Optional[str] = None,
        from_account: Optional[str] = None,
        to_account: Optional[str] = None
    ) -> Dict:
        """
        Simulate a complete test payment flow from one account to another.
        
        Args:
            amount: Payment amount
            scenario: Test scenario (success, decline, insufficient_funds, etc.)
            currency: Currency code
            description: Payment description
            from_account: Source account number
            to_account: Destination account number
            
        Returns:
            Complete payment result
        """
        try:
            # Build metadata
            metadata = {
                "scenario": scenario,
                "from_account": from_account or "N/A",
                "to_account": to_account or "N/A"
            }
            
            # Create Payment Intent
            intent_result = await self.create_payment_intent(
                amount=amount,
                currency=currency,
                description=description or f"Transfer from {from_account} to {to_account}",
                metadata=metadata
            )
            
            # Get test payment method based on scenario
            payment_method = self._get_test_payment_method(scenario)
            
            # Confirm payment
            confirm_result = await self.confirm_payment(
                payment_intent_id=intent_result["payment_intent_id"],
                payment_method=payment_method
            )
            
            return {
                **confirm_result,
                "test_scenario": scenario,
                "test_mode": True,
                "from_account": from_account,
                "to_account": to_account
            }
            
        except ValueError as e:
            # Return error details for test scenarios
            return {
                "status": "failed",
                "error": str(e),
                "test_scenario": scenario,
                "test_mode": True,
                "from_account": from_account,
                "to_account": to_account
            }
    
    def _get_test_payment_method(self, scenario: str) -> str:
        """Get test payment method ID based on scenario."""
        # Stripe test payment methods
        test_methods = {
            "success": "pm_card_visa",
            "decline": "pm_card_chargeDeclined",
            "insufficient_funds": "pm_card_chargeDeclinedInsufficientFunds",
            "3ds_required": "pm_card_threeDSecure2Required",
            "lost_card": "pm_card_chargeDeclinedLostCard",
            "stolen_card": "pm_card_chargeDeclinedStolenCard"
        }
        return test_methods.get(scenario, "pm_card_visa")
