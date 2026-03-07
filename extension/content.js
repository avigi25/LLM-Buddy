/**
 * LLM Buddy - Content Script
 * Captures prompts AND responses from LLM websites.
 *
 * Supported sites:
 * - ChatGPT  (chatgpt.com, chat.openai.com)
 * - Claude   (claude.ai)
 * - Gemini   (gemini.google.com)
 * - Perplexity (perplexity.ai)
 * - Grok     (grok.com)
 * - DeepSeek (chat.deepseek.com)
 * - Le Chat  (chat.mistral.ai)
 * - HuggingChat (huggingface.co/chat)
 * - Meta AI  (meta.ai)
 * - Copilot  (copilot.microsoft.com)
 * - You.com  (you.com)
 * - Phind    (phind.com)
 */

(function () {
  "use strict";

  // Prevent double-injection
  if (window.__llmBuddyInjected) return;
  window.__llmBuddyInjected = true;

  const SITE = detectSite();
  if (!SITE) return;

  let lastPrompt = "";
  let debounceTimer = null;
  let lastPromptId = null; 

  console.log(`LLM Buddy: monitoring ${SITE} for prompts and responses`);

  // --- Site detection ---
  function detectSite() {
    const host = location.hostname;
    if (host.includes("chatgpt.com") || host.includes("chat.openai.com")) return "ChatGPT";
    if (host.includes("claude.ai")) return "Claude";
    if (host.includes("gemini.google.com")) return "Gemini";
    if (host.includes("perplexity.ai")) return "Perplexity";
    if (host.includes("grok.com")) return "Grok";
    if (host.includes("chat.deepseek.com")) return "DeepSeek";
    if (host.includes("chat.mistral.ai")) return "Le Chat";
    if (host.includes("huggingface.co") && location.pathname.startsWith("/chat")) return "HuggingChat";
    if (host.includes("meta.ai")) return "Meta AI";
    if (host.includes("copilot.microsoft.com")) return "Copilot";
    if (host.includes("you.com")) return "You.com";
    if (host.includes("phind.com")) return "Phind";
    return null;
  }

  // --- Prompt extraction ---
  function getPromptText() {
    let text = "";

    if (SITE === "ChatGPT") {
      const el =
        document.querySelector("#prompt-textarea") ||
        document.querySelector('textarea[data-id="root"]') ||
        document.querySelector("textarea") ||
        document.querySelector('[contenteditable="true"]');
      if (el) text = el.innerText || el.value || "";
    }

    if (SITE === "Claude") {
      const el =
        document.querySelector('[contenteditable="true"].ProseMirror') ||
        document.querySelector('[contenteditable="true"]') ||
        document.querySelector("textarea");
      if (el) text = el.innerText || el.value || "";
    }

    if (SITE === "Gemini") {
      const el =
        document.querySelector(".ql-editor") ||
        document.querySelector('[contenteditable="true"]') ||
        document.querySelector("textarea");
      if (el) text = el.innerText || el.value || "";
    }

    if (SITE === "Perplexity") {
      const el =
        document.querySelector("textarea") ||
        document.querySelector('[contenteditable="true"]');
      if (el) text = el.innerText || el.value || "";
    }

    // Generic fallback for Grok, DeepSeek, Le Chat, HuggingChat,
    // Meta AI, Copilot, You.com, Phind, and any future providers
    if (!text) {
      const el =
        document.querySelector('[role="textbox"]') ||
        document.querySelector("textarea") ||
        document.querySelector('[contenteditable="true"]');
      if (el) text = el.innerText || el.value || "";
    }

    return text.trim();
  }

  // --- Response extraction from DOM ---
  function getLastAssistantMessage() {
    let el = null;

    if (SITE === "ChatGPT") {
      const msgs = document.querySelectorAll(
        '[data-message-author-role="assistant"], [data-message-author="assistant"], .agent-turn'
      );
      if (msgs.length > 0) {
        el = msgs[msgs.length - 1];
        const md = el.querySelector(".markdown, .prose");
        if (md) el = md;
      }
    }

    if (SITE === "Claude") {
      const msgs = document.querySelectorAll(
        '[class*="font-claude-message"], [data-is-streaming], .claude-message'
      );
      if (msgs.length > 0) el = msgs[msgs.length - 1];
      
      if (!el) {
        const containers = document.querySelectorAll('[class*="response"], [class*="message-content"], .grid-cols-1');
        if (containers.length > 0) el = containers[containers.length - 1];
      }
    }

    if (SITE === "Gemini") {
      const msgs = document.querySelectorAll(
        "model-response, [class*=\"model-response\"], message-content"
      );
      if (msgs.length > 0) el = msgs[msgs.length - 1];
    }

    if (SITE === "Perplexity") {
      const msgs = document.querySelectorAll(
        '[class*="prose"], [class*="answer"], [class*="response-text"], .break-words'
      );
      if (msgs.length > 0) el = msgs[msgs.length - 1];
    }

    // Generic fallback for new providers — look for common response
    // container patterns used by Grok, DeepSeek, Le Chat, HuggingChat,
    // Meta AI, Copilot, You.com, Phind
    if (!el) {
      const selectors = [
        '[class*="assistant"]',
        '[class*="response"]',
        '[class*="answer"]',
        '[class*="message-content"]',
        '[class*="prose"]',
        '[class*="markdown"]',
        '[data-role="assistant"]',
        '[data-message-author="assistant"]',
      ];
      const msgs = document.querySelectorAll(selectors.join(", "));
      if (msgs.length > 0) el = msgs[msgs.length - 1];
    }

    return el ? el.innerText.trim() : "";
  }

  // --- Send prompt to background ---
  // --- Send prompt to background ---
  function capturePrompt(text) {
    if (!text || text.length < 2) return;
    if (text === lastPrompt) return;
    lastPrompt = text;

    console.log(`LLM Buddy: captured ${SITE} prompt (${text.length} chars)`);

    try {
      chrome.runtime.sendMessage(
        {
          type: "PROMPT_CAPTURED",
          data: {
            llmName: SITE,
            promptText: text,
            url: location.href,
            pageTitle: document.title,
            modelName: SITE,
          },
        },
        (response) => {
          if (chrome.runtime.lastError) {
             console.warn("LLM Buddy: Extension context invalidated. Please refresh the page.");
             return;
          }
          if (response && response.result && response.result.prompt_id) {
            lastPromptId = response.result.prompt_id;
            watchForResponse(lastPromptId);
          }
        }
      );
    } catch (e) {
      if (e.message.includes("Extension context invalidated")) {
        console.warn("LLM Buddy: Extension context invalidated. Please refresh the page.");
      } else {
        console.error("LLM Buddy error:", e);
      }
    }
  }

  // --- Watch for LLM response after prompt submission ---
  // --- Watch for LLM response after prompt submission ---
  function watchForResponse(promptId) {
    let lastContent = "";
    let stableCount = 0;
    let checkCount = 0;
    const MAX_CHECKS = 180; // 3 minutes max (180 * 1s)
    const STABLE_THRESHOLD = 3; // Content must be stable for 3 seconds

    const checker = setInterval(() => {
      checkCount++;
      const currentContent = getLastAssistantMessage();

      if (currentContent && currentContent.length > 0 && currentContent === lastContent) {
        stableCount++;
        if (stableCount >= STABLE_THRESHOLD) {
          clearInterval(checker);
          console.log(`LLM Buddy: captured ${SITE} response (${currentContent.length} chars)`);
          
          try {
            chrome.runtime.sendMessage({
              type: "RESPONSE_CAPTURED",
              data: {
                promptId: promptId,
                responseText: currentContent,
              },
            }, () => {
              // Catch errors silently if the background script is gone
              if (chrome.runtime.lastError) {
                console.warn("LLM Buddy: Extension context invalidated. Please refresh the page.");
              }
            });
          } catch (e) {
            if (e.message.includes("Extension context invalidated")) {
              console.warn("LLM Buddy: Extension context invalidated. Please refresh the page.");
            } else {
              console.error("LLM Buddy error:", e);
            }
          }
        }
      } else {
        stableCount = 0;
        lastContent = currentContent;
      }

      if (checkCount >= MAX_CHECKS) {
        clearInterval(checker);
        if (lastContent && lastContent.length > 10) {
          console.log(`LLM Buddy: response timeout, saving partial (${lastContent.length} chars)`);
          
          try {
            chrome.runtime.sendMessage({
              type: "RESPONSE_CAPTURED",
              data: {
                promptId: promptId,
                responseText: lastContent,
              },
            }, () => {
              // Catch errors silently if the background script is gone
              if (chrome.runtime.lastError) {
                console.warn("LLM Buddy: Extension context invalidated. Please refresh the page.");
              }
            });
          } catch (e) {
            if (e.message.includes("Extension context invalidated")) {
              console.warn("LLM Buddy: Extension context invalidated. Please refresh the page.");
            } else {
              console.error("LLM Buddy error:", e);
            }
          }
        }
      }
    }, 1000);
  }

  // --- Detect submissions ---

  // Method 1: Watch for Enter key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      const text = getPromptText();
      if (text) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => capturePrompt(text), 100);
      }
    }
  }, true);

  // Method 2: Watch for send button clicks
  function setupButtonWatcher() {
    document.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;

      const isSend =
        btn.getAttribute("data-testid") === "send-button" ||
        btn.getAttribute("aria-label")?.toLowerCase().includes("send") ||
        btn.querySelector('svg path[d*="M2"]') ||
        btn.classList.toString().toLowerCase().includes("send");

      if (isSend) {
        const text = getPromptText();
        if (text) {
          clearTimeout(debounceTimer);
          debounceTimer = setTimeout(() => capturePrompt(text), 100);
        }
      }
    }, true);
  }

  // Method 3: Injected fetch interceptor using CustomEvent bridge
  // Inject the script as a file to comply with CSP restrictions
  const script = document.createElement("script");
  script.src = chrome.runtime.getURL("interceptor.js");
  (document.head || document.documentElement).appendChild(script);
  
  // Clean up the script tag after it executes
  script.onload = function() {
    this.remove();
  };

  // Listen for messages bridged from the injected script
  window.addEventListener("LLMBuddy_Capture", (e) => {
    const text = e.detail;
    if (text) {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => capturePrompt(text), 50);
    }
  });

  // Initialize
  setupButtonWatcher();

})();