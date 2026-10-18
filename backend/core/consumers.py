"""
WebSocket consumers for core application.
"""
import asyncio
import websockets
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class AmiVoiceProxyConsumer(AsyncWebsocketConsumer):
    """
    WebSocket proxy for AmiVoice API.
    Handles bidirectional communication between client and AmiVoice API.
    """
    
    async def connect(self):
        """Accept WebSocket connection and connect to AmiVoice API."""
        # Check if user is authenticated
        if not self.scope["user"].is_authenticated:
            await self.close(code=4401)
            return
        
        await self.accept()
        
        try:
            # Connect to AmiVoice API
            amivoice_url = settings.AMIVOICE_API_URL
            self.amivoice_ws = await websockets.connect(amivoice_url)
            
            # Start receiving messages from AmiVoice
            asyncio.create_task(self.receive_from_amivoice())
            
            logger.info(f"AmiVoice connection established for user {self.scope['user'].username}")
            
        except Exception as e:
            logger.error(f"Failed to connect to AmiVoice API: {e}")
            await self.send(text_data=json.dumps({
                'error': 'Failed to connect to speech recognition service'
            }))
            await self.close()
    
    async def disconnect(self, close_code):
        """Close connection to AmiVoice API."""
        if hasattr(self, 'amivoice_ws'):
            await self.amivoice_ws.close()
        logger.info(f"AmiVoice connection closed for user {self.scope['user'].username}")
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Receive audio data from client and forward to AmiVoice API.
        """
        try:
            if bytes_data:
                if settings.DEBUG:
                    logger.debug(f"WS received bytes data. len={len(bytes_data)} bytes={bytes_data[:10]}...")

                # Forward binary audio data to AmiVoice
                await self.amivoice_ws.send(bytes_data)
            elif text_data:
                if settings.DEBUG:
                    logger.debug(f"WS received text data: len={len(text_data)} text={text_data}")
                
                # Replace the grammar name and authorization key
                if text_data.startswith("s "):
                    parts = text_data.split(" ")
                    parts[2] = settings.AMIVOICE_GRAMMAR  # Update grammar
                    api_key_embedded = False
                    for i, part in enumerate(parts):
                        if part.startswith("authorization="):
                            parts[i] = f"authorization={settings.AMIVOICE_API_KEY}"  # Update API key
                            api_key_embedded = True
                            break
                    if not api_key_embedded:
                        parts.append(f"authorization={settings.AMIVOICE_API_KEY}")
                    text_data = " ".join(parts)
                
                    if settings.DEBUG:
                        # Mask API key in debug logs for security
                        masked_data = text_data.replace(settings.AMIVOICE_API_KEY, "***MASKED***")
                        logger.debug(f"Forwarding to AmiVoice: text={masked_data}")

                # Handle text commands (e.g., end of speech)
                await self.amivoice_ws.send(text_data)
        except Exception as e:
            logger.error(f"Error forwarding data to AmiVoice: {e}")
            await self.send(text_data=json.dumps({
                'error': 'Failed to send data to speech recognition service'
            }))
    
    async def receive_from_amivoice(self):
        """
        Receive recognition results from AmiVoice API and forward to client.
        """
        try:
            async for message in self.amivoice_ws:
                # Forward AmiVoice response to client
                # (All messages from AmiVoice API are text messages)
                assert isinstance(message, str)

                if settings.DEBUG:
                    logger.debug(f"Received from AmiVoice: len={len(message)} message={message}")
                
                await self.send(text_data=message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("AmiVoice connection closed")
        except Exception as e:
            logger.error(f"Error receiving from AmiVoice: {e}")
            await self.send(text_data="e error receiving data from AmiVoice service")


class LLMConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for LLM processing with streaming support.
    """
    
    async def connect(self):
        """Accept WebSocket connection for LLM processing."""
        # Check if user is authenticated
        if not self.scope["user"].is_authenticated:
            await self.close(code=4401)
            return
        
        await self.accept()
        logger.info(f"LLM WebSocket connection established for user {self.scope['user'].username}")
    
    async def disconnect(self, close_code):
        """Close LLM WebSocket connection."""
        logger.info(f"LLM WebSocket connection closed for user {self.scope['user'].username}")
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Receive user prompt and process through LLM with streaming.
        """
        if not text_data:
            await self.send(text_data=json.dumps({
                'error': 'No data received',
                'done': True
            }))
            return
        
        try:
            data = json.loads(text_data)
            user_prompt = data.get('prompt', '')
            
            if not user_prompt or not isinstance(user_prompt, str):
                await self.send(text_data=json.dumps({
                    'error': 'Prompt is required',
                    'done': True
                }))
                return
            
            if len(user_prompt) > settings.LLM_MAX_PROMPT_CHARS:
                await self.send(text_data=json.dumps({
                    'error': 'Prompt is too long',
                    'done': True
                }))
                return
            
            # Import here to avoid circular imports
            from .services.llm_service import process_with_llm_stream
            
            # Process with streaming
            async for chunk in process_with_llm_stream(self.scope['user'], user_prompt):
                await self.send(text_data=json.dumps(chunk))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON',
                'done': True
            }))
        except Exception as e:
            logger.error(f"Error in LLM processing: {e}", exc_info=True)
            # Do not expose internal error details to the client
            await self.send(text_data=json.dumps({
                'error': 'LLM processing failed',
                'done': True
            }))
