-- Banking Database Schema
-- ========================
-- PostgreSQL schema for banking data (accounts, transactions, loans)

-- Accounts table
CREATE TABLE IF NOT EXISTS accounts (
    account_id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('checking', 'savings', 'credit_card')),
    account_number VARCHAR(50) NOT NULL UNIQUE,
    balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    credit_limit DECIMAL(15, 2) NULL,  -- Only for credit_card accounts
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_accounts_account_type ON accounts(account_type);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
    transaction_date DATE NOT NULL,
    description VARCHAR(255) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('debit', 'credit', 'transfer', 'payment')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_transaction UNIQUE (account_id, transaction_date, description, amount, transaction_type)
);

CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);

-- Loans table
CREATE TABLE IF NOT EXISTS loans (
    loan_id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    loan_type VARCHAR(50) NOT NULL,
    loan_account_number VARCHAR(50) NOT NULL UNIQUE,
    balance DECIMAL(15, 2) NOT NULL,
    interest_rate DECIMAL(5, 2) NOT NULL,
    monthly_payment DECIMAL(15, 2) NOT NULL,
    remaining_term_months INTEGER NULL,
    next_payment_date DATE NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_loans_user_id ON loans(user_id);
CREATE INDEX IF NOT EXISTS idx_loans_loan_type ON loans(loan_type);

-- Sample data (matching mock data structure)
-- User 12345 - John Doe
INSERT INTO accounts (user_id, account_type, account_number, balance, credit_limit) VALUES
    ('12345', 'checking', 'CHK-12345-001', 2547.83, NULL),
    ('12345', 'savings', 'SAV-12345-002', 15430.22, NULL),
    ('12345', 'credit_card', 'CC-12345-003', 1250.45, 5000.00)
ON CONFLICT (account_number) DO NOTHING;

INSERT INTO transactions (account_id, transaction_date, description, amount, transaction_type)
SELECT a.account_id, t.transaction_date, t.description, t.amount, t.transaction_type
FROM (VALUES
    -- Checking account transactions
    ('CHK-12345-001', '2025-11-05'::DATE, 'Grocery Store', -87.32, 'debit'),
    ('CHK-12345-001', '2025-11-04'::DATE, 'Salary Deposit', 3200.00, 'credit'),
    ('CHK-12345-001', '2025-11-03'::DATE, 'Gas Station', -45.67, 'debit'),
    ('CHK-12345-001', '2025-11-02'::DATE, 'Online Transfer', -500.00, 'transfer'),
    ('CHK-12345-001', '2025-11-01'::DATE, 'Coffee Shop', -12.95, 'debit'),
    -- Savings account transactions
    ('SAV-12345-002', '2025-11-05'::DATE, 'Interest Payment', 25.50, 'credit'),
    ('SAV-12345-002', '2025-11-01'::DATE, 'Monthly Deposit', 500.00, 'credit'),
    ('SAV-12345-002', '2025-10-28'::DATE, 'Transfer to Checking', -200.00, 'transfer')
) AS t(account_number, transaction_date, description, amount, transaction_type)
INNER JOIN accounts a ON a.account_number = t.account_number
ON CONFLICT DO NOTHING;

INSERT INTO loans (user_id, loan_type, loan_account_number, balance, interest_rate, monthly_payment, remaining_term_months, next_payment_date) VALUES
    ('12345', 'Mortgage', 'LOAN-12345-001', 285000.00, 3.75, 1820.50, 312, '2025-12-01'),
    ('12345', 'Auto Loan', 'LOAN-12345-002', 18500.00, 4.25, 435.20, 48, '2025-12-15')
ON CONFLICT (loan_account_number) DO NOTHING;

-- User 67890 - Jane Smith
INSERT INTO accounts (user_id, account_type, account_number, balance, credit_limit) VALUES
    ('67890', 'checking', 'CHK-67890-001', 3821.67, NULL),
    ('67890', 'savings', 'SAV-67890-002', 25678.90, NULL),
    ('67890', 'credit_card', 'CC-67890-003', 2100.30, 8000.00)
ON CONFLICT (account_number) DO NOTHING;

INSERT INTO transactions (account_id, transaction_date, description, amount, transaction_type)
SELECT a.account_id, t.transaction_date, t.description, t.amount, t.transaction_type
FROM (VALUES
    -- Checking account transactions
    ('CHK-67890-001', '2025-11-05'::DATE, 'Rent Payment', -1800.00, 'debit'),
    ('CHK-67890-001', '2025-11-04'::DATE, 'Freelance Payment', 1250.00, 'credit'),
    ('CHK-67890-001', '2025-11-03'::DATE, 'Utility Bill', -125.40, 'debit'),
    ('CHK-67890-001', '2025-11-02'::DATE, 'Investment Deposit', -1000.00, 'transfer'),
    ('CHK-67890-001', '2025-11-01'::DATE, 'Restaurant', -85.60, 'debit'),
    -- Savings account transactions
    ('SAV-67890-002', '2025-11-05'::DATE, 'Interest Payment', 42.30, 'credit'),
    ('SAV-67890-002', '2025-11-01'::DATE, 'Monthly Deposit', 1000.00, 'credit'),
    ('SAV-67890-002', '2025-10-25'::DATE, 'Transfer to Checking', -500.00, 'transfer')
) AS t(account_number, transaction_date, description, amount, transaction_type)
INNER JOIN accounts a ON a.account_number = t.account_number
ON CONFLICT DO NOTHING;

INSERT INTO loans (user_id, loan_type, loan_account_number, balance, interest_rate, monthly_payment, remaining_term_months, next_payment_date) VALUES
    ('67890', 'Personal Loan', 'LOAN-67890-001', 8500.00, 6.50, 275.80, 36, '2025-12-10')
ON CONFLICT (loan_account_number) DO NOTHING;

