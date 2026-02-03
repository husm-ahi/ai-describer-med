"""
Tests for core.services.llm_service module.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from django.conf import settings
from backend.core.services.llm_service import process_with_llm, process_with_llm_stream
from backend.core.models import SystemPrompt, LLMLog


@pytest.mark.unit
@pytest.mark.django_db
class TestProcessWithLLM:
    """Tests for process_with_llm function."""
    
    @patch('backend.core.services.llm_service.completion')
    def test_process_with_llm_success(self, mock_completion, user, system_prompt):
        """Test successful LLM processing."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"result": "test"}'
        mock_completion.return_value = mock_response
        
        # Process
        result = process_with_llm(user, 'Test prompt')
        
        # Assertions
        assert result['success'] is True
        assert result['response'] == '{"result": "test"}'
        assert 'processing_time_ms' in result
        
        # Check that completion was called
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs['model'] == settings.LLM_MODEL
        assert len(call_kwargs['messages']) == 1
    
    @patch('backend.core.services.llm_service.completion')
    def test_process_with_llm_uses_active_prompt(self, mock_completion, user, system_prompt):
        """Test that active system prompt is used."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = 'Response'
        mock_completion.return_value = mock_response
        
        # Process
        result = process_with_llm(user, 'User input')
        
        # Check that prompt contains user input
        call_kwargs = mock_completion.call_args[1]
        message_content = call_kwargs['messages'][0]['content']
        assert 'User input' in message_content
    
    @patch('backend.core.services.llm_service.completion')
    def test_process_with_llm_uses_default_prompt(self, mock_completion, user):
        """Test that default prompt is used when no active prompt exists."""
        # Make sure no active prompt exists
        SystemPrompt.objects.all().delete()
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = 'Response'
        mock_completion.return_value = mock_response
        
        # Process
        result = process_with_llm(user, 'Test prompt')
        
        # Should still succeed with default prompt
        assert result['success'] is True
        
        # Check message contains SOAP format
        call_kwargs = mock_completion.call_args[1]
        message_content = call_kwargs['messages'][0]['content']
        assert 'SOAP' in message_content
    
    @patch('backend.core.services.llm_service.completion')
    def test_process_with_llm_creates_log(self, mock_completion, user, system_prompt):
        """Test that LLM log is created."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = 'Test response'
        mock_completion.return_value = mock_response
        
        # Process
        result = process_with_llm(user, 'Test prompt')
        
        # Check log was created
        log = LLMLog.objects.filter(user_prompt='Test prompt').first()
        assert log is not None
        assert log.llm_response == 'Test response'
        assert log.prompt_version == system_prompt.version
    
    @patch('backend.core.services.llm_service.completion')
    def test_process_with_llm_error_handling(self, mock_completion, user):
        """Test error handling in LLM processing."""
        # Mock LLM error
        mock_completion.side_effect = Exception('API Error')
        
        # Process
        result = process_with_llm(user, 'Test prompt')
        
        # Should return error
        assert result['success'] is False
        assert 'error' in result
        assert 'API Error' in result['error']


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.asyncio
class TestProcessWithLLMStream:
    """Tests for process_with_llm_stream async function."""
    
    @patch('backend.core.services.llm_service.acompletion')
    async def test_process_with_llm_stream_success(self, mock_acompletion, user, system_prompt):
        """Test successful streaming LLM processing."""
        # Mock streaming response
        chunk1 = Mock()
        chunk1.choices = [Mock()]
        chunk1.choices[0].delta = Mock(content='chunk1')
        chunk1.choices[0].finish_reason = None
        
        chunk2 = Mock()
        chunk2.choices = [Mock()]
        chunk2.choices[0].delta = Mock(content='chunk2')
        chunk2.choices[0].finish_reason = None
        
        chunk3 = Mock()
        chunk3.choices = [Mock()]
        chunk3.choices[0].delta = Mock(content=None)
        chunk3.choices[0].finish_reason = 'stop'
        
        async def mock_stream():
            yield chunk1
            yield chunk2
            yield chunk3
        
        mock_acompletion.return_value = mock_stream()
        
        # Process
        chunks = []
        async for chunk in process_with_llm_stream(user, 'Test prompt'):
            chunks.append(chunk)
        
        # Assertions
        assert len(chunks) >= 2  # At least content chunks + done signal
        
        # Check content chunks
        content_chunks = [c for c in chunks if 'chunk' in c and c.get('done') is False]
        assert len(content_chunks) >= 2
        assert 'chunk1' in content_chunks[0]['chunk']
        assert 'chunk2' in content_chunks[1]['chunk']
        
        # Check done signal
        done_chunks = [c for c in chunks if c.get('done') is True]
        assert len(done_chunks) == 1
        assert 'processing_time_ms' in done_chunks[0]
    
    @patch('backend.core.services.llm_service.acompletion')
    async def test_process_with_llm_stream_creates_log(self, mock_acompletion, user, system_prompt):
        """Test that streaming creates a log."""
        from asgiref.sync import sync_to_async
        
        # Mock streaming response
        chunk = Mock()
        chunk.choices = [Mock()]
        chunk.choices[0].delta = Mock(content='Test content')
        chunk.choices[0].finish_reason = 'stop'
        
        async def mock_stream():
            yield chunk
        
        mock_acompletion.return_value = mock_stream()
        
        # Process
        chunks = []
        async for chunk_data in process_with_llm_stream(user, 'Stream test'):
            chunks.append(chunk_data)
        
        # Check log was created (use sync_to_async)
        log = await sync_to_async(LLMLog.objects.filter(user_prompt='Stream test').first)()
        assert log is not None
        assert 'Test content' in log.llm_response
    
    @patch('backend.core.services.llm_service.acompletion')
    @patch('backend.core.services.llm_service.sync_to_async')
    async def test_process_with_llm_stream_fallback(self, mock_sync_to_async, mock_acompletion, user, system_prompt):
        """Test fallback to sync when streaming fails."""
        # Mock streaming failure
        mock_acompletion.side_effect = Exception('Streaming not supported')
        
        # Mock sync completion
        mock_sync_completion = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = 'Fallback response'
        mock_sync_completion.return_value = mock_response
        
        # Setup sync_to_async to return our mock
        def sync_to_async_side_effect(func):
            if func.__name__ == 'completion':
                return mock_sync_completion
            else:
                # For other functions, return a simple async wrapper
                async def wrapper(*args, **kwargs):
                    return func(*args, **kwargs)
                return wrapper
        
        mock_sync_to_async.side_effect = sync_to_async_side_effect
        
        # Process
        chunks = []
        async for chunk in process_with_llm_stream(user, 'Fallback test'):
            chunks.append(chunk)
        
        # Should get response via fallback
        done_chunks = [c for c in chunks if c.get('done') is True]
        assert len(done_chunks) == 1
    
    @patch('backend.core.services.llm_service.acompletion')
    async def test_process_with_llm_stream_error(self, mock_acompletion, user):
        """Test error handling in streaming."""
        # Mock error during stream - should trigger fallback to sync
        mock_acompletion.side_effect = Exception('Stream error')
        
        # Process
        chunks = []
        async for chunk in process_with_llm_stream(user, 'Error test'):
            chunks.append(chunk)
        
        # Should get either error chunk or fallback success
        # When streaming fails, it falls back to sync completion
        done_chunks = [c for c in chunks if c.get('done') is True]
        assert len(done_chunks) >= 1
