chrome.action.onClicked.addListener(() => {
  chrome.tabs.create({
    url: chrome.runtime.getURL('/html/page.html')
  })
})

// 记录是否创建过 offscreen
let offscreenCreated = false

async function ensureOffscreen () {
  // 已创建过 offscreen，避免重复创建
  if (offscreenCreated) return
  try {
    // 创建 offscreen 页面
    await chrome.offscreen.createDocument({
      url: chrome.runtime.getURL('/html/offscreen.html'),
      reasons: ['BLOBS'], // 处理 Blob/Canvas/MediaRecorder
      justification: 'Canvas rendering and MediaRecorder video encoding'
    })
    offscreenCreated = true
    console.log('offscreen 创建成功')
  } catch (error) {
    console.error('offscreen 创建失败', error)
  }
}

// 外部扩展消息监听
chrome.runtime.onMessageExternal.addListener(function (message, sender, sendResponse) {
  const action = message.action
  if (action === 'token') {
    // 储存 token
    sendResponse(chrome.storage.local.set({ token: message.token }))
  } else if (action === 'mark') {
    // 显示徽标
    sendResponse(chrome.action.setBadgeText({ text: message.text }))
  }

  return true
})

// 内部扩展消息监听
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === 'start-export') {
    console.log(msg.payload)
    ensureOffscreen().then(() => {
      chrome.runtime.sendMessage({ type: 'do-export', payload: msg.payload })
    })
    sendResponse({ ok: true })
    return true
  }

  if (msg.type === 'export-progress') {
    // 收到进度更新消息，转发给前台
    chrome.runtime.sendMessage({
      type: 'progress-update',
      progress: msg.progress
    })
  }

  if (msg.type === 'export-done') {
    // 视频导出完成，下载 WebM 文件
    const batchIndex = msg.batchIndex !== undefined ? msg.batchIndex : 0
    const filename = `video_${batchIndex + 1}_${Date.now()}.webm`

    chrome.downloads.download({
      url: msg.blobUrl,
      filename,
      saveAs: false // 不弹出保存对话框
    })

    // 通知前台当前视频已完成，可以处理下一个
    chrome.runtime.sendMessage({ type: 'export-finished' })
  }

  if (msg.type === 'all-export-done') {
    // 全部任务完成，关闭 offscreen
    offscreenCreated = false
    chrome.offscreen.closeDocument?.()
  }
})
