// ElevenLabs Content Script: 负责注入执行环境脚本并中转消息
(function() {
  console.log("ElevenLabs Tool: Content script bridge loaded.");

  // 1. 注入 injectFetch.js 到页面 Context
  try {
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('elevenlabs/injectFetch.js');
    (document.head || document.documentElement).appendChild(script);
    script.onload = () => script.remove();
  } catch (e) {
    console.error("ElevenLabs Tool: Failed to inject fetch hook", e);
  }

  // 2. 监听来自 injectFetch.js 的 window.postMessage
  window.addEventListener("message", (event) => {
    // 只处理来自本页面的消息
    if (event.source !== window || !event.data) return;

    // 检查扩展上下文是否有效
    try {
      if (typeof chrome === "undefined" || !chrome.runtime || !chrome.runtime.id) {
        return; // 上下文已失效，静默退出
      }

      if (event.data.type === "ELEVEN_VOICES_UPDATED") {
        console.log("ElevenLabs Tool: Syncing voices to background...");
        chrome.runtime.sendMessage({ 
          action: "update_voices", 
          voices: event.data.voices 
        }).catch(() => {}); // 捕获异步消息错误
      }

      if (event.data.type === "ELEVEN_TOKEN_UPDATED") {
        console.log("ElevenLabs Tool: Syncing token to background...");
        chrome.runtime.sendMessage({ 
          action: "saveToken", 
          token: event.data.token 
        }).catch(() => {}); // 捕获异步消息错误
      }
    } catch (e) {
      // 捕获同步调用错误 (如 Context invalidated)
    }
  });

  // 3. 初始时，如果页面已经有 Token 也可以通过 extID.js 等方式同步，
  // 这里我们已经有 extID.js 处理 Token 了。
})();
