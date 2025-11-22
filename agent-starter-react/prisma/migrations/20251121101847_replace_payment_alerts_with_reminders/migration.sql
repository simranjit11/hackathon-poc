-- DropTable
DROP TABLE IF EXISTS "payment_alerts";

-- CreateTable
CREATE TABLE "payment_reminders" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "scheduled_date" TIMESTAMP(3) NOT NULL,
    "amount" DECIMAL(15,2) NOT NULL,
    "recipient" TEXT NOT NULL,
    "description" TEXT,
    "beneficiary_id" TEXT,
    "account_id" TEXT NOT NULL,
    "is_completed" BOOLEAN NOT NULL DEFAULT false,
    "reminder_notification_settings" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "payment_reminders_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "payment_reminders_user_id_idx" ON "payment_reminders"("user_id");

-- CreateIndex
CREATE INDEX "payment_reminders_account_id_idx" ON "payment_reminders"("account_id");

-- CreateIndex
CREATE INDEX "payment_reminders_beneficiary_id_idx" ON "payment_reminders"("beneficiary_id");

-- CreateIndex
CREATE INDEX "payment_reminders_scheduled_date_idx" ON "payment_reminders"("scheduled_date");

-- CreateIndex
CREATE INDEX "payment_reminders_is_completed_idx" ON "payment_reminders"("is_completed");

-- AddForeignKey
ALTER TABLE "payment_reminders" ADD CONSTRAINT "payment_reminders_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payment_reminders" ADD CONSTRAINT "payment_reminders_account_id_fkey" FOREIGN KEY ("account_id") REFERENCES "accounts"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payment_reminders" ADD CONSTRAINT "payment_reminders_beneficiary_id_fkey" FOREIGN KEY ("beneficiary_id") REFERENCES "beneficiaries"("id") ON DELETE SET NULL ON UPDATE CASCADE;

