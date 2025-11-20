-- CreateTable
CREATE TABLE "accounts" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "account_number" TEXT NOT NULL,
    "account_type" TEXT NOT NULL,
    "balance" DECIMAL(15,2) NOT NULL,
    "credit_limit" DECIMAL(15,2),
    "currency" TEXT NOT NULL DEFAULT 'USD',
    "status" TEXT NOT NULL DEFAULT 'active',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "accounts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "loans" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "account_id" TEXT,
    "loan_type" TEXT NOT NULL,
    "loan_number" TEXT NOT NULL,
    "outstanding_balance" DECIMAL(15,2) NOT NULL,
    "interest_rate" DECIMAL(5,4) NOT NULL,
    "monthly_payment" DECIMAL(15,2) NOT NULL,
    "remaining_term_months" INTEGER NOT NULL,
    "next_payment_date" TIMESTAMP(3) NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "loans_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "transactions" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "account_id" TEXT NOT NULL,
    "transaction_type" TEXT NOT NULL,
    "amount" DECIMAL(15,2) NOT NULL,
    "currency" TEXT NOT NULL DEFAULT 'USD',
    "from_account" TEXT,
    "to_account" TEXT,
    "beneficiary_id" TEXT,
    "description" TEXT,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "reference_number" TEXT,
    "payment_session_id" TEXT,
    "expires_at" TIMESTAMP(3),
    "completed_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "transactions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "payment_alerts" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "alert_type" TEXT NOT NULL,
    "threshold" DECIMAL(15,2),
    "account_id" TEXT,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "payment_alerts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "notification_preferences" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "channel" TEXT NOT NULL,
    "event_type" TEXT NOT NULL,
    "is_enabled" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "notification_preferences_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "accounts_account_number_key" ON "accounts"("account_number");

-- CreateIndex
CREATE INDEX "accounts_user_id_idx" ON "accounts"("user_id");

-- CreateIndex
CREATE INDEX "accounts_account_type_idx" ON "accounts"("account_type");

-- CreateIndex
CREATE INDEX "accounts_status_idx" ON "accounts"("status");

-- CreateIndex
CREATE UNIQUE INDEX "loans_loan_number_key" ON "loans"("loan_number");

-- CreateIndex
CREATE INDEX "loans_user_id_idx" ON "loans"("user_id");

-- CreateIndex
CREATE INDEX "loans_loan_type_idx" ON "loans"("loan_type");

-- CreateIndex
CREATE UNIQUE INDEX "transactions_reference_number_key" ON "transactions"("reference_number");

-- CreateIndex
CREATE UNIQUE INDEX "transactions_payment_session_id_key" ON "transactions"("payment_session_id");

-- CreateIndex
CREATE INDEX "transactions_user_id_idx" ON "transactions"("user_id");

-- CreateIndex
CREATE INDEX "transactions_account_id_idx" ON "transactions"("account_id");

-- CreateIndex
CREATE INDEX "transactions_beneficiary_id_idx" ON "transactions"("beneficiary_id");

-- CreateIndex
CREATE INDEX "transactions_transaction_type_idx" ON "transactions"("transaction_type");

-- CreateIndex
CREATE INDEX "transactions_status_idx" ON "transactions"("status");

-- CreateIndex
CREATE INDEX "transactions_payment_session_id_idx" ON "transactions"("payment_session_id");

-- CreateIndex
CREATE INDEX "transactions_created_at_idx" ON "transactions"("created_at");

-- CreateIndex
CREATE INDEX "payment_alerts_user_id_idx" ON "payment_alerts"("user_id");

-- CreateIndex
CREATE INDEX "payment_alerts_alert_type_idx" ON "payment_alerts"("alert_type");

-- CreateIndex
CREATE INDEX "payment_alerts_is_active_idx" ON "payment_alerts"("is_active");

-- CreateIndex
CREATE INDEX "notification_preferences_user_id_idx" ON "notification_preferences"("user_id");

-- CreateIndex
CREATE INDEX "notification_preferences_is_enabled_idx" ON "notification_preferences"("is_enabled");

-- CreateIndex
CREATE UNIQUE INDEX "notification_preferences_user_id_channel_event_type_key" ON "notification_preferences"("user_id", "channel", "event_type");

-- AddForeignKey
ALTER TABLE "accounts" ADD CONSTRAINT "accounts_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "loans" ADD CONSTRAINT "loans_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "loans" ADD CONSTRAINT "loans_account_id_fkey" FOREIGN KEY ("account_id") REFERENCES "accounts"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "transactions" ADD CONSTRAINT "transactions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "transactions" ADD CONSTRAINT "transactions_account_id_fkey" FOREIGN KEY ("account_id") REFERENCES "accounts"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "transactions" ADD CONSTRAINT "transactions_beneficiary_id_fkey" FOREIGN KEY ("beneficiary_id") REFERENCES "beneficiaries"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payment_alerts" ADD CONSTRAINT "payment_alerts_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "notification_preferences" ADD CONSTRAINT "notification_preferences_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
