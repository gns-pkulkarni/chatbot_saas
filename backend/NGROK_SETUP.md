# Ngrok and Stripe Webhook Setup

## Every time you start ngrok:

1. **Start your backend server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

2. **Start ngrok:**
   ```bash
   ngrok http 8000
   ```

3. **Update your .env file:**
   Update the `FRONTEND_URL` with your ngrok URL:
   ```
   FRONTEND_URL=https://your-ngrok-url.ngrok-free.app
   ```
   Example:
   ```
   FRONTEND_URL=https://83717d1636e3.ngrok-free.app
   ```

4. **Update Stripe Webhook Endpoint (if URL changed):**
   - Go to Stripe Dashboard > Developers > Webhooks
   - Update your webhook endpoint to:
     ```
     https://your-ngrok-url.ngrok-free.app/payments/stripe-webhook
     ```

## Important Notes:

- The `FRONTEND_URL` in .env determines where users are redirected after successful payment
- The webhook endpoint handles the actual subscription activation
- If you see "Not Found" after payment, check that FRONTEND_URL matches your ngrok URL
- The ngrok warning page appears when accessing the webhook URL directly (this is normal)

## Webhook Events to Listen For:
- `checkout.session.completed` - Main event for subscription activation
- `customer.subscription.updated` - For subscription changes
- `customer.subscription.deleted` - For cancellations
- `invoice.payment_succeeded` - For renewal payments

## Testing Payments:
Use Stripe test card numbers:
- Success: 4242 4242 4242 4242
- Decline: 4000 0000 0000 0002
- Requires authentication: 4000 0025 0000 3155
