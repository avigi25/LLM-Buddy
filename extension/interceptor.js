(function() {
  const originalFetch = window.fetch;

  function isLLMEndpoint(url) {
    const patterns = [
      /backend-api\/conversation/,          // ChatGPT
      /backend-api\/f\/conversation/,       // ChatGPT (alternate)
      /api\/chat/,                          // Generic chat API
      /api\/append_message/,                // Claude web UI
      /chat_conversations\/.*\/completion/, // Claude web UI
      /GenerateContent/,                    // Gemini
      /completions/,                        // OpenAI API
      /messages/,                           // Anthropic API
      /rest\/app-chat\/conversations/,      // Grok
      /chat\.deepseek\.com\/api/,           // DeepSeek
      /chat\.mistral\.ai\/api/,             // Le Chat
      /huggingface\.co\/chat/,              // HuggingChat
      /copilot\.microsoft\.com.*api/,       // Copilot
      /you\.com\/api/,                      // You.com
      /phind\.com\/api/,                    // Phind
      /meta\.ai\/api/,                      // Meta AI
      /gemini\.google\.com.*\/f\//,         // Gemini web UI
      /perplexity\.ai\/api/,               // Perplexity
    ];
    return patterns.some(p => p.test(url));
  }

  function extractPromptFromBody(body) {
    if (body.messages) {
      const userMsgs = body.messages.filter(m => m.role === "user" || m.author?.role === "user");
      if (userMsgs.length > 0) {
        const last = userMsgs[userMsgs.length - 1];
        const content = last.content || last;
        if (typeof content === "string") return content;
        // ChatGPT Web UI: content.parts may contain mixed strings and objects
        if (content.parts) {
          const textParts = content.parts.filter(p => typeof p === "string");
          return textParts.join(" ");
        }
        if (content.text) return content.text;
      }
    }
    if (body.prompt) return body.prompt;
    if (body.text) return body.text;
    if (body.query) return body.query;
    if (body.contents) {
      const parts = body.contents.flatMap(c => c.parts || []).filter(p => p.text).map(p => p.text);
      if (parts.length) return parts.join(" ");
    }
    return null;
  }

  function extractAttachmentsFromBody(body) {
    const attachments = [];

    if (body.messages) {
      const userMsgs = body.messages.filter(m => m.role === "user" || m.author?.role === "user");
      if (userMsgs.length > 0) {
        const last = userMsgs[userMsgs.length - 1];
        const content = last.content || last;

        // OpenAI/Claude-style content array
        if (Array.isArray(content)) {
          for (const item of content) {
            if (item.type === "image_url") {
              const url = item.image_url?.url || "";
              attachments.push({
                type: "image",
                source: url.startsWith("data:") ? "base64" : "url",
                mediaType: url.startsWith("data:") ? url.split(";")[0].replace("data:", "") : null,
              });
            } else if (item.type === "image") {
              attachments.push({
                type: "image",
                mediaType: item.source?.media_type || null,
                source: item.source?.type || "unknown",
              });
            } else if (item.type === "document") {
              attachments.push({
                type: "document",
                mediaType: item.source?.media_type || null,
                source: item.source?.type || "unknown",
                name: item.name || null,
              });
            }
          }
        }

        // ChatGPT Web UI multimodal parts
        if (content?.parts && Array.isArray(content.parts)) {
          for (const part of content.parts) {
            if (typeof part === "object" && part !== null) {
              const ct = part.content_type || "";
              if (ct === "image_asset_pointer") {
                attachments.push({ type: "image", source: "chatgpt_asset" });
              } else if (ct.includes("file") || ct.includes("document")) {
                attachments.push({ type: "document", source: "chatgpt_asset", name: part.name || null });
              }
            }
          }
        }
      }
    }

    // Gemini format
    if (body.contents) {
      for (const c of body.contents) {
        for (const part of (c.parts || [])) {
          if (part.inline_data) {
            attachments.push({
              type: part.inline_data.mime_type?.startsWith("image/") ? "image" : "document",
              mediaType: part.inline_data.mime_type,
              source: "inline_base64",
            });
          } else if (part.file_data) {
            attachments.push({
              type: "document",
              mediaType: part.file_data.mime_type,
              source: "file_uri",
            });
          }
        }
      }
    }

    return attachments.length > 0 ? attachments : null;
  }

  window.fetch = async function(...args) {
    const [resource, config] = args;
    const url = typeof resource === "string" ? resource : resource?.url || "";

    let needsConvIdFromResponse = false;

    if (config?.method === "POST" && config?.body && isLLMEndpoint(url)) {
      try {
        const body = typeof config.body === "string" ? JSON.parse(config.body) : config.body;
        const prompt = extractPromptFromBody(body);
        const attachments = extractAttachmentsFromBody(body);
        // Extract conversation metadata from request body if available
        const conversationId = body.conversation_id || body.conversationId || null;
        const parentMessageId = body.parent_message_id
          || body.parent_message_uuid  // Claude web UI
          || null;
        // Count messages from various API formats
        const messagesCount = body.messages ? body.messages.length
          : body.contents ? body.contents.length
          : null;
        if (prompt || attachments) {
          window.dispatchEvent(new CustomEvent("LLMBuddy_Capture", {
            detail: {
              text: prompt,
              attachments: attachments,
              conversationId: conversationId,
              parentMessageId: parentMessageId,
              messagesCount: messagesCount,
            }
          }));
          // If no conversation_id in request, try to extract from response
          if (!conversationId) {
            needsConvIdFromResponse = true;
          }
        }
      } catch (e) {
        // Ignore parse errors safely
      }
    }

    const response = originalFetch.apply(this, args);

    // For first messages (no conversation_id in request), read the first
    // chunk of the SSE response to extract the conversation_id.
    if (needsConvIdFromResponse) {
      response.then(function(resp) {
        try {
          const clone = resp.clone();
          const reader = clone.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          function readChunk() {
            reader.read().then(function(result) {
              if (result.done) return;
              buffer += decoder.decode(result.value, {stream: true});
              const match = buffer.match(/"conversation_id"\s*:\s*"([^"]+)"/);
              if (match) {
                reader.cancel().catch(function(){});
                window.dispatchEvent(new CustomEvent("LLMBuddy_ConvIdUpdate", {
                  detail: { conversationId: match[1] }
                }));
                return;
              }
              // Read up to 20KB to find the conversation_id
              if (buffer.length < 20000) readChunk();
              else reader.cancel().catch(function(){});
            }).catch(function(){});
          }
          readChunk();
        } catch (e) {
          // Ignore errors — this is a best-effort enhancement
        }
      }).catch(function(){});
    }

    return response;
  };
})();
