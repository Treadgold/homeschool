# Payment System Setup Guide

This guide explains how to set up the payment system for both development and production environments.

## Development Setup

### 1. **Mock Payments (No Stripe Account Required)**

For initial development without Stripe integration:

```bash
# In your .env file
ENVIRONMENT=development
ENABLE_PAYMENTS=false
STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
```

This will use the `MockPaymentService` which simulates payment flows without requiring Stripe keys.

### 2. **Stripe Test Mode (Recommended for Development)**

1. Create a free Stripe account at https://stripe.com
2. Navigate to the Stripe Dashboard
3. Ensure you're in "Test Mode" (toggle in the left sidebar)
4. Get your test API keys from "Developers" > "API keys"

```bash
# In your .env file
ENVIRONMENT=development
ENABLE_PAYMENTS=true
STRIPE_PUBLISHABLE_KEY=pk_test_51234567890...
STRIPE_SECRET_KEY=sk_test_51234567890...
STRIPE_WEBHOOK_SECRET=whsec_1234567890...
STRIPE_CURRENCY=nzd
SITE_URL=http://localhost:8000
```

### 3. **Test Credit Cards**

Use these test credit card numbers in development:

- **Successful payment**: 4242 4242 4242 4242
- **Payment requires authentication**: 4000 0025 0000 3155
- **Payment is declined**: 4000 0000 0000 0002
- **Insufficient funds**: 4000 0000 0000 9995

Use any future expiry date, any 3-digit CVC, and any postal code.

### 4. **Webhook Testing in Development**

For local webhook testing, use ngrok or similar:

```bash
# Install ngrok
npm install -g ngrok

# Expose your local server
ngrok http 8000

# Use the HTTPS URL for webhook endpoint in Stripe Dashboard
# Example: https://abc123.ngrok.io/webhook/stripe
```

## Production Setup

### 1. **Stripe Live Mode**

1. Complete Stripe account verification
2. Switch to "Live Mode" in Stripe Dashboard
3. Get your live API keys
4. **CRITICAL**: Never use test keys in production!

```bash
# In your production .env file
ENVIRONMENT=production
ENABLE_PAYMENTS=true
STRIPE_PUBLISHABLE_KEY=pk_live_51234567890...
STRIPE_SECRET_KEY=sk_live_51234567890...
STRIPE_WEBHOOK_SECRET=whsec_1234567890...
STRIPE_CURRENCY=nzd
SITE_URL=https://yourdomain.com
```

### 2. **Webhook Configuration**

1. In Stripe Dashboard > "Developers" > "Webhooks"
2. Add endpoint: `https://yourdomain.com/webhook/stripe`
3. Select events to send:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `checkout.session.completed`
4. Copy the webhook secret to your environment variables

### 3. **Security Checklist**

- [ ] Use HTTPS for all payment-related pages
- [ ] Validate webhook signatures
- [ ] Store sensitive keys as environment variables
- [ ] Implement proper error logging
- [ ] Set up monitoring for failed payments
- [ ] Test refund functionality
- [ ] Verify tax handling (if applicable)

## Testing the Payment Flow

### 1. **Development Testing**

```bash
# Start your application
uvicorn app.main:app --reload

# Test booking flow:
# 1. Create an account
# 2. Add children to your profile
# 3. Book a paid event
# 4. Complete payment (will redirect to Stripe Checkout in test mode)
# 5. Verify booking status in admin panel
```

### 2. **Payment Status Checking**

The system tracks these payment statuses:
- `unpaid` - No payment required or not yet processed
- `pending` - Payment initiated, awaiting confirmation
- `paid` - Payment successful
- `failed` - Payment failed
- `refunded` - Payment refunded

### 3. **Admin Functions**

Access `/admin/payments` to:
- View all payment transactions
- Process refunds
- Export financial reports
- Monitor payment statistics

Access `/admin/stripe` to:
- Check Stripe connection status
- View webhook logs
- Configure payment settings
- Monitor account balance

## Configuration Options

### Environment Variables

| Variable | Description | Development | Production |
|----------|-------------|-------------|------------|
| `ENVIRONMENT` | App environment | `development` | `production` |
| `ENABLE_PAYMENTS` | Enable payment processing | `true`/`false` | `true` |
| `STRIPE_PUBLISHABLE_KEY` | Stripe public key | `pk_test_...` | `pk_live_...` |
| `STRIPE_SECRET_KEY` | Stripe secret key | `sk_test_...` | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | Webhook verification | `whsec_...` | `whsec_...` |
| `STRIPE_CURRENCY` | Payment currency | `nzd` | `nzd` |
| `SITE_URL` | Your domain | `http://localhost:8000` | `https://yourdomain.com` |

### Payment Flow Types

The system supports two Stripe integration patterns:

1. **Stripe Checkout** (Current implementation)
   - Hosted payment page
   - Easier to implement
   - Built-in payment methods
   - Automatic tax calculation

2. **Payment Intents + Elements** (Future enhancement)
   - Custom payment forms
   - More control over UX
   - Requires more frontend code

## Common Issues and Solutions

### Issue: "Invalid API Key"
**Solution**: Check that you're using the correct key for your environment (test vs live)

### Issue: "Webhook signature verification failed"
**Solution**: Ensure webhook secret matches the one from Stripe Dashboard

### Issue: "Payment succeeded but booking still pending"
**Solution**: Check webhook delivery in Stripe Dashboard, verify endpoint URL

### Issue: "Payments work in development but not production"
**Solution**: Verify you're using live keys and HTTPS URLs in production

## Migration Strategy

To gradually roll out payments:

1. **Phase 1**: Deploy with `ENABLE_PAYMENTS=false` (mock mode)
2. **Phase 2**: Enable Stripe test mode for admin testing
3. **Phase 3**: Switch to live mode for production payments

This allows you to test the complete flow before processing real payments.

## Monitoring and Maintenance

### Key Metrics to Monitor
- Payment success rate
- Average transaction value
- Refund rate
- Webhook delivery success
- Payment method distribution

### Regular Tasks
- Monitor Stripe Dashboard for disputes
- Review failed payment reasons
- Update webhook endpoints if URLs change
- Backup payment transaction logs
- Test payment flow after deployments

## Support and Documentation

- [Stripe Documentation](https://stripe.com/docs)
- [Stripe Test Data](https://stripe.com/docs/testing)
- [Webhook Testing](https://stripe.com/docs/webhooks/test)
- [Payment Methods](https://stripe.com/docs/payments/payment-methods) 