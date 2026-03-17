// 拦截 ElevenLabs 的 fetch 调用以获取 Voice List 和 Token
(function() {
  const originalFetch = window.fetch;

  window.fetch = async (...args) => {
    const response = await originalFetch(...args);
    const url = typeof args[0] === 'string' ? args[0] : args[0].url;

    try {
      // 1. 拦截声音列表
      if (url.includes('/api/v1/voices')) {
        const clone = response.clone();
        const data = await clone.json();
        if (data && data.voices) {
          const simplifiedVoices = data.voices.map(v => ({ id: v.voice_id, name: v.name }));
          console.log("ElevenLabs Tool: Captured voices", simplifiedVoices);
          window.postMessage({ type: "ELEVEN_VOICES_UPDATED", voices: simplifiedVoices }, "*");
        }
      }

      // 2. 拦截 Token (Firebase Identity Lookup)
      if (url.includes('identitytoolkit.googleapis.com/v1/accounts:lookup')) {
         const clone = response.clone();
         const data = await clone.json();
         if (data && data.users && data.users[0]) {
           // lookup 请求的 body 通常包含 idToken
           // 但 response 里的 localId 等也是标识
         }
      }
      
      // 拦截所有带 Authorization 的请求 (更通用)
      const authHeader = args[1] && args[1].headers && (args[1].headers['Authorization'] || args[1].headers['authorization']);
      if (authHeader && authHeader.startsWith('Bearer ')) {
        const token = authHeader.substring(7);
        if (token && token.length > 100) { // 简单的长度校验，防止误抓
          window.postMessage({ type: "ELEVEN_TOKEN_UPDATED", token: token }, "*");
        }
      }
    } catch (e) {
      // 忽略解析错误
    }

    return response;
  };
})();
