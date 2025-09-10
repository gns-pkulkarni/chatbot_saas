-- Stripe Integration Database Schema Changes
-- Execute this after backing up your database

-- ================================================
-- MODIFICATIONS TO EXISTING TABLES
-- ================================================

-- 1. Update saas_client_profiles table
ALTER TABLE saas_client_profiles ADD COLUMN IF NOT EXISTS 
    stripe_customer_id VARCHAR(255) UNIQUE;
ALTER TABLE saas_client_profiles ADD COLUMN IF NOT EXISTS 
    preferred_currency VARCHAR(3) DEFAULT 'USD';

-- 2. Update saas_subscriptions table
ALTER TABLE saas_subscriptions ADD COLUMN IF NOT EXISTS 
    stripe_subscription_id VARCHAR(255) UNIQUE;
ALTER TABLE saas_subscriptions ADD COLUMN IF NOT EXISTS 
    stripe_price_id VARCHAR(255);
ALTER TABLE saas_subscriptions ADD COLUMN IF NOT EXISTS 
    stripe_checkout_session_id VARCHAR(255);
ALTER TABLE saas_subscriptions ADD COLUMN IF NOT EXISTS 
    payment_status VARCHAR(50) DEFAULT 'pending'; -- 'pending', 'paid', 'failed'
ALTER TABLE saas_subscriptions ADD COLUMN IF NOT EXISTS 
    amount DECIMAL(10, 2) DEFAULT 0;
ALTER TABLE saas_subscriptions ADD COLUMN IF NOT EXISTS 
    currency VARCHAR(3) DEFAULT 'USD';

-- 3. Update saas_plans table with Stripe price IDs
ALTER TABLE saas_plans ADD COLUMN IF NOT EXISTS 
    stripe_price_id VARCHAR(255);

-- Update the plans with your Stripe price IDs
UPDATE saas_plans SET stripe_price_id = NULL WHERE name = 'Freemium';
UPDATE saas_plans SET stripe_price_id = 'price_1Ruw3SLhal1XdhwmSCYu7T9x' WHERE name = 'Starter';
UPDATE saas_plans SET stripe_price_id = 'price_1Ruw3zLhal1Xdhwm2bcwrHhQ' WHERE name = 'Pro';
UPDATE saas_plans SET stripe_price_id = 'price_1Ruw4ZLhal1XdhwmDpucVr7v' WHERE name = 'Ultimate';

-- ================================================
-- NEW TABLES (Simplified for MVP)
-- ================================================

-- 1. Stripe Webhook Events (for reliability and debugging)
CREATE TABLE IF NOT EXISTS saas_stripe_webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stripe_event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stripe_webhooks_event_id ON saas_stripe_webhooks(stripe_event_id);
CREATE INDEX IF NOT EXISTS idx_stripe_webhooks_processed ON saas_stripe_webhooks(processed);

-- 2. Payment History (simplified transactions table)
CREATE TABLE IF NOT EXISTS saas_payment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES saas_client_profiles(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES saas_subscriptions(id),
    stripe_payment_intent_id VARCHAR(255),
    stripe_invoice_id VARCHAR(255),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'succeeded', 'failed', 'refunded'
    payment_method VARCHAR(100), -- 'card', 'upi', 'wallet', etc.
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_history_client_id ON saas_payment_history(client_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_subscription_id ON saas_payment_history(subscription_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_created_at ON saas_payment_history(created_at);

-- ================================================
-- HELPER FUNCTIONS
-- ================================================

-- Function to handle Freemium subscription creation
CREATE OR REPLACE FUNCTION create_freemium_subscription(
    p_client_id UUID,
    p_plan_id UUID
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    v_subscription_id UUID;
BEGIN
    -- Create a subscription for freemium plan (15 days)
    INSERT INTO saas_subscriptions (
        client_id,
        plan_id,
        start_date,
        end_date,
        status,
        payment_status,
        amount,
        currency
    ) VALUES (
        p_client_id,
        p_plan_id,
        CURRENT_DATE,
        CURRENT_DATE + INTERVAL '15 days',
        'active',
        'paid',
        0,
        'USD'
    ) RETURNING id INTO v_subscription_id;
    
    RETURN v_subscription_id;
END;
$$;
