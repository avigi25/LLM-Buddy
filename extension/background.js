/**
 * LLM Buddy - Background Service Worker
 * Receives prompts from content scripts and sends them to the Flask API.
 */

const DEFAULT_SERVER = "http://localhost:5000";

// Get the configured server URL
async function getServerUrl() {
  const result = await chrome.storage.local.get(["serverUrl"]);
  return result.serverUrl || DEFAULT_SERVER;
}

// Send a prompt to the LLM Buddy server
async function sendPrompt(data) {
  const serverUrl = await getServerUrl();
  try {
    const response = await fetch(`${serverUrl}/record_prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (response.ok) {
      const result = await response.json();
      // Update badge to show it's working
      chrome.action.setBadgeBackgroundColor({ color: "#4CAF50" });
      const countResult = await chrome.storage.local.get(["promptCount"]);
      const count = (countResult.promptCount || 0) + 1;
      await chrome.storage.local.set({ promptCount: count });
      chrome.action.setBadgeText({ text: String(count) });
      return result;
    } else {
      console.error("LLM Buddy: Server error", response.status);
      chrome.action.setBadgeBackgroundColor({ color: "#F44336" });
      chrome.action.setBadgeText({ text: "!" });
    }
  } catch (err) {
    console.error("LLM Buddy: Could not reach server", err.message);
    chrome.action.setBadgeBackgroundColor({ color: "#F44336" });
    chrome.action.setBadgeText({ text: "!" });
  }
  return null;
}

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "PROMPT_CAPTURED") {
    sendPrompt(message.data).then((result) => {
      sendResponse({ success: !!result, result });
    });
    return true; // async response
  }

  if (message.type === "RESPONSE_CAPTURED") {
    sendResponse({ success: true }); // ack immediately
    updateResponse(message.data);    // fire-and-forget
    return false;
  }

  if (message.type === "CHECK_SERVER") {
    getServerUrl().then(async (url) => {
      try {
        const resp = await fetch(`${url}/ping`);
        const data = await resp.json();
        sendResponse({ connected: true, data });
      } catch {
        sendResponse({ connected: false });
      }
    });
    return true;
  }
});

// Send a response update to the LLM Buddy server
async function updateResponse(data) {
  const serverUrl = await getServerUrl();
  try {
    const response = await fetch(`${serverUrl}/update_response`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt_id: data.promptId,
        response_text: data.responseText,
      }),
    });
    if (response.ok) {
      console.log("LLM Buddy: response saved for prompt", data.promptId);
    } else {
      console.error("LLM Buddy: failed to save response", response.status);
    }
  } catch (err) {
    console.error("LLM Buddy: could not send response", err.message);
  }
}

// Clear badge and inject content scripts into already-open tabs on install/update
chrome.runtime.onInstalled.addListener(() => {
  // Reset prompt count
  chrome.storage.local.set({ promptCount: 0 });
  chrome.action.setBadgeText({ text: "" });

  // Get the matching URLs and scripts directly from the manifest
  const manifest = chrome.runtime.getManifest();
  const contentScripts = manifest.content_scripts[0];

  // Query all open tabs that match the LLM websites
  chrome.tabs.query({ url: contentScripts.matches }, (tabs) => {
    if (!tabs) return;
    
    // Inject the content script into each matching tab
    for (const tab of tabs) {
      // Ignore chrome:// or other restricted URLs just to be safe
      if (tab.url.startsWith("chrome://") || tab.url.startsWith("edge://")) continue;
      
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: contentScripts.js
      }).catch(err => {
        console.warn(`LLM Buddy: Could not inject into tab ${tab.id}`, err);
      });
    }
  });
});