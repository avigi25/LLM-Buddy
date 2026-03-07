(function() {
  const originalFetch = window.fetch;

  function isLLMEndpoint(url) {
    const patterns = [
      /backend-api\/conversation/,
      /api\/chat/,
      /api\/append_message/,
      /GenerateContent/,
      /completions/,
      /messages/,
      /rest\/app-chat\/conversations/,   // Grok
      /chat\.deepseek\.com\/api/,         // DeepSeek
      /chat\.mistral\.ai\/api/,           // Le Chat
      /huggingface\.co\/chat/,            // HuggingChat
      /copilot\.microsoft\.com.*api/,     // Copilot
      /you\.com\/api/,                    // You.com
      /phind\.com\/api/,                  // Phind
      /meta\.ai\/api/,                    // Meta AI
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
        if (content.parts) return content.parts.join(" ");
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

  window.fetch = async function(...args) {
    const [resource, config] = args;
    const url = typeof resource === "string" ? resource : resource?.url || "";

    if (config?.method === "POST" && config?.body && isLLMEndpoint(url)) {
      try {
        const body = typeof config.body === "string" ? JSON.parse(config.body) : config.body;
        const prompt = extractPromptFromBody(body);
        if (prompt) {
          window.dispatchEvent(new CustomEvent("LLMBuddy_Capture", { detail: prompt }));
        }
      } catch (e) {
        // Ignore parse errors safely
      }
    }
    return originalFetch.apply(this, args);
  };
})();