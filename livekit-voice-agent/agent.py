"""
LiveKit Voice Agent - Quick Start
==================================
The simplest possible LiveKit voice agent to get you started.
Requires only OpenAI and Deepgram API keys.
"""

from typing import Any
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession, RunContext
from livekit.agents.llm import function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from session_manager import get_session_manager

from datetime import datetime
import os
import json

# Load environment variables
load_dotenv()

class Assistant(Agent):
    """Banking voice assistant with comprehensive financial services."""

    def __init__(self):
        super().__init__(
            instructions="""You are a helpful and professional banking voice assistant.
            You can help customers with account balances, payments, transfers, transaction history,
            loan inquiries, and setting up alerts. Keep responses clear and professional."""
        )

        # Mock customer accounts database
        self.accounts = {
            "12345": {
                "customer_name": "John Doe",
                "checking": {"balance": 2547.83, "account_number": "CHK-12345-001"},
                "savings": {"balance": 15430.22, "account_number": "SAV-12345-002"},
                "credit_card": {"balance": 1250.45, "limit": 5000.00, "account_number": "CC-12345-003"}
            },
            "67890": {
                "customer_name": "Jane Smith",
                "checking": {"balance": 3821.67, "account_number": "CHK-67890-001"},
                "savings": {"balance": 25678.90, "account_number": "SAV-67890-002"},
                "credit_card": {"balance": 2100.30, "limit": 8000.00, "account_number": "CC-67890-003"}
            }
        }

        # Mock transaction history
        self.transactions = {
            "12345": [
                {"date": "2025-11-05", "description": "Grocery Store", "amount": -87.32, "type": "debit"},
                {"date": "2025-11-04", "description": "Salary Deposit", "amount": 3200.00, "type": "credit"},
                {"date": "2025-11-03", "description": "Gas Station", "amount": -45.67, "type": "debit"},
                {"date": "2025-11-02", "description": "Online Transfer", "amount": -500.00, "type": "transfer"},
                {"date": "2025-11-01", "description": "Coffee Shop", "amount": -12.95, "type": "debit"}
            ],
            "67890": [
                {"date": "2025-11-05", "description": "Rent Payment", "amount": -1800.00, "type": "debit"},
                {"date": "2025-11-04", "description": "Freelance Payment", "amount": 1250.00, "type": "credit"},
                {"date": "2025-11-03", "description": "Utility Bill", "amount": -125.40, "type": "debit"},
                {"date": "2025-11-02", "description": "Investment Deposit", "amount": -1000.00, "type": "transfer"},
                {"date": "2025-11-01", "description": "Restaurant", "amount": -85.60, "type": "debit"}
            ]
        }

        # Mock loan information
        self.loans = {
            "12345": [
                {"type": "Mortgage", "balance": 285000.00, "rate": 3.75, "monthly_payment": 1820.50},
                {"type": "Auto Loan", "balance": 18500.00, "rate": 4.25, "monthly_payment": 435.20}
            ],
            "67890": [
                {"type": "Personal Loan", "balance": 8500.00, "rate": 6.50, "monthly_payment": 275.80}
            ]
        }

        # Mock alerts and reminders
        self.alerts = {
            "12345": [
                {"type": "Payment Reminder", "description": "Credit card payment due Nov 15", "active": True},
                {"type": "Low Balance Alert", "description": "Alert when checking falls below $500", "active": True}
            ],
            "67890": [
                {"type": "Payment Reminder", "description": "Mortgage payment due Nov 10", "active": True}
            ]
        }

    @function_tool
    async def get_current_date_and_time(self, context: RunContext) -> str:
        """Get the current date and time."""
        current_datetime = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        return f"The current date and time is {current_datetime}"

    @function_tool
    async def check_account_balance(self, context: RunContext, customer_id: str, account_type: str = "checking") -> str:
        """Check account balance for a customer.

        Args:
            customer_id: Customer ID (e.g., '12345')
            account_type: Type of account - 'checking', 'savings', or 'credit_card'
        """
        if customer_id not in self.accounts:
            return f"Sorry, I couldn't find an account with ID {customer_id}. Please verify your customer ID."

        customer = self.accounts[customer_id]
        account_type = account_type.lower()

        if account_type not in customer:
            return f"Account type '{account_type}' not found. Available accounts: checking, savings, credit_card"

        account = customer[account_type]
        name = customer["customer_name"]

        if account_type == "credit_card":
            available_credit = account["limit"] - account["balance"]
            return f"Hello {name}! Your {account_type.replace('_', ' ')} account (ending in {account['account_number'][-3:]}) has:\n" \
                   f"Current balance: ${account['balance']:.2f}\n" \
                   f"Credit limit: ${account['limit']:.2f}\n" \
                   f"Available credit: ${available_credit:.2f}"
        else:
            return f"Hello {name}! Your {account_type} account (ending in {account['account_number'][-3:]}) balance is ${account['balance']:.2f}"

    @function_tool
    async def make_payment(self, context: RunContext, customer_id: str, from_account: str, to_account: str, amount: float, description: str = "") -> str:
        """Make a payment or transfer between accounts.

        Args:
            customer_id: Customer ID making the payment
            from_account: Source account ('checking', 'savings')
            to_account: Destination account or payee
            amount: Amount to transfer
            description: Optional description for the transaction
        """
        if customer_id not in self.accounts:
            return f"Customer ID {customer_id} not found."

        customer = self.accounts[customer_id]
        
        if from_account not in customer:
            return f"Source account '{from_account}' not found."

        if customer[from_account]["balance"] < amount:
            return f"Insufficient funds. Available balance: ${customer[from_account]['balance']:.2f}"

        # Process the payment
        customer[from_account]["balance"] -= amount
        
        # Add to transaction history
        if customer_id not in self.transactions:
            self.transactions[customer_id] = []
            
        self.transactions[customer_id].insert(0, {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "description": f"Payment to {to_account}" + (f" - {description}" if description else ""),
            "amount": -amount,
            "type": "payment"
        })

        confirmation_number = f"PAY{len(self.transactions[customer_id]) + 1000}"
        
        return f"Payment successful!\n" \
               f"Confirmation: {confirmation_number}\n" \
               f"From: {from_account.title()} account\n" \
               f"To: {to_account}\n" \
               f"Amount: ${amount:.2f}\n" \
               f"New {from_account} balance: ${customer[from_account]['balance']:.2f}"

    @function_tool
    async def view_transaction_history(self, context: RunContext, customer_id: str, num_transactions: int = 5) -> str:
        """View recent transaction history.

        Args:
            customer_id: Customer ID
            num_transactions: Number of recent transactions to show (default 5)
        """
        if customer_id not in self.accounts:
            return f"Customer ID {customer_id} not found."

        if customer_id not in self.transactions:
            return "No transaction history found for this account."

        transactions = self.transactions[customer_id][:num_transactions]
        customer_name = self.accounts[customer_id]["customer_name"]
        
        result = f"Recent transactions for {customer_name}:\n\n"
        
        for i, txn in enumerate(transactions, 1):
            amount_str = f"+${abs(txn['amount']):.2f}" if txn['amount'] > 0 else f"-${abs(txn['amount']):.2f}"
            result += f"{i}. {txn['date']} - {txn['description']}: {amount_str}\n"
        
        return result

    @function_tool
    async def inquire_about_loans(self, context: RunContext, customer_id: str) -> str:
        """Get information about customer's loans and interest rates.

        Args:
            customer_id: Customer ID
        """
        if customer_id not in self.accounts:
            return f"Customer ID {customer_id} not found."

        customer_name = self.accounts[customer_id]["customer_name"]
        
        if customer_id not in self.loans or not self.loans[customer_id]:
            return f"Hello {customer_name}! You currently have no active loans with us. " \
                   f"Would you like information about our current loan products and rates?"

        loans = self.loans[customer_id]
        result = f"Hello {customer_name}! Here are your current loans:\n\n"
        
        total_monthly = 0
        for i, loan in enumerate(loans, 1):
            result += f"{i}. {loan['type']}\n"
            result += f"   Balance: ${loan['balance']:,.2f}\n"
            result += f"   Interest Rate: {loan['rate']:.2f}%\n"
            result += f"   Monthly Payment: ${loan['monthly_payment']:.2f}\n\n"
            total_monthly += loan['monthly_payment']
        
        result += f"Total monthly loan payments: ${total_monthly:.2f}\n\n"
        result += "Current rates for new loans:\n"
        result += "• Personal Loans: 5.99% - 18.99% APR\n"
        result += "• Auto Loans: 3.49% - 8.99% APR\n"
        result += "• Mortgages: 6.50% - 7.25% APR"
        
        return result

    @function_tool
    async def check_credit_limit(self, context: RunContext, customer_id: str) -> str:
        """Check credit card limits and available credit.

        Args:
            customer_id: Customer ID
        """
        if customer_id not in self.accounts:
            return f"Customer ID {customer_id} not found."

        customer = self.accounts[customer_id]
        customer_name = customer["customer_name"]
        
        if "credit_card" not in customer:
            return f"Hello {customer_name}! You don't have a credit card account with us. " \
                   f"Would you like information about our credit card products?"

        cc = customer["credit_card"]
        available_credit = cc["limit"] - cc["balance"]
        utilization = (cc["balance"] / cc["limit"]) * 100
        
        result = f"Hello {customer_name}! Your credit card information:\n\n"
        result += f"Credit Limit: ${cc['limit']:,.2f}\n"
        result += f"Current Balance: ${cc['balance']:,.2f}\n"
        result += f"Available Credit: ${available_credit:,.2f}\n"
        result += f"Credit Utilization: {utilization:.1f}%\n\n"
        
        if utilization > 80:
            result += "⚠️ Your credit utilization is high. Consider making a payment to improve your credit score."
        elif utilization < 30:
            result += "✓ Great job! Your credit utilization is in a healthy range."
        
        return result

    @function_tool
    async def set_payment_reminder(self, context: RunContext, customer_id: str, reminder_type: str, description: str, due_date: str = "") -> str:
        """Set up payment reminders or alerts.

        Args:
            customer_id: Customer ID
            reminder_type: Type of reminder ('payment', 'low_balance', 'large_transaction')
            description: Description of the reminder
            due_date: Due date for payment reminders (optional)
        """
        if customer_id not in self.accounts:
            return f"Customer ID {customer_id} not found."

        customer_name = self.accounts[customer_id]["customer_name"]
        
        if customer_id not in self.alerts:
            self.alerts[customer_id] = []

        alert = {
            "type": reminder_type.replace('_', ' ').title() + " Alert",
            "description": description + (f" (Due: {due_date})" if due_date else ""),
            "active": True
        }
        
        self.alerts[customer_id].append(alert)
        
        return f"Reminder set successfully for {customer_name}!\n\n" \
               f"Type: {alert['type']}\n" \
               f"Description: {alert['description']}\n" \
               f"Status: Active\n\n" \
               f"You'll receive notifications for this reminder."

    @function_tool
    async def view_alerts(self, context: RunContext, customer_id: str) -> str:
        """View active payment alerts and reminders.

        Args:
            customer_id: Customer ID
        """
        if customer_id not in self.accounts:
            return f"Customer ID {customer_id} not found."

        customer_name = self.accounts[customer_id]["customer_name"]
        
        if customer_id not in self.alerts or not self.alerts[customer_id]:
            return f"Hello {customer_name}! You have no active alerts or reminders set up."

        alerts = self.alerts[customer_id]
        result = f"Active alerts for {customer_name}:\n\n"
        
        for i, alert in enumerate(alerts, 1):
            status = "🟢 Active" if alert["active"] else "🔴 Inactive"
            result += f"{i}. {alert['type']} - {status}\n"
            result += f"   {alert['description']}\n\n"
        
        return result

    @function_tool
    async def get_interest_rates(self, context: RunContext) -> str:
        """Get current interest rates for various banking products."""
        return """Current Interest Rates (as of November 2025):

💰 DEPOSIT ACCOUNTS:
• Checking Account: 0.10% APY
• Savings Account: 4.25% APY
• Money Market: 4.50% APY
• 12-Month CD: 5.00% APY
• 24-Month CD: 4.75% APY

💳 CREDIT PRODUCTS:
• Credit Cards: 15.99% - 24.99% APR
• Personal Loans: 5.99% - 18.99% APR
• Auto Loans: 3.49% - 8.99% APR
• Home Equity Line: 7.25% - 9.50% APR

🏠 MORTGAGE RATES:
• 30-Year Fixed: 7.125% APR
• 15-Year Fixed: 6.625% APR
• 5/1 ARM: 6.250% APR

Rates are subject to change and based on creditworthiness. Contact us for personalized rates!"""        

async def entrypoint(ctx: agents.JobContext):
    """
    Entrypoint for LiveKit voice agent.
    Initializes session with user identity from participant metadata.
    """
    room = ctx.room
    room_name = room.name

    # Extract user identity from participant metadata
    user_id = None
    email = None
    roles = ["customer"]
    permissions = ["read"]
    platform = "web"

    # Get the first remote participant (the user)
    # In LiveKit, participants include both local and remote participants
    for participant in room.remote_participants.values():
        if participant.metadata:
            try:
                metadata = json.loads(participant.metadata)
                user_id = metadata.get("user_id")
                email = metadata.get("email")
                roles = metadata.get("roles", ["customer"])
                permissions = metadata.get("permissions", ["read"])
                # Determine platform from metadata or participant name
                platform = metadata.get("platform", "web")
                break
            except (json.JSONDecodeError, AttributeError) as e:
                print(f"Error parsing participant metadata: {e}")
                continue

    # If no metadata found, try to extract from participant identity
    # Fallback: use participant identity if it follows the pattern voice_assistant_user_{user_id}
    if not user_id:
        for participant in room.remote_participants.values():
            identity = participant.identity
            if identity and identity.startswith("voice_assistant_user_"):
                user_id = identity.replace("voice_assistant_user_", "")
                # Use default values if metadata not available
                email = f"user_{user_id}@example.com"
                break

    # Initialize session in Redis if user_id is available
    session_manager = get_session_manager()
    if user_id:
        try:
            session_key = session_manager.create_session(
                user_id=user_id,
                email=email or f"user_{user_id}@example.com",
                roles=roles if isinstance(roles, list) else [roles],
                permissions=permissions if isinstance(permissions, list) else [permissions],
                room_name=room_name,
                platform=platform,
            )
            print(f"Session initialized: {session_key}")
            print(f"User: {user_id} ({email}), Roles: {roles}, Permissions: {permissions}")
        except Exception as e:
            print(f"Warning: Could not create session: {e}")
            print("Continuing without session management...")
    else:
        print("Warning: No user_id found in participant metadata. Session not created.")

    # Create agent session
    agent_session = AgentSession(
        stt="assemblyai/universal-streaming:en",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-3:a167e0f3-df7e-4d52-a9c3-f949145efdab",  # Male voice
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    # Start the session
    await agent_session.start(
        room=room,
        agent=Assistant()
    )

    # Generate initial greeting
    await agent_session.generate_reply(
        instructions="Greet the user professionally as a banking assistant and ask for their customer ID to help with their banking needs."
    )

if __name__ == "__main__":
    # Run the agent
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))