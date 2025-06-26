import stripe
from typing import Dict, Any, Optional, List
from app.config import config
from app.models import Event, Booking, User, Child
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self):
        stripe.api_key = config.STRIPE_SECRET_KEY
        self.currency = config.STRIPE_CURRENCY
        
    def create_payment_intent(
        self, 
        amount_cents: int, 
        booking_details: Dict[str, Any],
        customer_email: str
    ) -> Dict[str, Any]:
        """Create a Stripe PaymentIntent for the given amount and booking details"""
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=self.currency,
                automatic_payment_methods={'enabled': True},
                metadata={
                    'booking_type': 'event_booking',
                    'user_email': customer_email,
                    'event_id': str(booking_details.get('event_id', '')),
                    'child_count': str(booking_details.get('child_count', 0)),
                    'environment': config.ENVIRONMENT
                },
                description=f"Event booking: {booking_details.get('event_title', 'Unknown Event')}"
            )
            
            return {
                'success': True,
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
                'amount': intent.amount,
                'currency': intent.currency
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe PaymentIntent creation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def create_checkout_session(
        self,
        amount_cents: int,
        booking_details: Dict[str, Any],
        customer_email: str,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout Session (alternative to PaymentIntent)"""
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': self.currency,
                        'product_data': {
                            'name': booking_details.get('event_title', 'Event Booking'),
                            'description': f"Booking for {booking_details.get('child_count', 1)} child(ren)"
                        },
                        'unit_amount': amount_cents,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata={
                    'booking_type': 'event_booking',
                    'user_email': customer_email,
                    'event_id': str(booking_details.get('event_id', '')),
                    'child_count': str(booking_details.get('child_count', 0)),
                    'environment': config.ENVIRONMENT
                }
            )
            
            return {
                'success': True,
                'checkout_url': session.url,
                'session_id': session.id
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Checkout Session creation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def confirm_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """Confirm and retrieve payment details"""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                'success': True,
                'status': intent.status,
                'amount_received': intent.amount_received,
                'metadata': intent.metadata
            }
        except stripe.error.StripeError as e:
            logger.error(f"Payment confirmation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_refund(self, payment_intent_id: str, amount_cents: Optional[int] = None) -> Dict[str, Any]:
        """Create a refund for a payment"""
        try:
            refund_data = {'payment_intent': payment_intent_id}
            if amount_cents:
                refund_data['amount'] = amount_cents
                
            refund = stripe.Refund.create(**refund_data)
            
            return {
                'success': True,
                'refund_id': refund.id,
                'amount': refund.amount,
                'status': refund.status
            }
        except stripe.error.StripeError as e:
            logger.error(f"Refund creation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def handle_webhook_event(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Handle Stripe webhook events"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, config.STRIPE_WEBHOOK_SECRET
            )
            
            return {
                'success': True,
                'event_type': event['type'],
                'event_id': event['id'],
                'data': event['data']
            }
        except ValueError:
            return {'success': False, 'error': 'Invalid payload'}
        except stripe.error.SignatureVerificationError:
            return {'success': False, 'error': 'Invalid signature'}
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get Stripe account connection status"""
        try:
            # Test the connection by making a simple API call
            account = stripe.Account.retrieve()
            
            return {
                'connected': True,
                'test_mode': config.stripe_is_test_mode,
                'account_id': account.id,
                'business_profile': account.get('business_profile', {}),
                'charges_enabled': account.charges_enabled,
                'payouts_enabled': account.payouts_enabled
            }
        except stripe.error.StripeError as e:
            return {
                'connected': False,
                'error': str(e),
                'test_mode': config.stripe_is_test_mode
            }

# Mock payment service for development when Stripe is not configured
class MockPaymentService:
    """Mock payment service for development without Stripe keys"""
    
    def create_payment_intent(self, amount_cents: int, booking_details: Dict[str, Any], customer_email: str) -> Dict[str, Any]:
        return {
            'success': True,
            'client_secret': 'pi_mock_client_secret',
            'payment_intent_id': 'pi_mock_payment_intent',
            'amount': amount_cents,
            'currency': 'nzd'
        }
    
    def create_checkout_session(self, amount_cents: int, booking_details: Dict[str, Any], customer_email: str, success_url: str, cancel_url: str) -> Dict[str, Any]:
        # In development, redirect directly to success page
        return {
            'success': True,
            'checkout_url': success_url + '?mock=true',
            'session_id': 'cs_mock_session'
        }
    
    def confirm_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        return {
            'success': True,
            'status': 'succeeded',
            'amount_received': 1000,  # Mock amount
            'metadata': {}
        }
    
    def create_refund(self, payment_intent_id: str, amount_cents: Optional[int] = None) -> Dict[str, Any]:
        return {
            'success': True,
            'refund_id': 're_mock_refund',
            'amount': amount_cents or 1000,
            'status': 'succeeded'
        }
    
    def handle_webhook_event(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        return {
            'success': True,
            'event_type': 'payment_intent.succeeded',
            'event_id': 'evt_mock',
            'data': {}
        }
    
    def get_connection_status(self) -> Dict[str, Any]:
        return {
            'connected': True,
            'test_mode': True,
            'account_id': 'acct_mock',
            'business_profile': {'name': 'Mock Account'},
            'charges_enabled': True,
            'payouts_enabled': True,
            'mock_mode': True
        }

def get_payment_service() -> PaymentService:
    """Factory function to get the appropriate payment service"""
    if config.STRIPE_SECRET_KEY and config.ENABLE_PAYMENTS:
        return PaymentService()
    else:
        logger.info("Using mock payment service (Stripe not configured)")
        return MockPaymentService() 