"""
Tests for core.consumers module.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.core.consumers import AmiVoiceProxyConsumer
import inspect


@pytest.mark.asyncio
@pytest.mark.django_db
class TestAmiVoiceProxyConsumer:
    """Tests for AmiVoiceProxyConsumer."""
    
    async def test_connect_requires_authentication(self):
        """Test that connection requires authentication."""
        from channels.testing import WebsocketCommunicator
        
        # Create communicator without authenticated user
        communicator = WebsocketCommunicator(
            AmiVoiceProxyConsumer.as_asgi(),
            "/ws/amivoice/"
        )
        communicator.scope['user'] = Mock(is_authenticated=False)
        
        connected, _ = await communicator.connect()
        
        # Should not connect
        assert not connected
        
        await communicator.disconnect()
    
    @patch('backend.core.consumers.websockets.connect')
    async def test_connect_authenticated_user(self, mock_ws_connect, user):
        """Test that authenticated user can connect."""
        from channels.testing import WebsocketCommunicator
        
        # Mock AmiVoice WebSocket connection
        mock_amivoice_ws = AsyncMock()
        
        # Make connect an async function
        async def async_connect(*args, **kwargs):
            return mock_amivoice_ws
        mock_ws_connect.side_effect = async_connect
        
        # Create communicator with authenticated user
        communicator = WebsocketCommunicator(
            AmiVoiceProxyConsumer.as_asgi(),
            "/ws/amivoice/"
        )
        communicator.scope['user'] = user
        
        connected, _ = await communicator.connect()
        
        # Should connect successfully
        assert connected
        
        await communicator.disconnect()
    
    @patch('backend.core.consumers.websockets.connect')
    async def test_connection_error_handling(self, mock_ws_connect, user):
        """Test error handling when AmiVoice connection fails."""
        from channels.testing import WebsocketCommunicator
        
        # Mock AmiVoice connection failure
        async def async_connect_error(*args, **kwargs):
            raise Exception('Connection failed')
        mock_ws_connect.side_effect = async_connect_error
        
        # Create communicator
        communicator = WebsocketCommunicator(
            AmiVoiceProxyConsumer.as_asgi(),
            "/ws/amivoice/"
        )
        communicator.scope['user'] = user
        
        connected, _ = await communicator.connect()
        
        # Should still accept connection but may send error
        assert connected
        
        # May receive error message
        try:
            response = await communicator.receive_from(timeout=1)
            # Error message might be sent
        except:
            # Or connection might close immediately
            pass
        
        await communicator.disconnect()


@pytest.mark.unit
class TestConsumerConfiguration:
    """Tests for consumer configuration."""
    
    def test_consumer_can_be_imported(self):
        """Test that consumer can be imported successfully."""
        from backend.core.consumers import AmiVoiceProxyConsumer
        assert AmiVoiceProxyConsumer is not None
    
    def test_consumer_is_async(self):
        """Test that consumer is async-capable."""
        from backend.core.consumers import AmiVoiceProxyConsumer
        # AsyncWebsocketConsumer methods should be async
        assert inspect.iscoroutinefunction(AmiVoiceProxyConsumer.connect)
        assert inspect.iscoroutinefunction(AmiVoiceProxyConsumer.disconnect)
        assert inspect.iscoroutinefunction(AmiVoiceProxyConsumer.receive)
