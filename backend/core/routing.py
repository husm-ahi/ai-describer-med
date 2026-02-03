"""
WebSocket routing for core application.
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/amivoice/$', consumers.AmiVoiceProxyConsumer.as_asgi()),
    re_path(r'ws/llm/$', consumers.LLMConsumer.as_asgi()),
]
