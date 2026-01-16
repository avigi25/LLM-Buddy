#!/usr/bin/env python3
"""
LLM Proxy Recorder - Records prompts from LLM websites using a MITM proxy

This script uses mitmproxy to intercept HTTP/HTTPS traffic to LLM websites
and record the prompts sent to them. It works with various LLM services like
ChatGPT, Claude, Gemini, etc.

Dependencies:
- mitmproxy: pip install mitmproxy
"""

import os
import sys
import json
import re
import base64
from urllib.parse import urlparse
import logging
from datetime import datetime
from mitmproxy import http, ctx
from mitmproxy.script import concurrent

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompt_database import PromptDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("proxy_recorder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("proxy_recorder")

class LLMPromptRecorder:
    """
    mitmproxy addon that records prompts sent to LLM services
    """
    
    def __init__(self):
        """Initialize the recorder with a database connection"""
        self.db = PromptDatabase()
        self.active_files = []  # List of active files for auto-association
        
        # Keep track of conversation IDs for each origin
        self.conversations = {}
        
        logger.info("LLM Proxy Recorder initialized with prompt database")
    
    def load(self, loader):
        """Called when the addon is loaded"""
        logger.info("LLM Proxy Recorder loaded")
    
    def configure(self, updated):
        """Called when configuration changes"""
        logger.info("Configuration updated")
    
    @concurrent
    def request(self, flow: http.HTTPFlow) -> None:
        """Process outgoing requests to LLM services"""
        # Skip if there's no request content
        if not flow.request.content:
            return
            
        # Extract the URL and origin
        url = flow.request.pretty_url
        origin = urlparse(url).netloc
        
        # Process based on the target service
        if self._is_chatgpt_request(url):
            self._process_chatgpt(flow, origin)
        elif self._is_claude_request(url):
            self._process_claude(flow, origin)
        elif self._is_gemini_request(url):
            self._process_gemini(flow, origin)
        elif self._is_bard_request(url):
            self._process_bard(flow, origin)
        elif self._is_perplexity_request(url):
            self._process_perplexity(flow, origin)
        elif self._is_llm_api_request(url):
            self._process_generic_llm_api(flow, origin)
    
    def _is_chatgpt_request(self, url):
        """Check if the request is to OpenAI/ChatGPT"""
        patterns = [
            r'api\.openai\.com/v1/chat/completions',
            r'api\.openai\.com/v1/engines/.*/completions',
            r'api\.openai\.com/v1/completions',
            r'chat\.openai\.com/backend-api/conversation',
            # Add this new pattern for chatgpt.com
            r'chatgpt\.com/backend-api/conversation'
        ]
        return any(re.search(pattern, url) for pattern in patterns)
    
    def _is_claude_request(self, url):
        """Check if the request is to Anthropic/Claude"""
        patterns = [
            r'api\.anthropic\.com/v1/messages',
            r'api\.anthropic\.com/v1/complete',
            r'claude\.ai/api/.*?/messages'
        ]
        return any(re.search(pattern, url) for pattern in patterns)
    
    def _is_gemini_request(self, url):
        """Check if the request is to Google/Gemini"""
        patterns = [
            r'generativelanguage\.googleapis\.com',
            r'gemini\.google\.com/api',
            r'generativeai\.google\.com/api',
            r'generativeai\.googleapis\.com'
        ]
        return any(re.search(pattern, url) for pattern in patterns)
    
    def _is_bard_request(self, url):
        """Check if the request is to Google/Bard"""
        patterns = [
            r'bard\.google\.com/api',
            r'bard\.google\.com/_/BardChatUi/data'
        ]
        return any(re.search(pattern, url) for pattern in patterns)
    
    def _is_perplexity_request(self, url):
        """Check if the request is to Perplexity AI"""
        patterns = [
            r'api\.perplexity\.ai',
            r'perplexity\.ai/api'
        ]
        return any(re.search(pattern, url) for pattern in patterns)
    
    def _is_llm_api_request(self, url):
        """Check if the request is to a generic LLM API"""
        patterns = [
            r'api\.mistral\.ai',
            r'api\.cohere\.ai',
            r'api\.together\.xyz',
            r'api\.groq\.com',
            r'api\.deepinfra\.com'
        ]
        return any(re.search(pattern, url) for pattern in patterns)
    
    def _process_chatgpt(self, flow, origin):
        """Process ChatGPT requests"""
        try:
            # Parse the request body
            body = json.loads(flow.request.content)
            
            # Check for chatgpt.com backend-api format
            if 'chatgpt.com/backend-api/conversation' in flow.request.url and "action" in body:
                try:
                    # The new format has messages in a different structure
                    messages = body.get("messages", [])
                    user_messages = [m for m in messages if m.get("author", {}).get("role") == "user"]
                    
                    if user_messages:
                        # Get the most recent user message
                        user_message = user_messages[-1]
                        content = user_message.get("content", {})
                        parts = content.get("parts", []) if content.get("content_type") == "text" else []
                        
                        if parts:
                            prompt_text = parts[0]
                            conversation_id = body.get("conversation_id", f"chatgpt-{datetime.now().timestamp()}")
                            model_name = body.get("model", "ChatGPT")
                            
                            # Record the prompt with explicit source
                            prompt_id = self.db.add_prompt(
                                prompt_text=prompt_text,
                                llm_name="ChatGPT",
                                source="Web Browser",  # Explicitly set the source
                                model_name=model_name,
                                description=f"ChatGPT prompt via {origin}",
                                url=flow.request.url,
                                conversation_id=conversation_id,
                                metadata={"api_type": "chatgpt_web", "format": "new"},
                                associated_files=self.active_files
                            )
                            
                            logger.info(f"Recorded new-format ChatGPT prompt: {prompt_id} | {prompt_text}")
                            return
                except Exception as e:
                    logger.error(f"Error processing new ChatGPT format: {e}")
                
                # Debug log to help identify structure
                logger.debug(f"Unrecognized chatgpt.com format: {json.dumps(body)[:200]}")
            
            # Handle different API formats
            if "messages" in body:
                # This is the chat completions API format
                messages = body.get("messages", [])
                if not messages:
                    return
                
                # Get the last user message
                user_messages = [m for m in messages if m.get("role") == "user"]
                if not user_messages:
                    return
                
                last_user_message = user_messages[-1]
                prompt_text = last_user_message.get("content", "")
                
                # Handle content arrays (multimodal format)
                if isinstance(prompt_text, list):
                    prompt_text = " ".join(
                        item.get("text", "") for item in prompt_text 
                        if isinstance(item, dict) and item.get("type") == "text"
                    )
                
                # Get the model name if available
                model_name = body.get("model", "gpt-unknown")
                
                # Get or create conversation ID
                conversation_id = body.get("conversation_id") or f"chatgpt-{datetime.now().timestamp()}"
                
                metadata = {
                    "api_type": "chat_completions",
                    "temperature": body.get("temperature"),
                    "max_tokens": body.get("max_tokens"),
                    "messages_count": len(messages)
                }
                
                # Record the prompt with explicit source
                prompt_id = self.db.add_prompt(
                    prompt_text=prompt_text,
                    llm_name="ChatGPT",
                    source="Web Browser",  # Explicitly set the source
                    model_name=model_name,
                    description=f"ChatGPT prompt via {origin}",
                    url=flow.request.url,
                    conversation_id=conversation_id,
                    metadata=metadata,
                    associated_files=self.active_files
                )
                
                logger.info(f"Recorded ChatGPT prompt: {prompt_id}")
            
            elif "prompt" in body:
                # This is the older completions API format
                prompt_text = body.get("prompt", "")
                model_name = body.get("model", "completions-unknown")
                
                # Record the prompt with explicit source
                prompt_id = self.db.add_prompt(
                    prompt_text=prompt_text,
                    llm_name="ChatGPT",
                    source="Web Browser",  # Explicitly set the source
                    model_name=model_name,
                    description=f"ChatGPT completions prompt via {origin}",
                    url=flow.request.url,
                    metadata={
                        "api_type": "completions",
                        "temperature": body.get("temperature"),
                        "max_tokens": body.get("max_tokens")
                    },
                    associated_files=self.active_files
                )
                
                logger.info(f"Recorded ChatGPT completions prompt: {prompt_id}")
                
        except Exception as e:
            logger.error(f"Error processing ChatGPT request: {e}")
    
    def _process_claude(self, flow, origin):
        """Process Claude requests"""
        try:
            # Parse the request body
            body = json.loads(flow.request.content)
            
            # Handle different API formats
            if "prompt" in body:
                # This is the v1/complete API
                prompt_text = body.get("prompt", "")
                model_name = body.get("model", "claude-unknown")
                
                # Record the prompt
                prompt_id = self.db.add_prompt(
                    prompt_text=prompt_text,
                    llm_name="Claude",
                    source="proxy",
                    model_name=model_name,
                    description=f"Claude prompt via {origin}",
                    url=flow.request.url,
                    metadata={
                        "api_type": "complete",
                        "temperature": body.get("temperature"),
                        "max_tokens": body.get("max_tokens_to_sample")
                    },
                    associated_files=self.active_files
                )
                
                logger.info(f"Recorded Claude prompt: {prompt_id}")
                
            elif "content" in body or "messages" in body:
                # This is the v1/messages API
                messages = body.get("messages", [])
                if not messages and "content" in body:
                    # Direct content field
                    prompt_text = body.get("content", "")
                    if isinstance(prompt_text, list):
                        prompt_text = " ".join(
                            item.get("text", "") for item in prompt_text 
                            if isinstance(item, dict) and item.get("type") == "text"
                        )
                else:
                    # Get the last user message
                    user_messages = [m for m in messages if m.get("role") == "user"]
                    if not user_messages:
                        return
                    
                    last_user_message = user_messages[-1]
                    prompt_text = last_user_message.get("content", "")
                    
                    # Handle content arrays (multimodal format)
                    if isinstance(prompt_text, list):
                        prompt_text = " ".join(
                            item.get("text", "") for item in prompt_text 
                            if isinstance(item, dict) and item.get("type") == "text"
                        )
                
                # Get the model name if available
                model_name = body.get("model", "claude-unknown")
                
                # Get or create conversation ID
                conversation_id = body.get("conversation_id") or f"claude-{datetime.now().timestamp()}"
                
                metadata = {
                    "api_type": "messages",
                    "temperature": body.get("temperature"),
                    "max_tokens": body.get("max_tokens"),
                    "messages_count": len(messages) if messages else 1
                }
                
                # Record the prompt
                prompt_id = self.db.add_prompt(
                    prompt_text=prompt_text,
                    llm_name="Claude",
                    source="proxy",
                    model_name=model_name,
                    description=f"Claude message via {origin}",
                    url=flow.request.url,
                    conversation_id=conversation_id,
                    metadata=metadata,
                    associated_files=self.active_files
                )
                
                logger.info(f"Recorded Claude message: {prompt_id}")
                
        except Exception as e:
            logger.error(f"Error processing Claude request: {e}")
    
    def _process_gemini(self, flow, origin):
        """Process Gemini requests"""
        try:
            # Parse the request body
            body = json.loads(flow.request.content)
            
            # Handle different API formats
            if "contents" in body:
                # This is the Gemini API format
                contents = body.get("contents", [])
                if not contents:
                    return
                
                # Get the text parts from the contents
                prompt_text = ""
                for content in contents:
                    parts = content.get("parts", [])
                    for part in parts:
                        if "text" in part:
                            prompt_text += part.get("text", "") + " "
                
                prompt_text = prompt_text.strip()
                if not prompt_text:
                    return
                
                # Get the model name if available
                model_name = body.get("model", "gemini-unknown")
                
                # Record the prompt
                prompt_id = self.db.add_prompt(
                    prompt_text=prompt_text,
                    llm_name="Gemini",
                    source="proxy",
                    model_name=model_name,
                    description=f"Gemini prompt via {origin}",
                    url=flow.request.url,
                    metadata={
                        "temperature": body.get("temperature"),
                        "max_tokens": body.get("maxOutputTokens")
                    },
                    associated_files=self.active_files
                )
                
                logger.info(f"Recorded Gemini prompt: {prompt_id}")
                
        except Exception as e:
            logger.error(f"Error processing Gemini request: {e}")
    
    def _process_bard(self, flow, origin):
        """Process Google Bard requests"""
        try:
            # Bard uses a more complex format, often with form data or encoded JSON
            content_type = flow.request.headers.get("Content-Type", "")
            
            if "application/x-www-form-urlencoded" in content_type:
                # Try to parse form data
                form_data = flow.request.urlencoded_form
                prompt_text = ""
                
                # Look for prompt in common form fields
                for field in ["f.req", "prompt", "message", "q"]:
                    if field in form_data:
                        value = form_data[field]
                        try:
                            # Try to parse as JSON
                            json_value = json.loads(value)
                            if isinstance(json_value, list) and len(json_value) > 0:
                                # Common Bard format is a nested JSON array
                                for item in json_value:
                                    if isinstance(item, str) and len(item) > 10:
                                        prompt_text = item
                                        break
                            elif isinstance(json_value, dict):
                                # Try common fields in JSON objects
                                for subfield in ["prompt", "query", "message", "text"]:
                                    if subfield in json_value:
                                        prompt_text = json_value[subfield]
                                        break
                        except:
                            # If not JSON, use the raw value if it looks like a prompt
                            if len(value) > 10 and " " in value:
                                prompt_text = value
                
                if prompt_text:
                    # Record the prompt
                    prompt_id = self.db.add_prompt(
                        prompt_text=prompt_text,
                        llm_name="Bard",
                        source="proxy",
                        model_name="bard",
                        description=f"Bard prompt via {origin}",
                        url=flow.request.url,
                        associated_files=self.active_files
                    )
                    
                    logger.info(f"Recorded Bard prompt: {prompt_id}")
            
            elif "application/json" in content_type:
                # Try standard JSON format
                body = json.loads(flow.request.content)
                
                prompt_keys = ["prompt", "query", "message", "text", "input"]
                for key in prompt_keys:
                    if key in body:
                        prompt_text = body[key]
                        
                        # Record the prompt
                        prompt_id = self.db.add_prompt(
                            prompt_text=prompt_text,
                            llm_name="Bard",
                            source="proxy",
                            model_name="bard",
                            description=f"Bard prompt via {origin}",
                            url=flow.request.url,
                            associated_files=self.active_files
                        )
                        
                        logger.info(f"Recorded Bard prompt: {prompt_id}")
                        break
                
        except Exception as e:
            logger.error(f"Error processing Bard request: {e}")
    
    def _process_perplexity(self, flow, origin):
        """Process Perplexity AI requests"""
        try:
            # Parse the request body
            body = json.loads(flow.request.content)
            
            # Check for common Perplexity API formats
            if "text" in body:
                prompt_text = body["text"]
            elif "prompt" in body:
                prompt_text = body["prompt"]
            elif "query" in body:
                prompt_text = body["query"]
            elif "message" in body or "messages" in body:
                messages = body.get("messages", [body.get("message")] if body.get("message") else [])
                user_messages = [m for m in messages if m.get("role") == "user"]
                if user_messages:
                    prompt_text = user_messages[-1].get("content", "")
                else:
                    return
            else:
                return  # No recognizable prompt format
            
            # Record the prompt
            prompt_id = self.db.add_prompt(
                prompt_text=prompt_text,
                llm_name="Perplexity",
                source="proxy",
                model_name=body.get("model", "perplexity-unknown"),
                description=f"Perplexity prompt via {origin}",
                url=flow.request.url,
                associated_files=self.active_files
            )
            
            logger.info(f"Recorded Perplexity prompt: {prompt_id}")
            
        except Exception as e:
            logger.error(f"Error processing Perplexity request: {e}")
    
    def _process_generic_llm_api(self, flow, origin):
        """Process requests to other LLM APIs"""
        try:
            # Parse the request body
            body = json.loads(flow.request.content)
            
            # Try to identify the LLM provider from the URL
            llm_name = "Unknown LLM"
            if "mistral.ai" in origin:
                llm_name = "Mistral AI"
            elif "cohere.ai" in origin:
                llm_name = "Cohere"
            elif "together.xyz" in origin:
                llm_name = "Together AI"
            elif "groq.com" in origin:
                llm_name = "Groq"
            elif "deepinfra.com" in origin:
                llm_name = "DeepInfra"
            
            # Look for the prompt in common JSON fields
            prompt_text = None
            if "prompt" in body:
                prompt_text = body["prompt"]
            elif "messages" in body:
                messages = body["messages"]
                user_messages = [m for m in messages if m.get("role") == "user"]
                if user_messages:
                    prompt_text = user_messages[-1].get("content", "")
            elif "inputs" in body:
                prompt_text = body["inputs"]
            
            if not prompt_text:
                return
            
            # Record the prompt
            prompt_id = self.db.add_prompt(
                prompt_text=prompt_text,
                llm_name=llm_name,
                source="proxy",
                model_name=body.get("model", "unknown"),
                description=f"{llm_name} prompt via {origin}",
                url=flow.request.url,
                associated_files=self.active_files
            )
            
            logger.info(f"Recorded {llm_name} prompt: {prompt_id}")
            
        except Exception as e:
            logger.error(f"Error processing generic LLM API request: {e}")
    
    def set_active_files(self, files):
        """Set the list of active files for auto-association"""
        self.active_files = files
        logger.info(f"Set {len(files)} active files for auto-association")
    
    def clear_active_files(self):
        """Clear the list of active files"""
        old_count = len(self.active_files)
        self.active_files = []
        logger.info(f"Cleared {old_count} active files")


# Create an instance of our addon
recorder = LLMPromptRecorder()

# Add a command to set active files
def set_active_files(files):
    recorder.set_active_files(files)

def clear_active_files():
    recorder.clear_active_files()

# mitmproxy addon API
addons = [recorder]


