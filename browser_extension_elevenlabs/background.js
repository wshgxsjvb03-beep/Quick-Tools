// Chrome extension background script (Manifest V3, service worker)

const HOST_NAME = "quick_tools_elevenlabs_host";
let lastToken = null;
let nativePort = null;
let voiceCache = []; // 用于存储抓取到的声音列表

// 初始化连接
function connectToNativeHost() {
  if (nativePort) return;
  
  console.log("Connecting to native host...");
  nativePort = chrome.runtime.connectNative(HOST_NAME);
  
  nativePort.onMessage.addListener((msg) => {
    console.log("Received from host:", msg);
    handleHostMessage(msg);
  });

  nativePort.onDisconnect.addListener(() => {
    console.log("Native host disconnected:", chrome.runtime.lastError);
    nativePort = null;
    // 1秒后尝试重连
    setTimeout(connectToNativeHost, 1000);
  });
}

async function handleHostMessage(msg) {
  if (msg.action === "generate_audio" || msg.action === "generate_audio_request") {
    try {
      if (!lastToken) {
        throw new Error("未获取到登录 Token，请刷新 ElevenLabs 网页并确保已登录。");
      }

      const { text, voiceId, modelId, name } = msg;
      const url = `https://elevenlabs.io/api/v1/text-to-speech/${voiceId}`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${lastToken}`,
          'Accept': 'audio/mpeg'
        },
        body: JSON.stringify({
          text,
          model_id: modelId,
          voice_settings: {
            stability: 0.5,
            similarity_boost: 0.75
          }
        })
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`API 返回错误 (${response.status}): ${errText}`);
      }

      const audioBlob = await response.blob();
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64Audio = reader.result.split(',')[1];
        const safeName = name || "elevenlabs_audio";
        const filename = `elevenlabs/${safeName.endsWith('.mp3') ? safeName : safeName + '.mp3'}`;
        
        const result = {
          action: "audio_generated",
          status: "success",
          audio: base64Audio,
          name: safeName
        };

        // 优先发送到主程序保存
        if (nativePort) {
          nativePort.postMessage(result);
          console.log("Audio sent to Native Host:", filename);
        } else {
          // 独立模式：直接通过浏览器下载
          const dataUrl = 'data:audio/mpeg;base64,' + base64Audio;
          chrome.downloads.download({
            url: dataUrl,
            filename: filename,
            saveAs: false
          }, (downloadId) => {
            if (chrome.runtime.lastError) {
               console.error("Download failed:", chrome.runtime.lastError);
            } else {
               console.log("Download started, ID:", downloadId);
               // 发送状态给面板或弹出通知
               chrome.notifications.create({
                 type: 'basic',
                 title: 'ElevenLabs 批量助手',
                 message: `音频已开始下载: ${safeName}`,
                 iconUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==' // 用一个透明像素占位
               });
            }
          });
          console.log("Audio saved via Browser Downloads (Standalone Mode).");
        }
        
        if (msg.sendResponse) {
          msg.sendResponse(result);
        }
      };
      reader.readAsDataURL(audioBlob);

    } catch (error) {
      console.error("Generation failed:", error);
      const errResult = {
        action: "audio_generated",
        status: "error",
        error: error.message
      };
      if (nativePort) nativePort.postMessage(errResult);
      if (msg.sendResponse) msg.sendResponse(errResult);
    }
  }
}

// 启动重连机制
connectToNativeHost();

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.action === "saveToken") {
    lastToken = msg.token || null;
    console.log("Token saved:", lastToken ? "Success" : "Empty");
    sendResponse({ ok: true });
    return true;
  }

  if (msg && msg.action === "get_voices_cache") {
    sendResponse({ voices: voiceCache });
    return true;
  }
  
  if (msg && msg.action === "update_voices") {
    if (msg.voices) voiceCache = msg.voices;
    sendResponse({ ok: true });
    return true;
  }

  if (msg && msg.action === "generate_audio_request") {
    // 包装一下调用
    handleHostMessage({ ...msg, sendResponse });
    return true; // 异步
  }

  if (msg && msg.action === "get_status") {
    sendResponse({ 
      connected: nativePort !== null,
      lastToken: lastToken !== null
    });
    return true;
  }

  if (msg && msg.action === "testNative") {
    if (nativePort) {
      nativePort.postMessage({ command: "ping" });
      sendResponse({ ok: true });
    } else {
      sendResponse({ ok: false, error: "Host not connected" });
    }
    return true;
  }

  return false;
});

