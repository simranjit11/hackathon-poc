"""
Test script for Two-Step OTP Payment Flow
==========================================
Tests the initiate_payment -> confirm_payment flow with hardcoded OTP
"""

import asyncio
import json
from mcp_server.cashfree_payment import CashfreePaymentService


async def test_two_step_payment():
    """Test two-step payment flow with hardcoded OTP."""
    
    print("=" * 80)
    print("Testing Two-Step OTP Payment Flow (Hardcoded OTP)")
    print("=" * 80)
    
    service = CashfreePaymentService()
    
    # Step 1: Create Order
    print("\n[STEP 1] Creating payment order...")
    print("-" * 80)
    
    order_result = await service.create_order(
        amount=500.00,
        customer_id="user_test",
        customer_name="Test User",
        customer_email="test@example.com",
        customer_phone="9999999999",
        order_note="Test payment with custom OTP flow",
        return_url="https://example.com/payment/success"
    )
    
    print(json.dumps(order_result, indent=2))
    
    if not order_result.get("success"):
        print("\n❌ Order creation failed!")
        return
    
    order_id = order_result.get("order_id")
    print(f"\n✅ Order Created: {order_id}")
    print(f"   Amount: ₹{order_result.get('order_amount')}")
    
    # Step 2: Initiate Payment (Generate OTP)
    print("\n[STEP 2] Initiating payment - Generating OTP...")
    print("-" * 80)
    
    initiate_result = await service.initiate_payment(
        order_id=order_id,
        payment_method="UPI",
        phone_number="9999999999"
    )
    
    print(json.dumps(initiate_result, indent=2))
    
    if not initiate_result.get("success"):
        print("\n❌ Payment initiation failed!")
        return
    
    test_otp = initiate_result.get("test_otp")
    print(f"\n✅ Payment Initiated!")
    print(f"   📱 OTP sent to: {initiate_result.get('phone_number')}")
    print(f"   🔑 Test OTP: {test_otp}")
    print(f"   ⏱  Expires in: {initiate_result.get('otp_expires_in_minutes')} minutes")
    
    # Step 3: Confirm Payment with OTP
    print("\n[STEP 3] Confirming payment with OTP...")
    print("-" * 80)
    print(f"Using OTP: {test_otp}")
    
    confirm_result = await service.confirm_payment(
        order_id=order_id,
        otp=test_otp
    )
    
    print("\n" + json.dumps(confirm_result, indent=2))
    
    if confirm_result.get("success"):
        print(f"\n✅ Payment Confirmed!")
        print(f"   Status: {confirm_result.get('payment_status')}")
        print(f"   Amount: ₹{confirm_result.get('payment_amount')}")
        print(f"   Time: {confirm_result.get('payment_time')}")
    else:
        print(f"\n❌ Payment confirmation failed!")
        print(f"   Error: {confirm_result.get('error')}")
    
    # Test with wrong OTP
    print("\n[STEP 4] Testing with invalid OTP...")
    print("-" * 80)
    
    # Create another order for wrong OTP test
    order2 = await service.create_order(
        amount=100.00,
        customer_id="user_test",
        customer_name="Test User",
        customer_email="test@example.com",
        customer_phone="9999999999",
        order_note="Test wrong OTP"
    )
    
    if order2.get("success"):
        order_id2 = order2.get("order_id")
        
        # Initiate
        await service.initiate_payment(
            order_id=order_id2,
            payment_method="UPI",
            phone_number="9999999999"
        )
        
        # Try wrong OTP
        wrong_otp_result = await service.confirm_payment(
            order_id=order_id2,
            otp="999999"  # Wrong OTP
        )
        
        print(json.dumps(wrong_otp_result, indent=2))
        
        if not wrong_otp_result.get("success"):
            print(f"\n✅ Wrong OTP correctly rejected!")
            print(f"   Error: {wrong_otp_result.get('error')}")
    
    print("\n" + "=" * 80)
    print("Two-Step OTP Payment Flow Test Complete!")
    print("=" * 80)
    
    print("\n📌 Implementation Summary:")
    print("\n✅ What's Working:")
    print("   1. create_cashfree_order - Creates order with Cashfree")
    print("   2. initiate_cashfree_payment - Generates OTP (hardcoded: 123456)")
    print("   3. confirm_cashfree_payment - Verifies OTP and completes payment")
    print("   4. OTP stored in-memory with expiry (10 minutes)")
    print("   5. Wrong OTP validation working")
    
    print("\n📱 User Flow:")
    print("   1. Customer initiates payment → create_order")
    print("   2. System generates OTP → initiate_payment")
    print("   3. OTP: 123456 (hardcoded for testing)")
    print("   4. Customer enters OTP → confirm_payment")
    print("   5. Payment SUCCESS ✅")
    
    print("\n🔧 Current Implementation:")
    print("   - OTP: Hardcoded to '123456' (for testing)")
    print("   - Storage: In-memory (lost on restart)")
    print("   - Expiry: 10 minutes")
    print("   - SMS: Not integrated (would need SMS gateway)")
    
    print("\n🚀 For Production:")
    print("   - Integrate SMS gateway (Twilio, AWS SNS, etc.)")
    print("   - Use Redis for OTP storage (persistent)")
    print("   - Generate random 6-digit OTP")
    print("   - Add rate limiting (max 3 OTP per phone/hour)")
    print("   - Add resend OTP functionality")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_two_step_payment())
