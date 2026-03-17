const logBox = document.getElementById("log");

function log(msg) {
  logBox.textContent += msg + "\n";
  logBox.scrollTop = logBox.scrollHeight;
}

document.getElementById("btn-test-host").onclick = () => {
  chrome.runtime.sendMessage({ action: "testNative" }, (res) => {
    if (!res || !res.ok) {
      log("❌ Host 连接失败: " + (res && res.error));
    } else {
      log("✅ Host 响应: " + JSON.stringify(res.response));
    }
  });
};

document.getElementById("btn-send-batch").onclick = () => {
  const demoJobs = [
    { id: "demo_1", text: "Hello from extension", voiceId: "", fileName: "demo_1.mp3" },
    { id: "demo_2", text: "第二条示例文案", voiceId: "", fileName: "demo_2.mp3" }
  ];
  chrome.runtime.sendMessage(
    { action: "batch_from_popup", jobs: demoJobs },
    (res) => {
      if (!res || !res.ok) {
        log("❌ 发送批量任务失败: " + (res && res.error));
      } else {
        log("✅ Host 返回: " + JSON.stringify(res.response));
      }
    }
  );
};

