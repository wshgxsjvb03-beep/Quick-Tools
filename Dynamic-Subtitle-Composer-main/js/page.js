// 字幕数据
let subtitleData = []

// 存储每个视频的字幕区域位置和大小
const perVideoOverlaySettings = {}

// 存储每个视频独立的样式参数
const perVideoStyleSettings = {}

// 当前正在预览/编辑的视频索引
let currentEditingVideoIndex = 0

// 存储字幕区域的相对位置和大小
let overlaySettings = {
  left: 10,
  top: 35,
  width: 80,
  height: 30
}

// 标记是否正在拖拽
let dragging = false
// 标记是否正在拖拽
let resizing = false
// 记录鼠标事件坐标
let startX, startY, initLeft, initTop, initWidth, initHeight

// 存储多个视频文件
let videoFiles = []

const videoInput = document.getElementById('videoInput')
const subtitle = document.getElementById('subtitle')
const voicePack = document.getElementById('voicePack')
const videoPreview = document.getElementById('videoPreview')
const videoContainer = document.getElementById('videoContainer')
const previewPlaceholder = document.getElementById('previewPlaceholder')
const textOverlay = document.getElementById('textOverlay')
const previewText = document.getElementById('previewText')
const exportBtn = document.getElementById('exportBtn')
const progressContainer = document.getElementById('progressContainer')
const progressFill = document.getElementById('progressFill')
const progressPct = document.getElementById('progressPct')
const fontSizeInput = document.getElementById('fontSize')
const fontColorInput = document.getElementById('fontColor')
const fontFamilySelect = document.getElementById('fontFamily')
const watermarkInput = document.getElementById('watermarkText')
const watermarkPositionSelect = document.getElementById('watermarkPosition')
const progressBatchLabel = document.getElementById('progressBatchLabel')
const particleEffectSelect = document.getElementById('particleEffect')

// 粒子预览相关状态
let previewAnimationFrame
// 当前预览区域的粒子列表
let previewParticles = []

// 判断文件是否为图片
function isImageFile (file) {
  return file.type.startsWith('image/')
}

/**
 * @description 获取或创建预览用的 <img> 元素
 * @returns {HTMLImageElement}
 */
function getOrCreateImagePreview () {
  let imgEl = document.getElementById('imagePreview')
  if (!imgEl) {
    imgEl = document.createElement('img')
    imgEl.id = 'imagePreview'
    imgEl.style.cssText = 'width:100%;max-height:1200px;display:none;object-fit:contain;'
    // 插入到 videoContainer 最前面，确保在 textOverlay 之下
    videoContainer.insertBefore(imgEl, videoContainer.firstChild)
  }
  return imgEl
}

/**
 * @description 根据文件类型切换预览元素（视频或图片）
 * @param {File} file - 要预览的文件
 * @param {Function} [onReady] - 媒体就绪后的回调
 */
function switchMediaPreview (file, onReady) {
  const imgEl = getOrCreateImagePreview()

  if (isImageFile(file)) {
    // 隐藏视频，显示图片
    videoPreview.style.display = 'none'
    videoPreview.src = ''
    imgEl.style.display = 'block'
    imgEl.onload = () => {
      if (onReady) onReady()
    }
    imgEl.src = URL.createObjectURL(file)
  } else {
    // 隐藏图片，显示视频
    imgEl.style.display = 'none'
    imgEl.src = ''
    videoPreview.style.display = 'block'
    videoPreview.src = URL.createObjectURL(file)
    videoPreview.muted = true
    videoPreview.onloadedmetadata = () => {
      if (onReady) onReady()
    }
    videoPreview.onloadeddata = () => {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          const wmEl = document.getElementById('watermarkPreview')
          if (wmEl && wmEl.textContent) wmEl.style.color = sampleWatermarkColor()
          initPreviewParticles()
        })
      })
    }
  }
}

/**
 * @description 创建预览区域的粒子 Canvas
 * @returns {HTMLCanvasElement}
 */
function createOrResizePreviewParticleCanvas () {
  let pCanvas = document.getElementById('previewParticleCanvas')
  if (!pCanvas) {
    pCanvas = document.createElement('canvas')
    pCanvas.id = 'previewParticleCanvas'
    pCanvas.style = 'position:absolute; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:1;'
    videoContainer.appendChild(pCanvas)
  }

  // 以视频元素的实际渲染尺寸为准
  const videoRect = videoPreview.getBoundingClientRect()
  const containerRect = videoContainer.getBoundingClientRect()
  const width = Math.max(1, Math.round(videoRect.width || containerRect.width))
  const height = Math.max(1, Math.round(videoRect.height || containerRect.height))

  // 设置 canvas 的物理像素尺寸
  pCanvas.width = width
  pCanvas.height = height
  pCanvas.style.width = width + 'px'
  pCanvas.style.height = height + 'px'

  return pCanvas
}

/**
 * @description 初始化预览粒子动画
 */
function initPreviewParticles () {
  const effect = particleEffectSelect.value
  let pCanvas = document.getElementById('previewParticleCanvas')

  if (effect === 'none') {
    if (pCanvas) pCanvas.style.display = 'none'
    cancelAnimationFrame(previewAnimationFrame)
    return
  }

  pCanvas = createOrResizePreviewParticleCanvas()
  pCanvas.style.display = 'block'
  const ctx = pCanvas.getContext('2d')

  // 创建 60 个粒子随机散布
  previewParticles = Array.from({ length: 60 }, () => new Particle(pCanvas.width, pCanvas.height, effect, true))

  let lastTime = 0

  // 使用 requestAnimationFrame 驱动的动画循环
  function animate (timestamp) {
    if (!lastTime) lastTime = timestamp
    // 以 60fps (16.67ms/frame) 为基准，最大 2 倍速
    const dt = Math.min(2, (timestamp - lastTime) / 16.67)
    lastTime = timestamp

    ctx.clearRect(0, 0, pCanvas.width, pCanvas.height)

    previewParticles.forEach(p => {
      p.update(dt)
      p.draw(ctx)
    })

    previewAnimationFrame = requestAnimationFrame(animate)
  }

  // 先停止旧动画，避免多个动画循环并存
  cancelAnimationFrame(previewAnimationFrame)
  previewAnimationFrame = requestAnimationFrame(animate)
}

// 读取当前所有配置（含粒子特效）
function readStyleFromUI () {
  return {
    fontSize: fontSizeInput.value,
    fontColor: fontColorInput.value,
    fontFamily: fontFamilySelect.value,
    highlightBg: document.getElementById('highlightBg').value,
    bgScale: document.getElementById('bgScale').value,
    lineHeightMult: document.getElementById('lineHeightMult').value,
    pingPong: document.getElementById('pingPongToggle').checked,
    watermarkText: watermarkInput.value,
    watermarkPosition: watermarkPositionSelect.value,
    particleEffect: particleEffectSelect.value
  }
}

/**
 * @description 将配置应用到当前视频
 * @param {Object} style - 样式配置对象
 * @param {number} [style.fontSize] - 字体大小
 * @param {string} [style.fontColor] - 字体颜色
 * @param {string} [style.fontFamily] - 字体类型
 * @param {string} [style.highlightBg] - 高亮背景颜色
 * @param {number} [style.bgScale] - 背景缩放比例
 * @param {number} [style.lineHeightMult] - 行高倍数
 * @param {boolean} [style.pingPong] - 是否启用往返滚动效果
 * @param {string} [style.watermarkText] - 水印文本内容
 * @param {string} [style.watermarkPosition] - 水印显示位置
 * @param {string} [style.particleEffect] - 粒子特效类型
 */
function applyStyleToUI (style) {
  if (!style) return
  if (style.fontSize !== undefined) fontSizeInput.value = style.fontSize
  if (style.fontColor !== undefined) fontColorInput.value = style.fontColor
  if (style.fontFamily !== undefined) fontFamilySelect.value = style.fontFamily
  if (style.highlightBg !== undefined) document.getElementById('highlightBg').value = style.highlightBg
  if (style.bgScale !== undefined) document.getElementById('bgScale').value = style.bgScale
  if (style.lineHeightMult !== undefined) document.getElementById('lineHeightMult').value = style.lineHeightMult
  if (style.pingPong !== undefined) document.getElementById('pingPongToggle').checked = style.pingPong
  if (style.watermarkText !== undefined) watermarkInput.value = style.watermarkText
  if (style.watermarkPosition !== undefined) watermarkPositionSelect.value = style.watermarkPosition
  if (style.particleEffect !== undefined) particleEffectSelect.value = style.particleEffect
}

// 默认样式配置
function getDefaultStyle () {
  return {
    fontSize: '60',
    fontColor: '#ffffff',
    fontFamily: 'Arial',
    highlightBg: '#f03737',
    bgScale: '1.2',
    lineHeightMult: '1.5',
    pingPong: true,
    watermarkText: 'Attribution to Elevenlabs.io',
    watermarkPosition: 'bottom-right',
    particleEffect: 'none'
  }
}

// 保存当前视频的配置
function syncStyleToCurrentVideo () {
  perVideoStyleSettings[currentEditingVideoIndex] = readStyleFromUI()
}

/**
 * @description 获取对应视频的配置
 * @param {number} index - 视频在列表中的索引
 * @returns {Object} 当前视频对应的样式对象
 */
function getStyleForVideo (index) {
  return perVideoStyleSettings[index] || { ...getDefaultStyle() }
}

/**
 * @description 左下角提示
 * @param {string} text - 文本内容
 */
function notify (text) {
  Toastify({
    text,
    duration: 2000,
    close: true,
    gravity: 'bottom',
    position: 'left',
    style: {
      background: 'linear-gradient(to right, #00b09b, #96c93d)',
      fontSize: '18px'
    }
  }).showToast()
}

// 用临时 canvas 截取当前帧（视频或图片），分析水印区域背景色
function sampleWatermarkColor () {
  // 获取水印文本
  const wmText = watermarkInput ? watermarkInput.value.trim() : ''
  if (!wmText) return '#ffffff'

  const tmpCanvas = document.createElement('canvas')
  let source = null
  let vw, vh

  // 图片用 <img>，视频用 <video>
  const imgEl = document.getElementById('imagePreview')
  if (imgEl && imgEl.style.display !== 'none' && imgEl.complete && imgEl.naturalWidth > 0) {
    source = imgEl
    vw = imgEl.naturalWidth
    vh = imgEl.naturalHeight
  } else {
    // 没有水印文本时，默认返回白色
    if (videoPreview.readyState < 2) return '#ffffff'
    source = videoPreview
    vw = videoPreview.videoWidth || videoContainer.offsetWidth
    vh = videoPreview.videoHeight || videoContainer.offsetHeight
  }

  tmpCanvas.width = vw
  tmpCanvas.height = vh

  const tmpCtx = tmpCanvas.getContext('2d', { willReadFrequently: true })

  // 预览视频/图片
  tmpCtx.drawImage(source, 0, 0, vw, vh)

  // 水印字体大小
  const wmFs = Math.max(30, vw * 0.022)
  // 水印内边距
  const padding = 15
  // 水印字体
  tmpCtx.font = `bold ${wmFs}px sans-serif`
  // 水印宽度 + 外边距
  const wmWidth = tmpCtx.measureText(wmText).width + 20
  // 水印字体高度
  const wmHeight = wmFs + 10

  // 水印默认放右下角
  const wmPos = watermarkPositionSelect ? watermarkPositionSelect.value : 'bottom-right'

  let sampleX, sampleY
  if (wmPos === 'bottom-right') {
    // 右下角
    sampleX = vw - padding - wmWidth
    sampleY = vh - padding - wmHeight
  } else if (wmPos === 'bottom-left') {
    // 左下角
    sampleX = padding
    sampleY = vh - padding - wmHeight
  } else if (wmPos === 'top-right') {
    // 右上角
    sampleX = vw - padding - wmWidth
    sampleY = padding
  } else {
    // 左上角
    sampleX = padding
    sampleY = padding
  }

  // 分析区域颜色，自适应颜色
  return analyzeAreaColor(tmpCtx, sampleX, sampleY, wmWidth, wmHeight)
}

// 更新预览字幕样式
async function updatePreviewText () {
  const containerW = videoContainer.offsetWidth || 640
  const fs = Math.max(10, (parseInt(fontSizeInput.value) * containerW) / 900)
  const color = fontColorInput.value
  const bgColor = document.getElementById('highlightBg').value
  const bgScale = parseFloat(document.getElementById('bgScale').value) || 1.1
  const fontValue = fontFamilySelect.value
  const fontFamily = fontValue + ', sans-serif'
  const fontName = fontValue.replace(/'/g, '').trim()

  // 算背景高亮的垂直内边距
  const bgPaddingV = (fs * bgScale - fs) / 2

  try {
    // 异步加载字体，防止预览时字体没渲染出来
    await document.fonts.load(`bold ${Math.round(fs)}px "${fontName}"`)
  } catch {}

  // 设置预览容器样式
  previewText.style.fontFamily = fontFamily
  previewText.style.fontWeight = 'bold'
  previewText.style.fontSize = fs + 'px'
  previewText.style.color = color
  previewText.style.textShadow = '0 1px 4px rgba(0,0,0,0.6)'
  previewText.style.lineHeight = '1'
  previewText.style.display = 'flex'
  previewText.style.alignItems = 'center'
  previewText.style.flexWrap = 'wrap'
  previewText.style.justifyContent = 'center'
  previewText.style.gap = '2px'
  previewText.style.background = 'rgba(0, 0, 0, 0.5)'
  previewText.style.borderRadius = '8px'
  previewText.style.padding = '8px 12px'

  // 模拟一段包含高亮词的文本
  const words = [
    { text: 'Adjust the ', highlight: false },
    { text: 'text', highlight: true },
    { text: 'area', highlight: true },
    { text: 'here', highlight: false }
  ]

  previewText.innerHTML = ''
  words.forEach(w => {
    const span = document.createElement('span')
    span.textContent = w.text
    span.style.display = 'inline-block'
    span.style.color = color
    span.style.fontFamily = fontFamily
    span.style.fontWeight = 'bold'
    span.style.fontSize = fs + 'px'
    span.style.textShadow = '0 1px 4px rgba(0,0,0,0.6)'
    span.style.lineHeight = '1'
    span.style.padding = `${bgPaddingV}px 6px`

    // 如果是高亮词，应用背景色和圆角
    if (w.highlight) {
      span.style.background = bgColor
      span.style.borderRadius = '5px'
    }
    previewText.appendChild(span)
  })

  // 更新水印预览（智能选色）
  let wmEl = document.getElementById('watermarkPreview')
  if (!wmEl) {
    wmEl = document.createElement('div')
    wmEl.id = 'watermarkPreview'
    wmEl.style.position = 'absolute'
    wmEl.style.pointerEvents = 'none'
    wmEl.style.fontWeight = 'bold'
    wmEl.style.zIndex = '999'
    wmEl.style.transition = 'color 0.3s'
    videoContainer.appendChild(wmEl)
  }

  // 根据水印位置设置四角定位
  const wmPos = watermarkPositionSelect ? watermarkPositionSelect.value : 'bottom-right'
  wmEl.style.top = ''
  wmEl.style.bottom = ''
  wmEl.style.left = ''
  wmEl.style.right = ''
  if (wmPos === 'bottom-right') {
    wmEl.style.bottom = '14px'
    wmEl.style.right = '15px'
  } else if (wmPos === 'bottom-left') {
    wmEl.style.bottom = '14px'
    wmEl.style.left = '15px'
  } else if (wmPos === 'top-right') {
    wmEl.style.top = '14px'
    wmEl.style.right = '15px'
  } else if (wmPos === 'top-left') {
    wmEl.style.top = '14px'
    wmEl.style.left = '15px'
  }

  const wmText = watermarkInput ? watermarkInput.value.trim() : ''
  wmEl.textContent = wmText
  const wmFs = Math.max(14, videoContainer.offsetWidth * 0.022)
  wmEl.style.fontSize = wmFs + 'px'
  wmEl.style.textShadow = '1px 1px 3px rgba(0,0,0,0.5)'
  wmEl.style.opacity = '0.65'

  // 采样当前帧颜色
  wmEl.style.color = sampleWatermarkColor()
}

// 任一样式控件变化时，保存到当前视频并刷新预览
function onStyleChange () {
  syncStyleToCurrentVideo()
  updatePreviewText()
  saveSettings()
}

// 监听设置更改
fontSizeInput.addEventListener('input', onStyleChange)
fontColorInput.addEventListener('input', onStyleChange)
fontFamilySelect.addEventListener('change', onStyleChange)
document.getElementById('highlightBg').addEventListener('input', onStyleChange)
document.getElementById('bgScale').addEventListener('input', onStyleChange)
document.getElementById('lineHeightMult').addEventListener('input', onStyleChange)
document.getElementById('pingPongToggle').addEventListener('change', onStyleChange)
watermarkInput.addEventListener('input', onStyleChange)
watermarkPositionSelect.addEventListener('change', onStyleChange)

// 粒子特效下拉变化时，保存配置并重新初始化预览粒子
particleEffectSelect.addEventListener('change', () => {
  syncStyleToCurrentVideo()
  saveSettings()
  initPreviewParticles()
})

// 窗口缩放时重新适配粒子 Canvas 尺寸
window.addEventListener('resize', () => {
  if (videoContainer.style.display !== 'none' && particleEffectSelect.value !== 'none') {
    initPreviewParticles()
  }
})

function syncOverlayToCurrentVideo () {
  perVideoOverlaySettings[currentEditingVideoIndex] = { ...overlaySettings }
}

function getOverlayForVideo (idx) {
  return perVideoOverlaySettings[idx] || { left: 10, top: 35, width: 80, height: 30 }
}

function switchPreviewVideo (idx) {
  if (!videoFiles[idx]) return

  // 保存当前视频的 overlay 和样式配置
  syncOverlayToCurrentVideo()
  syncStyleToCurrentVideo()

  currentEditingVideoIndex = idx

  videoContainer.style.display = 'block'
  previewPlaceholder.style.display = 'none'

  // 恢复该视频的 overlay 配置
  const savedOverlay = getOverlayForVideo(idx)
  overlaySettings = { ...savedOverlay }
  textOverlay.style.left = overlaySettings.left + '%'
  textOverlay.style.top = overlaySettings.top + '%'
  textOverlay.style.width = overlaySettings.width + '%'
  textOverlay.style.height = overlaySettings.height + '%'

  // 恢复该视频的样式配置
  applyStyleToUI(getStyleForVideo(idx))

  // 高亮当前选中的视频标签
  document.querySelectorAll('.video-tab').forEach((btn, i) => {
    btn.classList.toggle('active', i === idx)
  })

  // 根据文件类型切换预览元素
  switchMediaPreview(videoFiles[idx], () => {
    updatePreviewText()
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        const wmEl = document.getElementById('watermarkPreview')
        if (wmEl && wmEl.textContent) wmEl.style.color = sampleWatermarkColor()
        // 视频切换后重新初始化粒子预览
        initPreviewParticles()
      })
    })
  })
}

function renderVideoTabs () {
  const tabContainer = document.getElementById('videoTabContainer')
  if (!tabContainer) return

  tabContainer.innerHTML = ''

  if (videoFiles.length <= 1) {
    tabContainer.style.display = 'none'
    return
  }

  tabContainer.style.display = 'flex'

  videoFiles.forEach((file, idx) => {
    const btn = document.createElement('button')
    btn.className = 'video-tab' + (idx === currentEditingVideoIndex ? ' active' : '')
    btn.textContent = `视频 ${idx + 1}: ${file.name.length > 12 ? file.name.slice(0, 12) + '…' : file.name}`
    btn.title = `点击切换预览并设置字幕位置\n${file.name}`
    btn.addEventListener('click', () => switchPreviewVideo(idx))
    tabContainer.appendChild(btn)
  })
}

// 读取视频/图片文件
videoInput.onchange = e => {
  const files = Array.from(e.target.files)
  if (!files.length) return

  videoFiles = files

  // 为每个视频初始化默认配置（overlay + 样式）
  files.forEach((_, idx) => {
    if (!perVideoOverlaySettings[idx]) {
      perVideoOverlaySettings[idx] = { left: 10, top: 35, width: 80, height: 30 }
    }
    if (!perVideoStyleSettings[idx]) {
      // 新视频继承当前面板的设置，方便批量使用同一套样式
      perVideoStyleSettings[idx] = readStyleFromUI()
    }
  })

  // 默认预览第一个
  currentEditingVideoIndex = 0
  overlaySettings = { ...getOverlayForVideo(0) }
  textOverlay.style.left = overlaySettings.left + '%'
  textOverlay.style.top = overlaySettings.top + '%'
  textOverlay.style.width = overlaySettings.width + '%'
  textOverlay.style.height = overlaySettings.height + '%'

  applyStyleToUI(getStyleForVideo(0))

  videoContainer.style.display = 'block'
  previewPlaceholder.style.display = 'none'

  // 根据文件类型切换预览元素
  switchMediaPreview(files[0], () => {
    updatePreviewText()
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        const wmEl = document.getElementById('watermarkPreview')
        if (wmEl && wmEl.textContent) wmEl.style.color = sampleWatermarkColor()
        // 视频加载完成后初始化粒子预览
        initPreviewParticles()
      })
    })
  })

  renderVideoTabs()
}

// 字幕层拖拽事件
textOverlay.addEventListener('mousedown', e => {
  if (e.target.id === 'resizeHandle') return
  dragging = true
  startX = e.clientX
  startY = e.clientY
  const rect = textOverlay.getBoundingClientRect()
  const cont = videoContainer.getBoundingClientRect()
  initLeft = rect.left - cont.left
  initTop = rect.top - cont.top
})

// 缩放手柄按下鼠标
document.getElementById('resizeHandle').addEventListener('mousedown', e => {
  resizing = true
  startX = e.clientX
  startY = e.clientY
  initWidth = textOverlay.offsetWidth
  initHeight = textOverlay.offsetHeight
  e.stopPropagation()
  e.preventDefault()
})

// 全局监听鼠标移动
document.addEventListener('mousemove', e => {
  const cont = videoContainer.getBoundingClientRect()
  if (dragging) {
    // 计算位移并转换为百分比
    overlaySettings.left = Math.max(0, ((initLeft + e.clientX - startX) / cont.width) * 100)
    overlaySettings.top = Math.max(0, ((initTop + e.clientY - startY) / cont.height) * 100)
    textOverlay.style.left = overlaySettings.left + '%'
    textOverlay.style.top = overlaySettings.top + '%'
    syncOverlayToCurrentVideo()
  } else if (resizing) {
    // 计算宽高并转换为百分比
    overlaySettings.width = Math.max(10, ((initWidth + e.clientX - startX) / cont.width) * 100)
    overlaySettings.height = Math.max(5, ((initHeight + e.clientY - startY) / cont.height) * 100)
    textOverlay.style.width = overlaySettings.width + '%'
    textOverlay.style.height = overlaySettings.height + '%'
    syncOverlayToCurrentVideo()
  }
})

// 释放鼠标时停止所有交互
document.addEventListener('mouseup', () => {
  dragging = resizing = false
})

// 文件转换 base64
const toBase64 = file =>
  new Promise(resolve => {
    const r = new FileReader()
    r.onload = ev => resolve(ev.target.result)
    r.readAsDataURL(file)
  })

function setProgress (pct) {
  pct = Math.min(100, Math.max(0, Math.round(pct)))
  progressFill.style.width = pct + '%'
  progressPct.textContent = pct + '%'
}

// 导出视频
exportBtn.addEventListener('click', async () => {
  if (!videoFiles.length) return notify('请先选择视频')
  if (!subtitle || !subtitle.value.trim()) return notify('请输入字幕内容')
  if (!voicePack.value) return notify('未登录 Elevenlabs')

  const opalToken = await getOpalToken()
  if (!opalToken) return notify('未登陆 opal')

  // 保存当前视频的 overlay 和样式
  syncOverlayToCurrentVideo()
  syncStyleToCurrentVideo()

  const textLines = subtitle.value
    .split('\n')
    .map(l => l.trim())
    .filter(l => l.length > 0)
  if (!textLines.length) return notify('请输入字幕内容')

  const totalTasks = textLines.length
  const videoCount = videoFiles.length

  // UI 状态切换
  exportBtn.disabled = true
  progressContainer.style.display = 'block'
  setProgress(0)
  if (progressBatchLabel) progressBatchLabel.textContent = `0/${totalTasks}`

  // 滚动到进度条位置
  progressContainer.scrollIntoView({ behavior: 'smooth', block: 'center' })

  notify(`开始批量渲染，共 ${totalTasks} 个视频`)

  const tasks = []
  for (let i = 0; i < textLines.length; i++) {
    const videoIdx = i % videoCount
    const videoFile = videoFiles[videoIdx]
    const textContent = textLines[i]
    const overlay = getOverlayForVideo(videoIdx)
    // 每个任务使用对应视频的独立样式配置
    const style = getStyleForVideo(videoIdx)

    tasks.push({ videoFile, textContent, overlay, style, videoIdx, taskIndex: i })
  }

  for (let i = 0; i < tasks.length; i++) {
    const task = tasks[i]
    if (progressBatchLabel) progressBatchLabel.textContent = `${i + 1}/${totalTasks}`

    notify(`处理第 ${i + 1}/${totalTasks} 个：${task.textContent.slice(0, 20)}...`)

    // ── 阶段一：获取音频（0% → 10%）───────────────────────────
    setProgress(0)
    const videoData = await toBase64(task.videoFile)

    notify('正在获取音频')
    const audioBlob = await textToSpeech(task.textContent, voicePack.value)
    notify('获取音频完成')
    setProgress(10)

    // ── 阶段二：获取字幕（10% → 20%）──────────────────────────
    notify('正在转换字幕')
    subtitleData = await audioToSubtitle(audioBlob, opalToken)
    notify('转换字幕完成')
    setProgress(20)

    const audioData = await toBase64(audioBlob)

    notify(`开始渲染第 ${i + 1}/${totalTasks} 个视频`)

    // ── 阶段三：渲染（20% → 100%）─────────────────────────────
    await new Promise(resolve => {
      window._batchTaskResolve = resolve

      // 发送到后台渲染
      chrome.runtime.sendMessage({
        type: 'start-export',
        payload: {
          videoData,
          audioData,
          subtitleData,
          overlaySettings: task.overlay,
          // 使用该视频独立的样式配置
          fontSize: parseInt(task.style.fontSize),
          highlightBg: task.style.highlightBg,
          fontColor: task.style.fontColor,
          fontFamily: task.style.fontFamily,
          bgScale: parseFloat(task.style.bgScale),
          lineHeightMult: parseFloat(task.style.lineHeightMult),
          pingPong: task.style.pingPong,
          watermarkText: task.style.watermarkText,
          watermarkPosition: task.style.watermarkPosition,
          particleEffect: task.style.particleEffect || 'none',
          batchIndex: i,
          batchTotal: totalTasks
        }
      })
    })
  }

  exportBtn.disabled = false
  setProgress(100)
  if (progressBatchLabel) progressBatchLabel.textContent = `${totalTasks}/${totalTasks}`
  document.getElementById('statusHint').textContent = `全部 ${totalTasks} 个视频导出完成！`
  setTimeout(() => {
    progressContainer.style.display = 'none'
    document.getElementById('statusHint').textContent = '导出完成后将自动弹出保存对话框'
  }, 4000)
})

// 监听进度回传
chrome.runtime.onMessage.addListener(msg => {
  // 更新进度条
  if (msg.type === 'progress-update') {
    const renderPct = 20 + Math.round(msg.progress * 80)
    setProgress(renderPct)
  }

  // 渲染完成处理
  if (msg.type === 'export-finished') {
    notify('视频渲染完成')
    setProgress(100)
    if (typeof window._batchTaskResolve === 'function') {
      const resolve = window._batchTaskResolve
      window._batchTaskResolve = null
      resolve()
    }
  }
})

// 初始化预览
updatePreviewText()

// 获取 opal 访问令牌
async function getOpalToken () {
  const token = await fetch('https://opal.google/connection/refresh/')
    .then(response => response.json())
    .then(json => json.access_token)
  return token
}

/**
 * @description 音频转文字
 * @param {Blob} blob - 音频数据
 * @param {string} token - opal 访问令牌
 * @returns {Promise<Object[]>} 返回字幕数组
 */
async function audioToSubtitle (blob, token) {
  const audioBase64 = await toBase64(blob).then(result => result.split(',')[1])

  const param = {
    contents: [
      {
        parts: [{ text: '\n ' }, { inlineData: { data: audioBase64, mimeType: blob.type } }],
        role: 'user'
      }
    ],
    safetySettings: [
      { category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold: 'BLOCK_NONE' },
      { category: 'HARM_CATEGORY_HARASSMENT', threshold: 'BLOCK_NONE' },
      { category: 'HARM_CATEGORY_DANGEROUS_CONTENT', threshold: 'BLOCK_NONE' }
    ],
    systemInstruction: {
      parts: [
        {
          text: '请你分析音频，然后JSON 格式的文件。每一行（句子）包含它自己的开始和结束时间，以及一个 words 数组，句子不能太长，最多不能超过60字符，标记每个单词的具体出现时刻。\nAnalyze the attached image carefully and return **ONLY valid JSON**\n```json\n[\n  {\n    "start": 0.5,\n    "end": 3.2,\n    "text": "Napakapalad mo talaga",\n    "words": [\n      { "text": "Napakapalad", "start": 0.5, "end": 1.2 },\n      { "text": "mo", "start": 1.3, "end": 1.8 },\n      { "text": "talaga", "start": 1.9, "end": 3.2 }\n    ]\n  },\n  {\n    "start": 3.5,\n    "end": 6.0,\n    "text": "Maraming tao ang nagskip",\n    "words": [\n      { "text": "Maraming", "start": 3.5, "end": 4.1 },\n      { "text": "tao", "start": 4.2, "end": 4.5 },\n      { "text": "ang", "start": 4.6, "end": 4.8 },\n      { "text": "nagskip", "start": 4.9, "end": 6.0 }\n    ]\n  }\n]\n```'
        }
      ],
      role: 'user'
    }
  }

  const json = await fetch('https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent', {
    headers: { authorization: 'Bearer ' + token },
    body: JSON.stringify(param),
    method: 'POST',
    credentials: 'include'
  }).then(response => response.json())
  const formatJson = JSON.parse(json.candidates[0].content.parts[0].text.replace(/^```json|```$/g, ''))
  return formatJson
}

// 获取 elevenlabs 账号访问令牌
async function getToken () {
  return await new Promise(resolve => {
    chrome.storage.local.get(null, data => resolve(data))
  }).then(result => result.token)
}

// 获取语音包列表
async function getVoicePackList () {
  const json = await fetch('https://api.us.elevenlabs.io/v2/voices?page_size=100&sort=name&sort_direction=asc', {
    headers: {
      accept: '*/*',
      authorization: 'Bearer ' + (await getToken()),
      'content-type': 'application/json'
    },
    method: 'GET',
    credentials: 'include'
  }).then(response => response.json())
  if (json?.detail?.status === 'invalid_authorization_header') {
    return notify('未登录 Elevenlabs')
  }
  // 写入下拉菜单
  json.voices.map(x => voicePack.add(new Option(x.name, x.voice_id)))
}

/**
 * @description 文本转语音
 * @param {string} text - 文本内容
 * @param {string} voiceId - 语音包 ID
 * @returns {Promise<Blob>} 返回生成的音频 Blob
 */
async function textToSpeech (text, voiceId) {
  const param = { text, model_id: 'eleven_flash_v2_5' }
  const blob = await fetch(`https://api.us.elevenlabs.io/v1/text-to-speech/${voiceId}/stream`, {
    headers: {
      accept: '*/*',
      authorization: 'Bearer ' + (await getToken()),
      'content-type': 'application/json'
    },
    body: JSON.stringify(param),
    method: 'POST',
    credentials: 'include'
  }).then(response => response.blob())
  return blob
}

// 保存配置
function saveSettings () {
  chrome.storage.local.set(readStyleFromUI())
  // updatePreviewText()
}

// 加载配置
function loadSettings () {
  chrome.storage.local.get(null, config => {
    const defaults = getDefaultStyle()
    const merged = { ...defaults, ...config }
    applyStyleToUI(merged)
    // 读取完后刷新预览
    updatePreviewText()
  })
}

// 初始化
getVoicePackList()
loadSettings()
