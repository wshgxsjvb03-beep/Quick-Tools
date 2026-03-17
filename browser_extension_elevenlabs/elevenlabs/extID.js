;(() => {
  // 将扩展 ID 写入页面，供注入脚本读取
  const element = document.createElement("div");
  element.innerHTML = chrome.runtime.id;
  element.id = "qt_elevenlabs_ext_id";
  element.style.display = "none";
  document.documentElement.appendChild(element);

  // 注入 fetch 劫持脚本
  const script = document.createElement("script");
  script.src = chrome.runtime.getURL("/elevenlabs/injectFetch.js");
  (document.head || document.documentElement).appendChild(script);
})();

