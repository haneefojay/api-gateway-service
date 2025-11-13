"""
RabbitMQ Publisher for API Gateway
Handles message publishing to notification queues
"""

import aio_pika
import json
import logging
import ssl
from typing import Dict, Any
from app.config import settings, get_rabbitmq_url

logger = logging.getLogger(__name__)

class RabbitMQPublisher:
    """RabbitMQ message publisher"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
    
    async def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            # Wait for the broker TCP port to be ready to avoid race conditions
            await self._wait_for_broker()

            # For CloudAMQP with AMQPS (port 5671), we need to use amqps:// URL scheme
            # and provide SSL context
            url = get_rabbitmq_url()
            
            # Replace amqp:// with amqps:// for SSL connections on port 5671
            if settings.RABBITMQ_PORT == 5671:
                url = url.replace("amqp://", "amqps://")
                
                # Create SSL context for AMQPS
                ssl_context = ssl.create_default_context()
                # For CloudAMQP, we need to be more lenient with SSL verification
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                self.connection = await aio_pika.connect_robust(
                    url,
                    timeout=10,
                    ssl_context=ssl_context
                )
            else:
                # Plain AMQP for port 5672
                self.connection = await aio_pika.connect_robust(
                    url,
                    timeout=10
                )
            
            # Create channel
            self.channel = await self.connection.channel()
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                settings.RABBITMQ_EXCHANGE,
                type=aio_pika.ExchangeType.DIRECT,
                durable=True
            )
            
            # Declare queues and bind them to exchange
            await self._setup_queues()
            
            logger.info("✓ RabbitMQ connection established")
        
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise

    async def _wait_for_broker(self, max_retries: int = 10, delay: float = 1.0):
        """Simple TCP check to ensure RabbitMQ port is accepting connections.

        This helps avoid AMQP protocol errors caused by connecting before the
        broker is fully ready. Uses exponential backoff.
        """
        import asyncio
        import socket

        host = settings.RABBITMQ_HOST
        port = settings.RABBITMQ_PORT

        attempt = 0
        while attempt < max_retries:
            try:
                # Try opening a plain TCP connection
                fut = asyncio.open_connection(host=host, port=port)
                reader, writer = await asyncio.wait_for(fut, timeout=3)
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                logger.info("RabbitMQ TCP port is open")
                return
            except Exception as exc:
                attempt += 1
                wait = delay * (2 ** (attempt - 1))
                logger.debug(f"RabbitMQ not ready (attempt {attempt}/{max_retries}): {exc}")
                await asyncio.sleep(wait)

        raise ConnectionError(f"RabbitMQ TCP port {host}:{port} not reachable after {max_retries} attempts")
    
    async def _setup_queues(self):
        """Set up queues and bindings"""
        try:
            # Declare Dead Letter Exchange
            dlx = await self.channel.declare_exchange(
                "notifications.dlx",
                type=aio_pika.ExchangeType.FANOUT,
                durable=True
            )
            
            # Declare Dead Letter Queue
            failed_queue = await self.channel.declare_queue(
                "failed.queue",
                durable=True
            )
            await failed_queue.bind(dlx)
            
            # Declare Email Queue with DLX
            email_queue = await self.channel.declare_queue(
                "email.queue",
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "notifications.dlx"
                }
            )
            await email_queue.bind(
                self.exchange,
                routing_key="notification.email"
            )
            
            # Declare Push Queue with DLX
            push_queue = await self.channel.declare_queue(
                "push.queue",
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "notifications.dlx"
                }
            )
            await push_queue.bind(
                self.exchange,
                routing_key="notification.push"
            )
            
            logger.info("✓ RabbitMQ queues and bindings configured")
            
        except Exception as e:
            logger.error(f"Failed to setup queues: {str(e)}")
            raise
    
    async def publish_message(
        self,
        exchange: str,
        routing_key: str,
        message: Dict[str, Any]
    ) -> bool:
        """
        Publish message to RabbitMQ exchange
        
        Args:
            exchange: Exchange name
            routing_key: Routing key for message
            message: Message payload as dictionary
            
        Returns:
            bool: True if published successfully
        """
        try:
            if not self.channel or self.channel.is_closed:
                await self.connect()
            
            # Convert message to JSON
            message_body = json.dumps(message)
            
            # Create message with properties
            aio_message = aio_pika.Message(
                body=message_body.encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
                headers={
                    "correlation_id": message.get("correlation_id"),
                    "notification_id": message.get("notification_id")
                }
            )
            
            # Publish message
            await self.exchange.publish(
                aio_message,
                routing_key=routing_key
            )
            
            logger.info(
                f"Message published to {routing_key}: "
                f"{message.get('notification_id')}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise
    
    async def disconnect(self):
        """Close RabbitMQ connection"""
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("✓ RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {str(e)}")
    
    async def check_health(self) -> bool:
        """Check RabbitMQ connection health"""
        try:
            if self.connection and not self.connection.is_closed:
                return True
            return False
        except:
            return False
