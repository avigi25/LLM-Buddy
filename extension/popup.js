/**
 * LLM Buddy - Popup Script
 */

const statusEl = document.getElementById("status");
const countEl = document.getElementById("count");
const serverCountEl = document.getElementById("serverCount");
const urlInput = document.getElementById("serverUrl");
const saveBtn = document.getElementById("saveBtn");
const resetBtn = document.getElementById("resetBtn");

// Load saved settings
chrome.storage.local.get(["serverUrl", "promptCount"], (result) => {
  if (result.serverUrl) urlInput.value = result.serverUrl;
  countEl.textContent = result.promptCount || 0;
  checkConnection();
});

// Check connection to server
async function checkConnection() {
  try {
    const resp = await chrome.runtime.sendMessage({ type: "CHECK_SERVER" });
    if (resp && resp.connected) {
      statusEl.className = "status connected";
      statusEl.textContent = "Connected to LLM Buddy";
      if (resp.data && resp.data.prompt_count !== undefined) {
        serverCountEl.textContent = resp.data.prompt_count;
      }
    } else {
      statusEl.className = "status disconnected";
      statusEl.textContent =
        "Not connected — start the server in LLM Buddy";
    }
  } catch {
    statusEl.className = "status disconnected";
    statusEl.textContent = "Not connected — start the server in LLM Buddy";
  }
}

// Save settings
saveBtn.addEventListener("click", () => {
  const url = urlInput.value.trim().replace(/\/$/, "");
  chrome.storage.local.set({ serverUrl: url }, () => {
    checkConnection();
  });
});

// Reset count
resetBtn.addEventListener("click", () => {
  chrome.storage.local.set({ promptCount: 0 }, () => {
    countEl.textContent = "0";
    chrome.action.setBadgeText({ text: "" });
  });
});
