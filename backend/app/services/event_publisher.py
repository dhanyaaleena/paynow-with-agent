import json
import asyncio
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class EventPublisher:
    """Simulates Kafka event publishing by outputting to stdout"""
    
    def __init__(self):
        self.event_count = 0
    
    async def publish_payment_decided(
        self,
        payment_id: int,
        customer_id: str,
        payee_id: str,
        amount: float,
        currency: str,
        decision: str,
        reasons: list,
        request_id: str,
        agent_trace: list,
        user_display: list
    ) -> bool:
        """
        Publish a payment.decided event
        Returns bool: True if event was published successfully
        """
        try:
            event = {
                "event_type": "payment.decided",
                "event_id": f"evt_{self.event_count:08d}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "payment_id": payment_id,
                    "customer_id": customer_id,
                    "payee_id": payee_id,
                    "amount": amount,
                    "currency": currency,
                    "decision": decision,
                    "reasons": reasons,
                    "request_id": request_id,
                    "agent_trace": agent_trace,
                    "user_display": user_display
                },
                "metadata": {
                    "source": "paynow-api",
                    "version": "1.0"
                }
            }
            
            # Simulate async publishing delay
            await asyncio.sleep(0.001)  # 1ms delay
            
            # Output to stdout (simulating Kafka)
            print(f"[EVENT] {json.dumps(event, indent=2)}")
            
            self.event_count += 1
            logger.info(f"Published payment.decided event {event['event_id']} for payment {payment_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish payment.decided event: {e}")
            return False
    
    async def publish_payment_failed(
        self,
        customer_id: str,
        payee_id: str,
        amount: float,
        currency: str,
        error: str,
        request_id: str
    ) -> bool:
        """
        Publish a payment.failed event for failed payments
        Returns bool: True if event was published successfully
        """
        try:
            event = {
                "event_type": "payment.failed",
                "event_id": f"evt_{self.event_count:08d}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "customer_id": customer_id,
                    "payee_id": payee_id,
                    "amount": amount,
                    "currency": currency,
                    "error": error,
                    "request_id": request_id
                },
                "metadata": {
                    "source": "paynow-api",
                    "version": "1.0"
                }
            }
            
            await asyncio.sleep(0.001)
            print(f"[EVENT] {json.dumps(event, indent=2)}")
            
            self.event_count += 1
            logger.info(f"Published payment.failed event {event['event_id']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish payment.failed event: {e}")
            return False

event_publisher = EventPublisher()
