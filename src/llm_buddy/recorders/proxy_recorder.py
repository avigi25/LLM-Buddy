### C:/Users/antho/Downloads/LLM Buddy UX/LLM Buddy\src\llm_buddy\recorders\proxy_recorder.py

#!/usr/bin/env python3
"""
LLM Proxy Recorder - Records prompts from LLM websites using a MITM proxy.

Uses mitmproxy to intercept HTTP/HTTPS traffic to LLM websites and record
the prompts sent to them.

Supported providers:
  ChatGPT / OpenAI          Gemini / Google AI         Claude / Anthropic
  Perplexity                Grok / xAI                 DeepSeek
  OpenRouter                Le Chat / Mistral          HuggingChat
  Meta AI                   Microsoft Copilot          You.com
  Phind                     Mistral API                Cohere
  Together AI               Groq                       DeepInfra
"""

import json
import logging
import os
import re
import sys
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from mitmproxy import http
import base64

# mitmproxy 10+ removed the @concurrent decorator and raises
# NotImplementedError at class-definition time, silently killing the
# entire addon. The import itself succeeds but the decorator raises
# when applied to a method. Define a no-op unconditionally.
# (mitmproxy 10+ runs addon hooks concurrently by default.)
def concurrent(fn):  # type: ignore[misc]
    """No-op replacement for the removed mitmproxy @concurrent decorator."""
    return fn


os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join("logs", "proxy_recorder.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("proxy_recorder")

# Try to use the unified database; fall back to a local instance
try:
    from llm_buddy.core.database import PromptDatabase
    logger.info("Using unified LLM Buddy database")
except ImportError:
    # Standalone mode - look for prompt_database.py alongside this file
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from prompt_database import PromptDatabase  # type: ignore
        logger.info("Using local prompt_database module")
    except ImportError:
        logger.error(
            "No PromptDatabase available. Install llm-buddy or "
            "place prompt_database.py next to this file."
        )
        sys.exit(1)


class LLMPromptRecorder:
    """mitmproxy addon that records prompts sent to LLM services."""

    def __init__(self):
        self.db = PromptDatabase()
        self.active_files = []
        self.conversations = {}
        # Map flow IDs to prompt IDs for response pairing
        self._pending_responses: dict[str, tuple[str, str]] = {}

        # Gemini Web UI: map operation/request ids (e.g. r_e...) -> prompt_id
        # Gemini often does: batchexecute returns reqid; assistant.l returns actual output.
        self._gemini_reqid_to_prompt: dict[str, str] = {}
        self._latest_chatgpt_prompt_id = None

        logger.info("LLM Proxy Recorder initialized")

    def load(self, loader):
        logger.info("LLM Proxy Recorder loaded")

    def configure(self, updated):
        logger.info("Configuration updated")

    # ------------------------------------------------------------------
    # Request matching
    # ------------------------------------------------------------------

    @staticmethod
    def _match(url, patterns):
        return any(re.search(p, url) for p in patterns)

    @staticmethod
    def _find_reqid(text: str) -> str:
        """Find Gemini reqid tokens like r_e870ca6194466443 in arbitrary text."""
        m = re.search(r"\br_e[0-9a-f]{8,}\b", text)
        return m.group(0) if m else ""

    @concurrent
    def request(self, flow: http.HTTPFlow) -> None:
        """Process outgoing requests to LLM services."""
        if not flow.request.content:
            return

        url = flow.request.pretty_url
        origin = urlparse(url).netloc

        for patterns, method_name, llm_name in _REQUEST_DISPATCH:
            if self._match(url, patterns):
                processor = getattr(self, method_name)
                if llm_name:
                    processor(flow, origin, llm_name=llm_name)
                else:
                    processor(flow, origin)
                return

    @concurrent
    def response(self, flow: http.HTTPFlow) -> None:
        """Process responses from LLM services and pair with prompts."""
        info = self._pending_responses.pop(flow.id, None)
        if not info:
            return

        prompt_id, llm_source = info

        if not flow.response or not flow.response.content:
            return

        try:
            content_type = flow.response.headers.get("content-type", "")
            text = flow.response.get_text(strict=False)
            if not text:
                return

            # Dispatch to format-aware parser based on LLM source
            parser_name = _RESPONSE_PARSER.get(llm_source, "_parse_generic_response")
            parser = getattr(self, parser_name)
            response_text = parser(text, content_type)

            # Gemini Web UI: batchexecute often returns only a request id (r_e...).
            # If we can extract it, store it and wait for assistant.l response.
            if llm_source == "Gemini" and not (response_text and response_text.strip()):
                reqid = self._find_reqid(text)
                if reqid:
                    self._gemini_reqid_to_prompt[reqid] = prompt_id
                    logger.info(
                        "Gemini returned reqid %s for prompt %s; waiting for assistant.l",
                        reqid,
                        prompt_id,
                    )
                    return

            if response_text and response_text.strip():
                self.db.update_response(prompt_id, response_text.strip())
                logger.info(
                    "Captured %s response for prompt %s (%d chars)",
                    llm_source,
                    prompt_id,
                    len(response_text),
                )
            else:
                # Add visibility into why a response parsed blank
                head = text[:500]
                logger.warning(
                    "Blank %s response for prompt %s (content-type=%s, head=%r)",
                    llm_source,
                    prompt_id,
                    content_type,
                    head,
                )

        except Exception as e:
            logger.error("Error processing %s response: %s", llm_source, e)

    # ------------------------------------------------------------------
    # Format-specific response parsers
    # ------------------------------------------------------------------

    @concurrent
    def websocket_message(self, flow: http.HTTPFlow) -> None:
        """Intercept WebSocket messages for ChatGPT Stream Handoff."""
        if not flow.websocket:
            return

        message = flow.websocket.messages[-1]
        # Only process messages coming from the server
        if message.from_client:
            return
            
        url = flow.request.pretty_url
        if "chatgpt.com" in url:
            content = message.content
            if isinstance(content, str):
                content = content.encode('utf-8')
                
            self._process_chatgpt_websocket(content, url)
            
    def _process_chatgpt_websocket(self, content: bytes, url: str):
        """Decode embedded SSE JSON-patch payloads and append to active prompt."""
        try:
            text = content.decode('utf-8')
        except Exception:
            return # Ignore non-text frames

        # Ensure we have an active prompt to attach this response to
        if not getattr(self, "_latest_chatgpt_prompt_id", None):
            return

        try:
            # The WS frames are now pure JSON arrays, no "42" stripping required
            payloads = json.loads(text)
            if not isinstance(payloads, list):
                return
                
            extracted_text = ""
            
            for item in payloads:
                # 1. Navigate down the new JSON tree: item -> payload -> payload -> encoded_item
                inner_payload1 = item.get("payload", {})
                inner_payload2 = inner_payload1.get("payload", {}) if isinstance(inner_payload1, dict) else {}
                encoded_item = inner_payload2.get("encoded_item", "") if isinstance(inner_payload2, dict) else ""
                
                if not encoded_item:
                    continue
                    
                # 2. encoded_item is a string formatted as Server-Sent Events (SSE)
                # Example: 'event: delta\ndata: {"v": [{"p": "/message/content/parts/0", "o": "append", "v": "text"}]}\n\n'
                lines = encoded_item.split('\n')
                for line in lines:
                    if line.startswith("data: "):
                        data_str = line[len("data: "):].strip()
                        
                        if data_str == "[DONE]" or not data_str:
                            continue
                            
                        try:
                            # 3. Parse the embedded JSON inside the data string
                            data_json = json.loads(data_str)
                            
                            # 4. Extract the JSON Patch operations 
                            # (They are usually located in a list under the "v" key)
                            v_list = data_json.get("v", [])
                            
                            if isinstance(v_list, list):
                                for patch in v_list:
                                    # Look for append operations targeting the message parts
                                    if patch.get("o") == "append" and "parts" in patch.get("p", ""):
                                        chunk = patch.get("v", "")
                                        if isinstance(chunk, str):
                                            extracted_text += chunk
                                            
                        except json.JSONDecodeError:
                            pass # Ignore malformed data chunks
                            
            # 5. Save the stitched text to the database
            if extracted_text:
                prompt = self.db.get_prompt(self._latest_chatgpt_prompt_id)
                if prompt:
                    current_response = getattr(prompt, "response_text", "") or ""
                    new_response = current_response + extracted_text
                    self.db.update_response(self._latest_chatgpt_prompt_id, new_response)
                    logger.info(f"Appended {len(extracted_text)} chars from WS to prompt {self._latest_chatgpt_prompt_id}")
                        
        except json.JSONDecodeError:
            pass # Ignore frames that aren't valid JSON arrays
        except Exception as e:
            logger.error(f"Error processing ChatGPT websocket stream: {e}")

    @staticmethod
    def _iter_sse_data(text: str):
        """Yield parsed JSON objects from an SSE text/event-stream."""
        for line in text.split("\n"):
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str in ("[DONE]", ""):
                continue
            try:
                yield json.loads(data_str)
            except json.JSONDecodeError:
                pass

    def _parse_chatgpt_response(self, text: str, content_type: str) -> str:
        """Parse ChatGPT responses (API + Web UI, streaming + non-streaming)."""
        # --- ADDED THIS TRACING BLOCK ---
        #import time
        #debug_filename = f"chatgpt_debug_{int(time.time())}.log"
        #with open(debug_filename, "w", encoding="utf-8") as f:
        #    f.write(text)
        #    logger.info(f"Saved raw ChatGPT response stream to {debug_filename}")
        # ------------------------------

        try:
            data = json.loads(text)
            # Standard OpenAI API format
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
            # Internal Web UI format
            if "message" in data and "content" in data["message"] and "parts" in data["message"]["content"]:
                return "".join(data["message"]["content"]["parts"])
        except json.JSONDecodeError:
            pass  # Expected for SSE streams

        # We will collect text and code in sequence to maintain conversational order
        blocks = []
        
        # Read the stream line by line
        for line in text.splitlines():
            if line.startswith('data: '):
                data_str = line[6:].strip()
                
                # OpenAI stream termination marker
                if data_str == '[DONE]':
                    break
                
                try:
                    data = json.loads(data_str)
                    
                    # Check for standard OpenAI API streaming delta
                    if "choices" in data and len(data["choices"]) > 0:
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            blocks.append(("text", delta["content"]))
                        continue

                    # Check for ChatGPT Web UI streaming delta patches
                    operations = []
                    if isinstance(data, dict):
                        # Patch array can be nested under "v" alongside "o": "patch"
                        if data.get("o") == "patch" and isinstance(data.get("v"), list):
                            operations = data["v"]
                        # Some root-level events are standalone operations
                        elif "o" in data and "v" in data:
                            operations = [data]
                        # Array directly under "v"
                        elif isinstance(data.get("v"), list):
                            operations = data["v"]
                    
                    # Process the patch operations
                    for op in operations:
                        if isinstance(op, dict):
                            p = op.get("p", "")
                            o = op.get("o", "")
                            v = op.get("v", "")
                            
                            # 1. Handle streaming text/code appends
                            if o == "append" and isinstance(v, str):
                                # Standard conversational text
                                if p.startswith("/message/content/parts/"):
                                    blocks.append(("text", v))
                                # Tool generation payloads (Image prompts, Python code)
                                elif p == "/message/content/text":
                                    blocks.append(("code", v))
                            
                            # 2. Handle static block additions (like tool output or complete text replacements)
                            elif o == "add" and isinstance(v, dict):
                                msg = v.get("message", {})
                                content = msg.get("content", {})
                                if isinstance(content, dict) and content.get("content_type") == "text" and "parts" in content:
                                    parts_text = "".join(str(part) for part in content["parts"] if isinstance(part, str))
                                    # Filter out unhelpful boilerplate tool notifications
                                    if parts_text and "Processing image" not in parts_text:
                                        author_role = msg.get("author", {}).get("role", "system")
                                        blocks.append(("text", f"\n\n[{author_role}]: {parts_text}\n\n"))
                                        
                except json.JSONDecodeError:
                    # Ignore unparseable lines
                    pass

        # Reconstruct the response with proper markdown code blocks interleaving
        res = ""
        last_type = None
        
        for b_type, b_text in blocks:
            if b_type != last_type:
                if last_type is not None:
                    if b_type == "code":
                        # Guess format (image gen is usually JSON payload, else generic markdown)
                        res += "\n\n```json\n" if b_text.strip().startswith("{") else "\n\n```\n"
                    elif last_type == "code":
                        res += "\n```\n\n"
                elif b_type == "code":
                    res += "```json\n" if b_text.strip().startswith("{") else "```\n"
            res += b_text
            last_type = b_type

        # Close any lingering code block
        if last_type == "code":
            res += "\n```"

        return res.strip()

    def _parse_claude_response(self, text: str, content_type: str) -> str:
        """Parse Claude responses (API + Web UI, streaming + non-streaming)."""

        # --- Non-streaming API response ---
        if "text/event-stream" not in content_type:
            try:
                body = json.loads(text)
                # Claude messages API: content[].text
                blocks = body.get("content", [])
                texts = [
                    b["text"]
                    for b in blocks
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                if texts:
                    return "\n".join(texts)
                # Legacy complete API
                return body.get("completion", "")
            except Exception:
                return ""

        # --- SSE streaming ---
        chunks: list[str] = []

        for obj in self._iter_sse_data(text):
            obj_type = obj.get("type", "")

            # Claude API: content_block_delta → delta.text
            if obj_type == "content_block_delta":
                delta = obj.get("delta", {})
                if delta.get("type") == "text_delta":
                    chunks.append(delta.get("text", ""))
                continue

            # Claude Web UI / legacy: completion field (cumulative)
            comp = obj.get("completion")
            if comp:
                chunks.append(comp)
                continue

        return "".join(chunks)

    def _parse_gemini_response(self, text: str, content_type: str) -> str:
        """Parse Gemini responses (API JSON, API SSE, and Web UI RPC)."""

        # --- ADDED THIS TRACING BLOCK ---
        #import time
        #debug_filename = f"gemini_debug_{int(time.time())}.log"
        #with open(debug_filename, "w", encoding="utf-8") as f:
        #    f.write(text)
        #    logger.info(f"Saved raw Gemini response stream to {debug_filename}")
        # ------------------------------

        # Gemini Web UI responses often start with )]}' even when Content-Type is application/json.
        if text.startswith(")]}'"):
            clean = text.split("\n", 1)[-1]
            return self._extract_gemini_rpc_text(clean)

        # --- Gemini API: streaming SSE ---
        if "text/event-stream" in content_type:
            parts_text: list[str] = []
            for obj in self._iter_sse_data(text):
                parts_text.extend(self._extract_gemini_api_parts(obj))
            return "".join(parts_text)

        # --- Gemini API: non-streaming JSON ---
        if "application/json" in content_type:
            try:
                body = json.loads(text)
                parts = self._extract_gemini_api_parts(body)
                joined = "".join(parts)
                if joined:
                    return joined
            except Exception:
                pass
            # Fall back to RPC extractor if it wasn't clean JSON.
            return self._extract_gemini_rpc_text(text)

        # --- Gemini Web UI: RPC format ---
        clean = text.split("\n", 1)[-1] if text.startswith(")]}'") else text
        return self._extract_gemini_rpc_text(clean)

    @staticmethod
    def _extract_gemini_api_parts(obj: dict) -> list[str]:
        """Extract text parts from a Gemini API response object.

        Works for both generateContent and streamGenerateContent.
        Schema: candidates[].content.parts[].text
        """
        texts: list[str] = []
        try:
            for candidate in obj.get("candidates", []):
                for part in candidate.get("content", {}).get("parts", []):
                    if "text" in part:
                        texts.append(part["text"])
        except (TypeError, AttributeError):
            pass
        return texts

    def _extract_gemini_rpc_text(self, text: str) -> str:
        """Extract response text from Gemini Web UI's nested RPC format."""
        root_objects: list[Any] = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.isdigit():
                continue
            try:
                root_objects.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        if not root_objects:
            try:
                root_objects = [json.loads(text)]
            except Exception:
                return ""

        raw_strings: list[str] = []
        for obj in root_objects:
            self._collect_leaf_strings(obj, raw_strings)

        if not raw_strings:
            return ""

        candidates: list[str] = []
        for s in raw_strings:
            if not isinstance(s, str):
                continue
            
            # Work with clean strings for accurate filtering
            s_stripped = s.strip()
            if not s_stripped:
                continue

            # Skip the generic Google internal status codes and known plumbing
            if s_stripped in ("af.httprm", "di", "en", "US", "imagen_default", "image_generation_content", "und"):
                continue

            # Skip explicitly known UI or internal tokens
            if "Nano Banana" in s_stripped or "data_analysis_tool" in s_stripped or "google_search_tool" in s_stripped:
                continue

            # Skip obvious hashes and IDs
            if re.fullmatch(r"[a-f0-9\-]{20,}", s_stripped):
                continue

            # Skip strings without spaces that are suspiciously long 
            # (Catches Base64 blobs, SafeSearch keys, raw icon URLs)
            if len(s_stripped) > 25 and " " not in s_stripped:
                continue
                
            # Skip image generation filenames
            if re.search(r"\.(png|jpeg|jpg|webp|gif|svg)$", s_stripped, re.IGNORECASE):
                continue

            # Skip internal Knowledge Graph entities (e.g., /m/09g5pq)
            if re.match(r"^/[mja]/[a-zA-Z0-9_]+$", s_stripped):
                continue

            # Skip internal safety/classifier keys
            if any(k in s_stripped for k in ["_classifier", "_precondition", "input_prompt_regex", "image_output", "csam_"]):
                continue

            if "bard_" in s_stripped or "Bard" in s_stripped and len(s_stripped) < 60:
                continue
            if s_stripped.startswith("r_") or s_stripped.startswith("c_") or s_stripped.startswith("rc_"):
                continue

            # Skip short strings that are mostly numbers or symbols
            if len(s_stripped) < 20 and re.search(r"^[0-9\.\-\s\[\]\(\)]+$", s_stripped):
                continue

            # CRITICAL FILTER: Protect code and conversational text while dropping ML tags.
            has_newline = "\n" in s_stripped
            has_markdown = "`" in s_stripped or "**" in s_stripped
            has_url = "http://" in s_stripped or "https://" in s_stripped
            
            # Allow common sentence punctuation AND code block closures
            ends_with_punct = s_stripped.endswith((
                '.', '!', '?', '"', "'", ':', ';', 
                '}', ']', ')', '`', '>', '*'
            ))
            
            # If a string is short, it MUST contain conversational punctuation, code structures, or a URL.
            if len(s_stripped) < 100 and not (ends_with_punct or has_url or has_newline or has_markdown):
                continue

            candidates.append(s_stripped)

        if not candidates:
            return ""

        # Remove duplicates and subsets to get a clean combined response
        seen = set()
        unique_texts = []
        for t in candidates:
            if t in seen:
                continue
            seen.add(t)

            is_subset = False
            for kept in list(unique_texts):
                if t in kept:
                    is_subset = True
                    break
                if kept in t:
                    # 't' is larger and contains the previously kept text, replace it
                    unique_texts.remove(kept)
                    seen.remove(kept)
            
            if not is_subset:
                unique_texts.append(t)

        # Sort descending by length so the main conversational response body is first
        unique_texts.sort(key=len, reverse=True)
        
        # Join all valid text blocks
        return "\n\n".join(unique_texts)

    def _collect_leaf_strings(self, obj, results: list[str]) -> None:
        """Walk a JSON structure and collect *leaf* text strings.

        If a string value is itself valid JSON (a common Gemini RPC
        pattern), it is recursively parsed and its inner strings are
        collected instead.
        """
        if isinstance(obj, str):
            # Try to unwrap JSON-in-a-string
            stripped = obj.strip()
            if stripped and stripped[0] in ("[", "{"):
                try:
                    inner = json.loads(stripped)
                    self._collect_leaf_strings(inner, results)
                    return
                except (json.JSONDecodeError, RecursionError):
                    pass
            results.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                self._collect_leaf_strings(item, results)
        elif isinstance(obj, dict):
            for val in obj.values():
                self._collect_leaf_strings(val, results)

    def _parse_deepseek_response(self, text: str, content_type: str) -> str:
        """Parse DeepSeek responses, including reasoning_content from R1."""
        reasoning_chunks: list[str] = []
        content_chunks: list[str] = []

        # --- Non-streaming ---
        if "text/event-stream" not in content_type:
            try:
                body = json.loads(text)
                choice = body["choices"][0]["message"]
                reasoning = choice.get("reasoning_content", "")
                content = choice.get("content", "")
                parts: list[str] = []
                if reasoning:
                    parts.append(f"<thinking>\n{reasoning}\n</thinking>")
                if content:
                    parts.append(content)
                return "\n\n".join(parts)
            except Exception:
                return ""

        # --- SSE streaming ---
        for obj in self._iter_sse_data(text):
            try:
                delta = obj["choices"][0]["delta"]
                rc = delta.get("reasoning_content")
                if rc:
                    reasoning_chunks.append(rc)
                ct = delta.get("content")
                if ct:
                    content_chunks.append(ct)
            except (KeyError, IndexError, TypeError):
                pass

        parts: list[str] = []
        if reasoning_chunks:
            parts.append(f"<thinking>\n{''.join(reasoning_chunks)}\n</thinking>")
        if content_chunks:
            parts.append("".join(content_chunks))
        return "\n\n".join(parts)

    def _parse_generic_response(self, text: str, content_type: str) -> str:
        """Fallback parser for Perplexity, Mistral, Groq, etc."""

        # --- SSE (OpenAI-compatible deltas) ---
        if "text/event-stream" in content_type:
            chunks: list[str] = []
            for obj in self._iter_sse_data(text):
                try:
                    delta = obj["choices"][0]["delta"].get("content")
                    if delta:
                        chunks.append(delta)
                except (KeyError, IndexError, TypeError):
                    pass
            if chunks:
                return "".join(chunks)

        # --- Non-streaming JSON ---
        try:
            body = json.loads(text)
            # OpenAI chat completions
            try:
                return body["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                pass
            # Claude-style
            blocks = body.get("content", [])
            if isinstance(blocks, list):
                texts = [
                    b["text"]
                    for b in blocks
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                if texts:
                    return "\n".join(texts)
        except Exception:
            pass

        return ""

    # ------------------------------------------------------------------
    # LLM-specific processors
    # ------------------------------------------------------------------

    def _process_chatgpt(self, flow, origin, llm_name="ChatGPT"):
        try:
            text = flow.request.get_text(strict=False)
            if not text:
                return
            body = json.loads(text)

            # ChatGPT Web UI format (POST .../conversation)
            path = urlparse(flow.request.pretty_url).path or ""
            is_webui_send = (
                flow.request.method.upper() == "POST"
                and path.rstrip("/").endswith("/conversation")
                and "messages" in body
            )
            if is_webui_send:
                try:
                    messages = body.get("messages", [])
                    user_msgs = [
                        m
                        for m in messages
                        if m.get("author", {}).get("role") == "user"
                        or m.get("role") == "user"
                    ]
                    if user_msgs:
                        content = user_msgs[-1].get("content", {})
                        parts = (
                            content.get("parts", [])
                            if isinstance(content, dict)
                            and content.get("content_type") == "text"
                            else []
                        )
                        if parts and isinstance(parts[0], str):
                            self._record(
                                prompt_text=parts[0],
                                llm_name="ChatGPT",
                                model_name=body.get("model", "ChatGPT"),
                                origin=origin,
                                url=flow.request.url,
                                conversation_id=body.get("conversation_id"),
                                metadata={"api_type": "chatgpt_web", "format": "new"},
                                flow=flow,
                            )
                            return
                except Exception as e:
                    logger.error("Error processing ChatGPT Web format: %s", e)

            # Standard chat completions API
            if "messages" in body:
                user_msgs = [m for m in body["messages"] if m.get("role") == "user"]
                if user_msgs:
                    prompt_text: Any = user_msgs[-1].get("content", "")
                    if isinstance(prompt_text, list):
                        prompt_text = " ".join(
                            item.get("text", "")
                            for item in prompt_text
                            if isinstance(item, dict) and item.get("type") == "text"
                        )
                    self._record(
                        prompt_text=str(prompt_text),
                        llm_name="ChatGPT",
                        model_name=body.get("model", "gpt-unknown"),
                        origin=origin,
                        url=flow.request.url,
                        conversation_id=body.get("conversation_id"),
                        metadata={
                            "api_type": "chat_completions",
                            "temperature": body.get("temperature"),
                            "max_tokens": body.get("max_tokens"),
                            "messages_count": len(body["messages"]),
                        },
                        flow=flow,
                    )

            elif "prompt" in body:
                self._record(
                    prompt_text=body["prompt"],
                    llm_name="ChatGPT",
                    model_name=body.get("model", "completions-unknown"),
                    origin=origin,
                    url=flow.request.url,
                    metadata={"api_type": "completions"},
                    flow=flow,
                )
        except Exception as e:
            logger.error("Error processing ChatGPT request: %s", e)

    def _process_claude(self, flow, origin, llm_name="Claude"):
        try:
            text = flow.request.get_text(strict=False)
            if not text:
                return
            body = json.loads(text)

            if "prompt" in body:
                self._record(
                    prompt_text=body["prompt"],
                    llm_name="Claude",
                    model_name=body.get("model", "claude-unknown"),
                    origin=origin,
                    url=flow.request.url,
                    metadata={"api_type": "complete"},
                    flow=flow,
                )
            elif "content" in body or "messages" in body:
                messages = body.get("messages", [])
                if not messages and "content" in body:
                    prompt_text: Any = body["content"]
                    if isinstance(prompt_text, list):
                        prompt_text = " ".join(
                            item.get("text", "")
                            for item in prompt_text
                            if isinstance(item, dict) and item.get("type") == "text"
                        )
                else:
                    user_msgs = [m for m in messages if m.get("role") == "user"]
                    if not user_msgs:
                        return
                    prompt_text = user_msgs[-1].get("content", "")
                    if isinstance(prompt_text, list):
                        prompt_text = " ".join(
                            item.get("text", "")
                            for item in prompt_text
                            if isinstance(item, dict) and item.get("type") == "text"
                        )

                self._record(
                    prompt_text=str(prompt_text),
                    llm_name="Claude",
                    model_name=body.get("model", "claude-unknown"),
                    origin=origin,
                    url=flow.request.url,
                    conversation_id=body.get("conversation_id"),
                    metadata={"api_type": "messages", "messages_count": len(messages) or 1},
                    flow=flow,
                )
        except Exception as e:
            logger.error("Error processing Claude request: %s", e)

    def _process_gemini(self, flow, origin, llm_name="Gemini"):
        """Gemini API (generativelanguage.google... / generateContent)."""
        try:
            text = flow.request.get_text(strict=False)
            if not text:
                return
            body = json.loads(text)

            if "contents" not in body:
                return
            prompt_text = ""
            for content in body["contents"]:
                for part in content.get("parts", []):
                    if "text" in part:
                        prompt_text += part["text"] + " "
            prompt_text = prompt_text.strip()
            if prompt_text:
                self._record(
                    prompt_text=prompt_text,
                    llm_name="Gemini",
                    model_name=body.get("model", "gemini-unknown"),
                    origin=origin,
                    url=flow.request.url,
                    flow=flow,
                )
        except Exception as e:
            logger.error("Error processing Gemini request: %s", e)

    @staticmethod
    def _choose_best_prompt_candidate(strings: list[str], rpcids: list[str] | None = None) -> str:
        def looks_like_internal_token(s: str) -> bool:
            # e.g. ESY5D, PCck7e, aPya6c
            if re.fullmatch(r"[A-Z0-9]{4,10}", s):
                return True
            if re.fullmatch(r"[A-Za-z0-9]{5,10}", s) and "." not in s and " " not in s:
                # short-ish opaque token
                return True
            return False

        def score(s: str) -> tuple[int, int, int]:
            # higher is better
            letters = sum(ch.isalpha() for ch in s)
            digits = sum(ch.isdigit() for ch in s)
            spaces = sum(ch.isspace() for ch in s)

            has_space = 1 if spaces else 0
            has_punct = 1 if any(ch in ".,;:!?()[]{}<>/\\|+-=*~`'\"" for ch in s) else 0
            has_lower = 1 if any(ch.islower() for ch in s) else 0
            token_penalty = 1 if looks_like_internal_token(s) else 0

            # Prefer: human text (spaces/punct), lowercase, more letters; penalize digits + token-like
            return (
                10 * has_space + 3 * has_punct + 2 * has_lower - 20 * token_penalty - digits,
                letters,
                len(s),
            )

        candidates: list[str] = []
        rpcids_set = set(rpcids) if rpcids else set()

        for st in strings:
            if not isinstance(st, str):
                continue
            st = st.strip()
            if not st:
                continue
            
            if st in rpcids_set:
                continue

            # existing “skip noise” logic (keep yours)
            if st.startswith("r_"):
                continue
            if "bard_" in st or "BardChatUi" in st or "boq_" in st:
                continue
            if re.fullmatch(r"[A-Za-z0-9_\-]{20,}", st):
                continue
            if re.fullmatch(r"[0-9a-fA-F]{16,}", st):
                continue
            if len(st) >= 16 and re.fullmatch(r"[A-Za-z0-9_\-]{16,}", st):
                continue
            if st.lower() in {"bard_activity_enabled", "generic"}:
                continue
            if re.match(r"^https?://", st):
                continue
            if st.startswith("!") and len(st) > 20:
                continue
            if st in ("generic", "en", "en-US", "auto", "chat"):
                continue

            candidates.append(st)

        if not candidates:
            return ""

        # Pick the “most human” string, not the first one
        return max(candidates, key=score)

    def _process_bard(self, flow, origin, llm_name="Gemini"):
        """
        Gemini Web UI (legacy Bard endpoints):
          - /_/BardChatUi/data/batchexecute    (often returns reqid r_e...)
          - /_/BardChatUi/data/assistant.l...  (often returns the actual model output)
        """
        try:
            # If this is the follow-up call carrying the reqid, DON'T record a prompt.
            # Instead, attach the upcoming response to the original prompt id.
            path = urlparse(flow.request.pretty_url).path or ""
            if "assistant.l" in path:
                # Look for reqid in body, form, or URL
                reqid = ""
                if flow.request.content:
                    raw = flow.request.get_text(strict=False) or ""
                    reqid = self._find_reqid(raw)
                if not reqid:
                    reqid = self._find_reqid(flow.request.pretty_url)
                if reqid and reqid in self._gemini_reqid_to_prompt:
                    prompt_id = self._gemini_reqid_to_prompt.pop(reqid, None)
                    if prompt_id:
                        self._pending_responses[flow.id] = (prompt_id, "Gemini")
                        logger.info(
                            "Gemini assistant.l correlated reqid %s -> prompt %s",
                            reqid,
                            prompt_id,
                        )
                        return
                # If we can't correlate, fall through (best-effort prompt capture below),
                # but this may create garbage prompts; correlation is preferred.

            text = flow.request.get_text(strict=False)
            if not text:
                return

            prompt_text = ""
            
            # NEW: Extract the RPC IDs from the URL query
            rpcids = flow.request.query.get("rpcids", "").split(",")

            # Gemini's obscure URL-encoded RPC format
            if "application/x-www-form-urlencoded" in flow.request.headers.get("Content-Type", ""):
                form_data = flow.request.urlencoded_form
                payload = ""
                for field in ("f.req", "prompt", "message", "q"):
                    if field in form_data:
                        payload = form_data[field]
                        break
                
                # Best: parse f.req as JSON and harvest strings
                if payload:
                    harvested: list[str] = []
                    try:
                        outer = json.loads(payload)
                        self._collect_leaf_strings(outer, harvested)
                    except Exception:
                        # Fallback: extract quoted strings
                        matches = re.findall(r'"((?:[^"\\]|\\.)*)"', payload)
                        for m in matches:
                            try:
                                harvested.append(json.loads(f'"{m}"'))
                            except Exception:
                                harvested.append(m)
                    
                    # NEW: Pass rpcids down
                    prompt_text = self._choose_best_prompt_candidate(harvested, rpcids)
            else:
                # Standard JSON request formats (rare for web UI)
                harvested2: list[str] = []
                try:
                    outer2 = json.loads(text)
                    self._collect_leaf_strings(outer2, harvested2)
                except Exception:
                    # Fallback: extract quoted strings
                    matches = re.findall(r'"((?:[^"\\]|\\.)*)"', text)
                    for m in matches:
                        try:
                            harvested2.append(json.loads(f'"{m}"'))
                        except Exception:
                            harvested2.append(m)
                
                # NEW: Pass rpcids down
                prompt_text = self._choose_best_prompt_candidate(harvested2, rpcids)

            if prompt_text:
                self._record(
                    prompt_text=prompt_text,
                    llm_name="Gemini",
                    model_name="gemini-web",
                    origin=origin,
                    url=flow.request.url,
                    flow=flow,
                )

        except Exception as e:
            logger.error("Error processing Gemini request: %s", e)

    def _process_perplexity(self, flow, origin, llm_name="Perplexity"):
        try:
            text = flow.request.get_text(strict=False)
            if not text:
                return
            body = json.loads(text)
            prompt_text = None

            for key in ("text", "prompt", "query"):
                if key in body:
                    prompt_text = body[key]
                    break

            if prompt_text is None and ("message" in body or "messages" in body):
                messages = body.get("messages", [body["message"]] if "message" in body else [])
                user_msgs = [m for m in messages if m.get("role") == "user"]
                if user_msgs:
                    prompt_text = user_msgs[-1].get("content", "")

            if prompt_text:
                self._record(
                    prompt_text=prompt_text,
                    llm_name="Perplexity",
                    model_name=body.get("model", "perplexity-unknown"),
                    origin=origin,
                    url=flow.request.url,
                    flow=flow,
                )
        except Exception as e:
            logger.error("Error processing Perplexity request: %s", e)

    def _process_openai_compat(self, flow, origin, llm_name="Unknown"):
        """Shared request processor for OpenAI-compatible providers."""
        try:
            text = flow.request.get_text(strict=False)
            if not text:
                return
            body = json.loads(text)
            prompt_text = self._extract_openai_messages(body)
            if not prompt_text:
                prompt_text = body.get("prompt", "")
            if prompt_text:
                self._record(
                    prompt_text=prompt_text,
                    llm_name=llm_name,
                    model_name=body.get("model", f"{llm_name.lower()}-unknown"),
                    origin=origin,
                    url=flow.request.url,
                    conversation_id=body.get("conversation_id"),
                    metadata={
                        "api_type": "openai_compat",
                        "temperature": body.get("temperature"),
                        "max_tokens": body.get("max_tokens"),
                    },
                    flow=flow,
                )
        except Exception as e:
            logger.error("Error processing %s request: %s", llm_name, e)

    @staticmethod
    def _extract_openai_messages(body: dict) -> str:
        """Extract the last user message from an OpenAI-style messages[] array."""
        messages = body.get("messages", [])
        user_msgs = [m for m in messages if m.get("role") == "user"]
        if not user_msgs:
            return ""
        content = user_msgs[-1].get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            )
        return str(content) if content else ""

    def _process_generic(self, flow, origin, llm_name=None):
        try:
            text = flow.request.get_text(strict=False)
            if not text:
                return
            body = json.loads(text)

            if llm_name is None:
                llm_name = "Unknown LLM"
                for domain, name in _DOMAIN_NAMES.items():
                    if domain in origin:
                        llm_name = name
                        break

            prompt_text = None
            if "prompt" in body:
                prompt_text = body["prompt"]
            elif "messages" in body:
                user_msgs = [m for m in body["messages"] if m.get("role") == "user"]
                if user_msgs:
                    prompt_text = user_msgs[-1].get("content", "")
            elif "inputs" in body:
                prompt_text = body["inputs"]

            if prompt_text:
                self._record(
                    prompt_text=prompt_text,
                    llm_name=llm_name,
                    model_name=body.get("model", "unknown"),
                    origin=origin,
                    url=flow.request.url,
                    flow=flow,
                )
        except Exception as e:
            logger.error("Error processing generic LLM request: %s", e)

    # ------------------------------------------------------------------
    # Recording helper
    # ------------------------------------------------------------------

    def _record(
        self,
        prompt_text,
        llm_name,
        origin,
        url,
        model_name=None,
        conversation_id=None,
        metadata=None,
        flow=None,
    ):
        prompt_id = self.db.add_prompt(
            prompt_text=prompt_text,
            llm_name=llm_name,
            source="Proxy Recorder",
            model_name=model_name,
            description=f"{llm_name} prompt via {origin}",
            url=url,
            conversation_id=conversation_id or f"{llm_name.lower()}-{datetime.now().timestamp()}",
            metadata=metadata,
            associated_files=self.active_files,
        )
        self._latest_chatgpt_prompt_id = prompt_id
        logger.info("Recorded %s prompt: %s", llm_name, prompt_id)
        # Track flow for response pairing — store llm_name so the response parser can use format-specific extraction.
        if flow is not None:
            self._pending_responses[flow.id] = (prompt_id, llm_name)

    # ------------------------------------------------------------------
    # Active files management
    # ------------------------------------------------------------------

    def set_active_files(self, files):
        self.active_files = files
        logger.info("Set %d active files for auto-association", len(files))

    def clear_active_files(self):
        self.active_files = []
        logger.info("Cleared active files")


# ------------------------------------------------------------------
# URL pattern constants
# ------------------------------------------------------------------

_CHATGPT_PATTERNS = [
    # OpenAI API
    r"api\.openai\.com/v1/chat/completions(?:\?.*)?$",
    r"api\.openai\.com/v1/engines/[^/]+/completions(?:\?.*)?$",
    r"api\.openai\.com/v1/completions(?:\?.*)?$",

    # ChatGPT Web UI (send endpoint; anchored so it won't match /prepare)
    r"chat\.openai\.com/backend-api/f/conversation/?(?:\?.*)?$",
    r"chatgpt\.com/backend-api/f/conversation/?(?:\?.*)?$",
    r"chatgpt\.com/backend-api/f/conversation(?!/)",  # allow query params but not extra path segments

    # (Optional) older/alternate domains/paths, also anchored
    r"chat\.openai\.com/backend-api/conversation/?(?:\?.*)?$",
    r"chatgpt\.com/backend-api/conversation/?(?:\?.*)?$",
]

_CLAUDE_PATTERNS = [
    r"api\.anthropic\.com/v1/messages",
    r"api\.anthropic\.com/v1/complete",
    r"claude\.ai/api/.*?/messages",
    r"claude\.ai/api/.*?/completion",
    r"claude\.ai/api/append_message",
]

_GEMINI_PATTERNS = [
    r"generativelanguage\.googleapis\.com",
    r"gemini\.google\.com/api",
    r"generativeai\.google\.com/api",
    r"generativeai\.googleapis\.com",
]

_BARD_PATTERNS = [
    r"bard\.google\.com/api",
    r"bard\.google\.com/_/BardChatUi/data",
    r"gemini\.google\.com/_/BardChatUi/data",
]

_PERPLEXITY_PATTERNS = [
    r"api\.perplexity\.ai",
    r"perplexity\.ai/api",
]

_GENERIC_PATTERNS = [
    r"api\.mistral\.ai",
    r"api\.cohere\.ai",
    r"api\.together\.xyz",
    r"api\.groq\.com",
    r"api\.deepinfra\.com",
]

_GROK_PATTERNS = [
    r"api\.x\.ai/v1/chat/completions",
    r"api\.x\.ai/v1/completions",
    r"grok\.com/rest/app-chat/conversations",
]

_DEEPSEEK_PATTERNS = [
    r"api\.deepseek\.com/v1/chat/completions",
    r"api\.deepseek\.com/v1/completions",
    r"chat\.deepseek\.com/api/",
]

_OPENROUTER_PATTERNS = [
    r"openrouter\.ai/api/v1/chat/completions",
    r"openrouter\.ai/api/v1/completions",
]

_LECHAT_PATTERNS = [
    r"chat\.mistral\.ai/api/chat",
]

_HUGGINGCHAT_PATTERNS = [
    r"huggingface\.co/chat/conversation",
]

_META_AI_PATTERNS = [
    r"meta\.ai/api",
    r"www\.meta\.ai/api",
]

_COPILOT_PATTERNS = [
    r"copilot\.microsoft\.com/c/api",
    r"copilot\.microsoft\.com/api",
    r"sydney\.bing\.com/sydney",
]

_YOUCOM_PATTERNS = [
    r"you\.com/api/streamingSearch",
    r"you\.com/api/chat",
]

_PHIND_PATTERNS = [
    r"phind\.com/api",
    r"www\.phind\.com/api",
]

_DOMAIN_NAMES = {
    "mistral.ai": "Mistral AI",
    "cohere.ai": "Cohere",
    "together.xyz": "Together AI",
    "groq.com": "Groq",
    "deepinfra.com": "DeepInfra",
    "x.ai": "Grok",
    "grok.com": "Grok",
    "deepseek.com": "DeepSeek",
    "openrouter.ai": "OpenRouter",
    "chat.mistral.ai": "Le Chat",
    "huggingface.co": "HuggingChat",
    "meta.ai": "Meta AI",
    "copilot.microsoft.com": "Copilot",
    "sydney.bing.com": "Copilot",
    "you.com": "You.com",
    "phind.com": "Phind",
}

# Table-driven request dispatch: (patterns, method_name, llm_name)
# Order matters — more specific patterns first.
# llm_name=None means _process_generic will do domain lookup.
_REQUEST_DISPATCH = [
    (_CHATGPT_PATTERNS, "_process_chatgpt", "ChatGPT"),
    (_CLAUDE_PATTERNS, "_process_claude", "Claude"),
    (_GEMINI_PATTERNS, "_process_gemini", "Gemini"),
    (_BARD_PATTERNS, "_process_bard", "Gemini"),
    (_PERPLEXITY_PATTERNS, "_process_perplexity", "Perplexity"),
    (_GROK_PATTERNS, "_process_openai_compat", "Grok"),
    (_DEEPSEEK_PATTERNS, "_process_openai_compat", "DeepSeek"),
    (_OPENROUTER_PATTERNS, "_process_openai_compat", "OpenRouter"),
    (_LECHAT_PATTERNS, "_process_openai_compat", "Le Chat"),
    (_HUGGINGCHAT_PATTERNS, "_process_openai_compat", "HuggingChat"),
    (_META_AI_PATTERNS, "_process_generic", "Meta AI"),
    (_COPILOT_PATTERNS, "_process_generic", "Copilot"),
    (_YOUCOM_PATTERNS, "_process_generic", "You.com"),
    (_PHIND_PATTERNS, "_process_generic", "Phind"),
    (_GENERIC_PATTERNS, "_process_generic", None),
]

# Response parser routing: llm_name -> parser method.
# Missing keys fall through to _parse_generic_response.
_RESPONSE_PARSER = {
    "ChatGPT": "_parse_chatgpt_response",
    "Claude": "_parse_claude_response",
    "Gemini": "_parse_gemini_response",
    "DeepSeek": "_parse_deepseek_response",
    # OpenAI-compatible providers share ChatGPT's parser
    "Grok": "_parse_chatgpt_response",
    "OpenRouter": "_parse_chatgpt_response",
    "Le Chat": "_parse_chatgpt_response",
    "HuggingChat": "_parse_chatgpt_response",
    "Perplexity": "_parse_chatgpt_response",
}

# ------------------------------------------------------------------
# mitmproxy addon API
# ------------------------------------------------------------------

recorder = LLMPromptRecorder()
addons = [recorder]


def set_active_files(files):
    recorder.set_active_files(files)


def clear_active_files():
    recorder.clear_active_files()