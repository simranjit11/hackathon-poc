"""
LiveKit Voice Agent - Quick Start
==================================
The simplest possible LiveKit voice agent to get you started.
Requires only OpenAI and Deepgram API keys.
"""

from typing import Any, AsyncIterable
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents import Agent, AgentSession, RunContext, ModelSettings
from livekit.agents.llm import function_tool
from livekit.agents import log as agents_log

logger = agents_log.logger
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
# Note: VoicePipelineAgent and AgentTranscriptionOptions are not available in current livekit-agents version
# Transcription options may need to be configured differently

# Presidio Imports
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
import re

# Initialize Presidio Engines lazily (only when needed)
# This avoids proxy/network issues during import
_analyzer = None
_anonymizer = None

def get_analyzer():
    """Get or create Presidio analyzer engine with custom OTP recognizer."""
    global _analyzer
    if _analyzer is None:
        try:
            #Create base analyzer
            _analyzer = AnalyzerEngine()
            
            # Add custom OTP recognizer
            # Pattern 1: Numeric OTPs (4-8 digits, optionally with spaces/dashes)
            numeric_otp_pattern = r'\b\d{4,8}\b|\b\d{3,4}[-\s]\d{3,4}\b'
            
            # Pattern 2: Word-based OTPs (e.g., "one two three four five")
            # Match sequences of number words (3-8 words) - basic number words only
            otp_words = r'(?:one|two|three|four|five|six|seven|eight|nine|zero)'
            # Match 3-8 consecutive number words - this is the core OTP value pattern
            otp_value_only = rf'\b(?:{otp_words}\s+){{2,7}}{otp_words}\b'
            
            # Pattern 3: OTP with context - matches the full phrase but we'll extract just the value
            # This helps with context scoring but the actual match should be the value part
            otp_with_context_full = rf'\b(?:my|the|your)?(?:otp|code|pin|password|passcode|verification\s+code)\s+is\s+((?:{otp_words}\s+){{2,7}}{otp_words})\b'
            
            # Create recognizers for different patterns
            numeric_otp_recognizer = PatternRecognizer(
                supported_entity="OTP",
                patterns=[
                    Pattern(
                        name="numeric_otp",
                        regex=numeric_otp_pattern,
                        score=0.8
                    )
                ],
                context=["otp", "code", "pin", "password", "passcode", "verification code", "one-time password", "verification"]
            )
            
            # Primary recognizer for word-based OTP values
            # This matches just the number words sequence (e.g., "one two three four five")
            word_otp_recognizer = PatternRecognizer(
                supported_entity="OTP",
                patterns=[
                    Pattern(
                        name="otp_value_only",
                        regex=otp_value_only,
                        score=0.8
                    )
                ],
                context=["otp", "code", "pin", "password", "passcode", "verification code", "one-time password", "my", "the", "your", "is"],
                # Increase context score when OTP-related words are nearby
                supported_language="en"
            )
            
            # Add both recognizers
            _analyzer.registry.add_recognizer(numeric_otp_recognizer)
            _analyzer.registry.add_recognizer(word_otp_recognizer)
            
        except Exception as e:
            # If spaCy model is not found, provide helpful error
            import sys
            print(f"Error initializing Presidio Analyzer: {e}", file=sys.stderr)
            print("Please run: uv run python -m spacy download en_core_web_lg", file=sys.stderr)
            raise
    return _analyzer

def get_anonymizer():
    """Get or create Presidio anonymizer engine."""
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer

from datetime import datetime
import os

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

    def _sanitize_text(self, text: str) -> str:
        """Helper to run Presidio Analyzer and Anonymizer on text."""
        if not text or text.strip() == "":
            return text
            
        # 1. Analyze (Detect PII)
        # Include OTP and other sensitive entities
        analyzer = get_analyzer()
        results = analyzer.analyze(
            text=text, 
            entities=["OTP", "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "SSN", "IBAN_CODE", "US_DRIVER_LICENSE", "US_PASSPORT", "US_BANK_NUMBER"], 
            language='en'
        )
        
        # 2. Anonymize (Redact PII)
        # You can customize operators: "replace", "mask", "redact", "hash"
        anonymizer = get_anonymizer()
        anonymized_result = anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators={"DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"})}
        )
        
        if len(results) > 0:
            logger.info(f"🛡️ Guardrail triggered. Redacted {len(results)} entities.")
            
        return anonymized_result.text
    
    def llm_node(
        self, 
        chat_ctx: llm.ChatContext, 
        tools: list[llm.FunctionTool], 
        model_settings: ModelSettings
    ):
        """
        Intercepts User Input -> LLM.
        Sanitizes the chat context so the LLM never sees the raw PII.
        """
        # Iterate through the context and sanitize the latest user message
        # Note: ChatContext uses items property, not messages attribute
        items = chat_ctx.items
        if items:
            # Find the last ChatMessage item
            for item in reversed(items):
                # Check if it's a ChatMessage (has 'type' attribute that equals 'message')
                if hasattr(item, 'type') and item.type == 'message' and hasattr(item, 'role'):
                    if item.role == "user":
                        # Use text_content property to get all text content
                        original_text = item.text_content
                        if original_text:
                            sanitized_text = self._sanitize_text(original_text)
                            
                            # Update the message content (replace first text content item)
                            if isinstance(item.content, list) and len(item.content) > 0:
                                # Replace the first text content with sanitized version
                                for i, content in enumerate(item.content):
                                    if isinstance(content, str):
                                        item.content[i] = sanitized_text
                                        break
                            
                            if original_text != sanitized_text:
                                logger.info(f"Sanitized User Input: {original_text} -> {sanitized_text}")
                    break

        # Pass the sanitized context to the default LLM behavior
        return super().llm_node(chat_ctx, tools, model_settings)
    
    def tts_node(self, text: AsyncIterable[str], model_settings: ModelSettings):
        """
        Intercepts LLM Output -> TTS.
        Sanitizes the stream before the agent speaks it.
        """
        
        # We define a generator to wrap the incoming text stream
        async def safe_text_stream():
            async for chunk in text:
                # Note: Running Presidio on small chunks (tokens) is inaccurate.
                # Ideally, you should buffer by sentence. 
                # For this sample, we assume 'chunk' is substantial or we accept partial redaction risks.
                # LiveKit's LLM stream usually yields chunks; a buffer might be needed for production accuracy.
                sanitized_chunk = self._sanitize_text(chunk)
                yield sanitized_chunk

        # Pass the safe stream to the original TTS node logic
        return super().tts_node(safe_text_stream(), model_settings)
        
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
    session = AgentSession(
        stt="assemblyai/universal-streaming:en",
        llm="openai/gpt-4.1-mini",
        tts="cartesia/sonic-3:a167e0f3-df7e-4d52-a9c3-f949145efdab",  # Male voice
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    # Start the session
    await session.start(
        room=ctx.room,
        agent=Assistant()
    )

    # Generate initial greeting
    await session.generate_reply(
        instructions="Greet the user professionally as a banking assistant and ask for their customer ID to help with their banking needs."
    )

if __name__ == "__main__":
    # Run the agent
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))