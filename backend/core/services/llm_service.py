"""
Service layer for LLM integration using liteLLM.
"""
import time
import logging
from typing import Dict, Any, AsyncGenerator
from django.conf import settings
from litellm import completion, acompletion
from ..models import SystemPrompt, LLMLog
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


def process_with_llm(user, user_prompt: str) -> Dict[str, Any]:
    """
    Process user prompt through LLM and return structured result.
    
    Args:
        user: Django User instance
        user_prompt: User's input text (from speech recognition)
    
    Returns:
        Dict containing the structured LLM response
    """
    start_time = time.time()
    
    try:
        # Get active system prompt
        try:
            system_prompt_obj = SystemPrompt.objects.filter(is_active=True).latest('created_at')
            system_prompt = system_prompt_obj.content
            prompt_version = system_prompt_obj.version
            
            # Replace placeholder with user prompt
            system_prompt = system_prompt.replace('{{{USER_INPUT}}}', user_prompt)
        except SystemPrompt.DoesNotExist:
            system_prompt = (
                "あなたは医療記録を構造化するAIアシスタントです。\n"
                "以下の情報をSOAP形式で構造化してJSON形式で返してください。\n"
                "{\n"
                '  "subjective": "主訴・現病歴",\n'
                '  "objective": "身体所見・検査所見",\n'
                '  "assessment": "診断・評価",\n'
                '  "plan": "治療計画"\n'
                "}\n\n"
                f"{user_prompt}"
            )
            prompt_version = "default"
        
        # Call LLM through liteLLM
        # When using placeholder replacement, send as single user message
        response = completion(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "user", "content": system_prompt}
            ],
            temperature=0.7,
        )
        
        # Extract response
        llm_response = response.choices[0].message.content
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Save log
        LLMLog.create_log(
            user=user,
            user_prompt=user_prompt,
            llm_response=llm_response,
            model_name=settings.LLM_MODEL,
            prompt_version=prompt_version,
            processing_time_ms=processing_time_ms
        )
        
        logger.info(f"LLM processing completed in {processing_time_ms}ms for user {user.username}")
        
        return {
            'success': True,
            'response': llm_response,
            # 'model': settings.LLM_MODEL,
            'processing_time_ms': processing_time_ms
        }
        
    except Exception as e:
        logger.error(f"LLM processing failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


async def process_with_llm_stream(user, user_prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Process user prompt through LLM with streaming support.
    
    Args:
        user: Django User instance
        user_prompt: User's input text (from speech recognition)
    
    Yields:
        Dict containing streaming chunks or final result
    """
    start_time = time.time()
    full_response = ""
    
    try:
        # Get active system prompt
        try:
            system_prompt_obj = await sync_to_async(
                SystemPrompt.objects.filter(is_active=True).latest
            )('created_at')
            system_prompt = system_prompt_obj.content
            prompt_version = system_prompt_obj.version
            
            # Replace placeholder with user prompt
            system_prompt = system_prompt.replace('{{{USER_INPUT}}}', user_prompt)
        except SystemPrompt.DoesNotExist:
            system_prompt = (
                "あなたは医療記録を構造化するAIアシスタントです。\n"
                "以下の情報をSOAP形式で構造化してJSON形式で返してください。\n"
                "{\n"
                '  "subjective": "主訴・現病歴",\n'
                '  "objective": "身体所見・検査所見",\n'
                '  "assessment": "診断・評価",\n'
                '  "plan": "治療計画"\n'
                "}\n\n"
                f"{user_prompt}"
            )
            prompt_version = "default"
        
        if settings.DEBUG:
            logger.debug(f"System Prompt: {system_prompt}")
        
        # Try streaming first
        try:
            response = await acompletion(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "user", "content": system_prompt}
                ],
                temperature=0.7,
                stream=True,
            )
            
            # Stream response chunks
            # Note: liteLLM doesn't include explicit 'done' flag
            # finish_reason indicates completion (e.g., 'stop', 'length')
            async for chunk in response:
                # Check if chunk has content
                if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield {
                        'chunk': content,
                        'done': False
                    }
                
                # Check finish_reason to detect end of stream
                if chunk.choices[0].finish_reason:
                    logger.debug(f"Stream finished with reason: {chunk.choices[0].finish_reason}")
            
            # Streaming completed (async for loop ended)
            processing_time_ms = int((time.time() - start_time) * 1000)
            
        except Exception as stream_error:
            # If streaming fails, fall back to synchronous
            logger.warning(f"Streaming failed, falling back to sync: {stream_error}")
            
            response = await sync_to_async(completion)(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "user", "content": system_prompt}
                ],
                temperature=0.7,
            )
            
            full_response = response.choices[0].message.content
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Send full response as one chunk
            yield {
                'chunk': full_response,
                'done': False
            }
        
        # Save log
        await sync_to_async(LLMLog.create_log)(
            user=user,
            user_prompt=user_prompt,
            llm_response=full_response,
            model_name=settings.LLM_MODEL,
            prompt_version=prompt_version,
            processing_time_ms=processing_time_ms
        )
        
        logger.info(f"LLM streaming completed in {processing_time_ms}ms for user {user.username}")
        
        # Send completion signal
        yield {
            'done': True,
            'processing_time_ms': processing_time_ms,
            'full_response': full_response
        }
        
    except Exception as e:
        logger.error(f"LLM streaming failed: {e}")
        yield {
            'error': str(e),
            'done': True
        }
