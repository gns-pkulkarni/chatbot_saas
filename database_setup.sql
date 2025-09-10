-- Create users table for authentication
CREATE TABLE IF NOT EXISTS saas_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create client profiles table
CREATE TABLE IF NOT EXISTS saas_client_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES saas_users(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create plans table
CREATE TABLE IF NOT EXISTS saas_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) DEFAULT 0,
    description TEXT,
    max_messages INTEGER DEFAULT 100,
    max_sites INTEGER DEFAULT 1,
    max_documents INTEGER DEFAULT 5,
    can_upload_docs BOOLEAN DEFAULT FALSE,
    can_use_voice BOOLEAN DEFAULT FALSE,
    branding_removed BOOLEAN DEFAULT FALSE,
    chat_history_days INTEGER DEFAULT 7,
    api_access BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert default plans
-- Note: -1 in max_sites and max_documents means unlimited
-- Prices are in DOLLARS (stored as decimal, not cents)
INSERT INTO saas_plans (name, price, description, max_messages, max_sites, max_documents, can_upload_docs, can_use_voice, branding_removed, chat_history_days, api_access)
VALUES 
    ('Freemium', 0, 'Perfect for trying out our service', 100, 1, 0, FALSE, FALSE, FALSE, 7, FALSE),
    ('Starter', 10, 'Basic chatbot with 1 website', -1, 1, 0, FALSE, FALSE, FALSE, 30, FALSE),      -- $10 - 1 website, text only
    ('Pro', 20, 'Enhanced with document support', -1, 1, 10, TRUE, FALSE, TRUE, 90, FALSE),          -- $20 - 1 website + 10 documents
    ('Ultimate', 30, 'Full features with voice', -1, -1, 25, TRUE, TRUE, TRUE, 365, TRUE)           -- $30 - Unlimited websites + 25 docs + voice
ON CONFLICT DO NOTHING;

-- Create subscriptions table
CREATE TABLE IF NOT EXISTS saas_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES saas_client_profiles(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES saas_plans(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create knowledge base table (replaces websites table)
CREATE TABLE IF NOT EXISTS saas_knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES saas_users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('url', 'document')),
    source_url TEXT,
    document_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Enable vector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Create knowledge base vectors table
CREATE TABLE IF NOT EXISTS saas_knowledge_base_vectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_base_id UUID REFERENCES saas_knowledge_base(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index on embeddings for faster similarity search
CREATE INDEX IF NOT EXISTS saas_knowledge_base_vectors_embedding_idx 
ON saas_knowledge_base_vectors 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create chat history table
CREATE TABLE IF NOT EXISTS saas_chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES saas_users(id) ON DELETE CASCADE,
    knowledge_base_id UUID REFERENCES saas_knowledge_base(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_cost_usd NUMERIC(10, 6)
);

-- Create the match function for vector similarity search
CREATE OR REPLACE FUNCTION match_saas_knowledge_base_vectors(
    query_embedding vector(1536),
    filter jsonb DEFAULT '{}',
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    metadata JSONB,
    similarity float
)
LANGUAGE plpgsql
AS $$
begin
    return query
    select
        saas_knowledge_base_vectors.id,
        saas_knowledge_base_vectors.content,
        saas_knowledge_base_vectors.metadata,
        1 - (saas_knowledge_base_vectors.embedding <=> query_embedding) as similarity
    from saas_knowledge_base_vectors
    where saas_knowledge_base_vectors.metadata @> filter
    order by saas_knowledge_base_vectors.embedding <=> query_embedding
    limit match_count;
end;
$$;

-- ================================================
-- STRIPE INTEGRATION TABLES AND MODIFICATIONS
-- ================================================

-- Modifications to existing tables for Stripe integration
ALTER TABLE saas_client_profiles ADD COLUMN IF NOT EXISTS 
    stripe_customer_id VARCHAR(255) UNIQUE;
ALTER TABLE saas_client_profiles ADD COLUMN IF NOT EXISTS 
    preferred_currency VARCHAR(3) DEFAULT 'USD';

ALTER TABLE saas_subscriptions ADD COLUMN IF NOT EXISTS 
    stripe_subscription_id VARCHAR(255) UNIQUE;
ALTER TABLE saas_subscriptions ADD COLUMN IF NOT EXISTS 
    stripe_price_id VARCHAR(255);
ALTER TABLE saas_subscriptions ADD COLUMN IF NOT EXISTS 
    stripe_checkout_session_id VARCHAR(255);
ALTER TABLE saas_subscriptions ADD COLUMN IF NOT EXISTS 
    payment_status VARCHAR(50) DEFAULT 'pending';
ALTER TABLE saas_subscriptions ADD COLUMN IF NOT EXISTS 
    amount DECIMAL(10, 2) DEFAULT 0;
ALTER TABLE saas_subscriptions ADD COLUMN IF NOT EXISTS 
    currency VARCHAR(3) DEFAULT 'USD';

ALTER TABLE saas_plans ADD COLUMN IF NOT EXISTS 
    stripe_price_id VARCHAR(255);

-- Stripe webhook events table
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

-- Payment history table
CREATE TABLE IF NOT EXISTS saas_payment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES saas_client_profiles(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES saas_subscriptions(id),
    stripe_payment_intent_id VARCHAR(255),
    stripe_invoice_id VARCHAR(255),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status VARCHAR(50) NOT NULL,
    payment_method VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_history_client_id ON saas_payment_history(client_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_subscription_id ON saas_payment_history(subscription_id);
CREATE INDEX IF NOT EXISTS idx_payment_history_created_at ON saas_payment_history(created_at);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_saas_users_email ON saas_users(email);
CREATE INDEX IF NOT EXISTS idx_saas_knowledge_base_user_id ON saas_knowledge_base(user_id);
CREATE INDEX IF NOT EXISTS idx_saas_knowledge_base_vectors_kb_id ON saas_knowledge_base_vectors(knowledge_base_id);
CREATE INDEX IF NOT EXISTS idx_saas_chat_history_user_id ON saas_chat_history(user_id);

-- Add updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
CREATE TRIGGER update_saas_users_updated_at BEFORE UPDATE ON saas_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_saas_client_profiles_updated_at BEFORE UPDATE ON saas_client_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_saas_subscriptions_updated_at BEFORE UPDATE ON saas_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_saas_knowledge_base_updated_at BEFORE UPDATE ON saas_knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
