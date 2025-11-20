"""
Test script for Cashfree Payment Gateway Integration
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, ".env")
load_dotenv(env_path)

from mcp_server.cashfree_payment import CashfreePaymentService


async def test_cashfree_integration():
    """Test Cashfree payment integration."""
    
    print("=" * 80)
    print("Testing Cashfree Payment Gateway Integration")
    print("=" * 80)
    
    # Initialize service
    service = CashfreePaymentService()
    
    # Test 1: Create Order
    print("\n[TEST 1] Creating a test payment order...")
    print("-" * 80)
    
    order_result = await service.create_order(
        amount=100.00,
        customer_id="user_123",
        customer_name="Test User",
        customer_email="test@example.com",
        customer_phone="9999999999",
        order_note="Test payment order via MCP Server",
        return_url="https://www.cashfree.com/devstudio/preview/pg/web/checkout"
    )
    
    print("\n✅ Order Creation Result:")
    import json
    print(json.dumps(order_result, indent=2))
    
    if not order_result.get("success"):
        print("\n❌ Order creation failed. Please check your Cashfree credentials.")
        print("\nTo get test credentials:")
        print("1. Visit https://merchant.cashfree.com/merchant/login")
        print("2. Create a test account or login")
        print("3. Go to Developers > API Keys")
        print("4. Copy your TEST App ID and Secret Key")
        print("5. Update .env file with actual credentials")
        return
    
    order_id = order_result.get("order_id")
    payment_session_id = order_result.get("payment_session_id")
    
    print(f"\n✅ Order Created Successfully!")
    print(f"   Order ID: {order_id}")
    print(f"   Payment Session ID: {payment_session_id}")
    print(f"   Order Status: {order_result.get('order_status')}")
    
    # Test 2: Get Order Status
    print("\n[TEST 2] Fetching order status...")
    print("-" * 80)
    
    status_result = await service.get_order_status(order_id)
    
    print("\n✅ Order Status Result:")
    print(json.dumps(status_result, indent=2))
    
    if status_result.get("success"):
        print(f"\n✅ Order Status: {status_result.get('order_status')}")
        print(f"   Order Amount: ₹{status_result.get('order_amount')}")
        print(f"   Customer: {status_result.get('customer_details', {}).get('customer_name')}")
    
    # Test 3: Payment URL Info
    print("\n[TEST 3] Payment Processing Information")
    print("-" * 80)
    print("\n📝 To complete the payment, use this Payment Session ID in your frontend:")
    print(f"   {payment_session_id}")
    print("\n📝 Or test the payment using Cashfree's DevStudio:")
    print(f"   https://www.cashfree.com/devstudio/preview/pg/web/checkout?payment_session_id={payment_session_id}")
    print("\n📝 Test Card Details (for sandbox):")
    print("   Card Number: 4111 1111 1111 1111")
    print("   CVV: Any 3 digits")
    print("   Expiry: Any future date")
    print("   OTP: 123456")
    
    print("\n" + "=" * 80)
    print("✅ All tests completed successfully!")
    print("=" * 80)
    print("\n📌 Next Steps:")
    print("   1. Replace TEST credentials in .env with your actual Cashfree credentials")
    print("   2. Test the payment flow using MCP Inspector")
    print("   3. Use create_cashfree_order tool with a valid JWT token")
    print("   4. Check order status with get_cashfree_order_status tool")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_cashfree_integration())
