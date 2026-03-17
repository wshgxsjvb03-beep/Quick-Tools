const canvas = document.getElementById('canvas')
const ctx = canvas.getContext('2d', { willReadFrequently: true })
const videoSource = document.getElementById('videoSource')
const audioSource = document.getElementById('audioSource')
const fontPreloader = document.getElementById('fontPreloader')

const REMOTE_FONTS_CONFIG = {
  Roboto: 'https://fonts.googleapis.com/css2?family=Roboto:wght@700&display=swap',
  Kavivanar: 'https://fonts.googleapis.com/css2?family=Kavivanar&display=swap',
  'Playwrite NZ': 'https://fonts.googleapis.com/css2?family=Playwrite+NZ:wght@100..400&display=swap',
  'Shantell Sans': 'https://fonts.googleapis.com/css2?family=Shantell+Sans:wght@700&display=swap',
  'Playpen Sans Thai': 'https://fonts.googleapis.com/css2?family=Playpen+Sans+Thai:wght@700&display=swap',
  'Patrick Hand': 'https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap',
  'Comic Neue': 'https://fonts.googleapis.com/css2?family=Comic+Neue:wght@700&display=swap',
  Kalam: 'https://fonts.googleapis.com/css2?family=Kalam:wght@700&display=swap',
  Caveat: 'https://fonts.googleapis.com/css2?family=Caveat:wght@700&display=swap',
  Stylish: 'https://fonts.googleapis.com/css2?family=Stylish&display=swap',
  Merienda: 'https://fonts.googleapis.com/css2?family=Merienda:wght@700&display=swap',
  Itim: 'https://fonts.googleapis.com/css2?family=Itim&display=swap',
  'Rubik Doodle Shadow': 'https://fonts.googleapis.com/css2?family=Rubik+Doodle+Shadow&display=swap'
}

const fontDataUriCache = {}

/**
 * @description 加载字体
 * @param {string} fontFamily - 字体名称
 */
async function loadFont (fontFamily) {
  const fontName = fontFamily.replace(/'/g, '').trim()
  if (!REMOTE_FONTS_CONFIG[fontName]) return

  try {
    if (!fontDataUriCache[fontName]) {
      const cssResp = await fetch(REMOTE_FONTS_CONFIG[fontName], {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
        }
      })
      const cssText = await cssResp.text()

      const faceBlocks = [...cssText.matchAll(/@font-face\s*\{([^}]+)\}/g)].map(m => m[1])
      let fontUrl = null
      for (const block of faceBlocks) {
        const isBold = /font-weight\s*:\s*(bold|700)/i.test(block)
        const urlMatch = block.match(/url\(([^)]+)\)\s+format\(['"']?woff2['"']?\)/)
        if (urlMatch) {
          const url = urlMatch[1].replace(/['"]/g, '')
          if (!fontUrl) fontUrl = url
          if (isBold) {
            fontUrl = url
            break
          }
        }
      }

      if (!fontUrl) {
        console.warn('未找到 woff2 CSS', cssText.slice(0, 300))
        return
      }

      const fontResp = await fetch(fontUrl)
      const fontBuffer = await fontResp.arrayBuffer()

      const uint8 = new Uint8Array(fontBuffer)
      let binary = ''
      for (let i = 0; i < uint8.length; i += 8192) {
        binary += String.fromCharCode(...uint8.subarray(i, i + 8192))
      }

      fontDataUriCache[fontName] = `data:font/woff2;base64,${btoa(binary)}`
      console.log('woff2 下载完成', fontName, (fontBuffer.byteLength / 1024).toFixed(1), 'KB')
    }

    await registerFontFaces(fontName)

    fontPreloader.style.fontFamily = `"${fontName}", sans-serif`
    fontPreloader.style.fontWeight = 'bold'
    fontPreloader.textContent = '字体激活 Font Warmup 0123'
    await new Promise(r => setTimeout(r, 300))

    console.log(
      '加载字体成功',
      fontName,
      [...document.fonts].filter(f => f.family.replace(/'/g, '').trim() === fontName).map(f => `w${f.weight}(${f.status})`)
    )
  } catch (error) {
    console.warn('失败', fontName, error)
  }
}

/**
 * @description 注册字体
 * @param {string} fontName - 字体名称
 */
async function registerFontFaces (fontName) {
  const dataUri = fontDataUriCache[fontName]
  if (!dataUri) return
  for (const weight of ['400', '700']) {
    const already = [...document.fonts].some(f => f.family.replace(/'/g, '').trim() === fontName && f.status === 'loaded')
    if (already) continue
    const face = new FontFace(fontName, `url(${dataUri})`, { weight })
    const loaded = await face.load()
    document.fonts.add(loaded)
  }

  await document.fonts.ready
}

// 注册字体
async function reAddFonts () {
  for (const fontName of Object.keys(fontDataUriCache)) {
    await registerFontFaces(fontName)
  }

  await document.fonts.ready
}

/**
 * @description 文本自动换行
 * @param {CanvasRenderingContext2D} ctx - Canvas 2D 绘图上下文
 * @param {Object[]} words - 单词数组
 * @param {number} maxWidth - 每行允许的最大宽度
 * @returns {Object[][]} 返回二维数组，每个子数组表示一行的单词对象
 */
function getWrappedLines (ctx, words, maxWidth) {
  const lines = []
  let currentLine = []
  let currentWidth = 0
  const spaceWidth = ctx.measureText(' ').width

  words.forEach(word => {
    const ww = ctx.measureText(word.text).width
    if (currentWidth + ww > maxWidth && currentLine.length > 0) {
      lines.push(currentLine)
      currentLine = [word]
      currentWidth = ww + spaceWidth
    } else {
      currentLine.push(word)
      currentWidth += ww + spaceWidth
    }
  })
  if (currentLine.length > 0) lines.push(currentLine)
  return lines
}

/**
 * @description 渲染当对应时间的字幕
 * @param {number} time - 当前视频播放时间
 * @param {Object} payload - 渲染参数对象
 * @param {Object[]} payload.subtitleData - 字幕数据数组
 * @param {Object} payload.overlaySettings - 叠加区域百分比配置
 * @param {number} payload.fontSize - 字体大小比例
 * @param {string} payload.highlightBg - 单词高亮背景颜色
 * @param {string} [payload.fontColor='#ffffff'] - 字体颜色
 * @param {string} [payload.fontFamily='Arial'] - 字体名称
 * @param {number} payload.bgScale - 高亮背景高度缩放比例
 * @param {number} payload.lineHeightMult - 行高倍数
 */
function drawSubtitle (time, payload) {
  const { subtitleData, overlaySettings, fontSize, highlightBg, fontColor = '#ffffff', fontFamily = 'Arial', bgScale, lineHeightMult } = payload

  const sentence = subtitleData.find(s => time >= s.start && time < s.end)
  if (!sentence) return

  const fs = (fontSize * canvas.width) / 900
  const lh = fs * lineHeightMult
  const fontName = fontFamily.replace(/'/g, '').trim()

  ctx.font = `bold ${fs}px "${fontName}"`
  if (ctx.font.includes('sans-serif') || ctx.font === '10px sans-serif') {
    ctx.font = `bold ${fs}px ${fontName}`
  }

  ctx.textBaseline = 'middle'

  const rectX = (overlaySettings.left / 100) * canvas.width
  const rectY = (overlaySettings.top / 100) * canvas.height
  const rectW = (overlaySettings.width / 100) * canvas.width
  const rectH = (overlaySettings.height / 100) * canvas.height

  const lines = getWrappedLines(ctx, sentence.words, rectW)
  const totalContentH = lines.length * lh

  const spaceW = ctx.measureText(' ').width
  let maxLineWidth = 0
  lines.forEach(line => {
    const lineWidth = line.reduce((acc, w) => acc + ctx.measureText(w.text).width, 0) + (line.length - 1) * spaceW
    if (lineWidth > maxLineWidth) maxLineWidth = lineWidth
  })

  const padX = fs * 0.4
  const padY = fs * 0.4
  const bgW = maxLineWidth + padX * 2
  const bgH = totalContentH + padY * 2
  const bgX = rectX + (rectW - bgW) / 2
  const bgY = rectY + (rectH - bgH) / 2

  ctx.save()
  ctx.fillStyle = 'rgba(0, 0, 0, 0.5)'
  ctx.beginPath()
  ctx.roundRect(bgX, bgY, bgW, bgH, 10)
  ctx.fill()
  ctx.restore()

  let startY = bgY + padY + lh / 2

  lines.forEach(line => {
    const lineWidth = line.reduce((acc, w) => acc + ctx.measureText(w.text).width, 0) + (line.length - 1) * spaceW
    let currentX = bgX + (bgW - lineWidth) / 2

    line.forEach(word => {
      const wW = ctx.measureText(word.text).width

      if (time >= word.start && time < word.end) {
        ctx.save()
        ctx.fillStyle = highlightBg
        const bgHWord = fs * bgScale
        const bgYWord = startY - bgHWord / 2
        ctx.beginPath()
        ctx.roundRect(currentX - 6, bgYWord, wW + 12, bgHWord, 8)
        ctx.fill()
        ctx.restore()
      }

      ctx.font = `bold ${fs}px "${fontName}"`
      ctx.fillStyle = fontColor
      ctx.shadowColor = 'rgba(0,0,0,0.5)'
      ctx.shadowBlur = 4
      ctx.fillText(word.text, currentX, startY)
      ctx.shadowBlur = 0
      ctx.shadowColor = 'transparent'

      currentX += wW + spaceW
    })

    startY += lh
  })
}

/**
 * @description 视频播放时间跳转到目标时间
 * @param {number} targetTime - 目标播放时间
 * @returns {Promise} 播放器完成跳转后的 Promise
 */
async function seekTo (targetTime) {
  if (Math.abs(videoSource.currentTime - targetTime) < 0.033) return
  return new Promise(resolve => {
    videoSource.onseeked = resolve
    videoSource.currentTime = targetTime
  })
}

/**
 * @description dataURL 转换 ArrayBuffer
 * @param {string} dataURL - base64 资源
 * @returns {Promise} 返回对应的 ArrayBuffer 数据
 */
async function dataURLToArrayBuffer (dataURL) {
  const res = await fetch(dataURL)
  return res.arrayBuffer()
}

/**
 * @description 绘制水印文本
 * @param {Object} payload - 水印参数对象
 * @param {string} payload.watermarkText - 水印文本内容
 * @param {string} [payload.watermarkPosition='bottom-right'] - 水印显示位置
 */
function drawWatermark (payload) {
  if (!payload.watermarkText) return

  const wmPos = payload.watermarkPosition || 'bottom-right'
  // 水印字体大小
  const wmFs = Math.max(30, canvas.width * 0.022)
  // 水印内边距
  const padding = 15

  ctx.save()
  // 水印字体
  ctx.font = `bold ${wmFs}px sans-serif`

  // 水印宽度 + 外边距
  const wmWidth = ctx.measureText(payload.watermarkText).width + 20
  const wmHeight = wmFs + 10
  let drawX, drawY, sampleX, sampleY

  if (wmPos === 'bottom-right') {
    // 右下角
    ctx.textAlign = 'right'
    ctx.textBaseline = 'bottom'
    drawX = canvas.width - padding
    drawY = canvas.height - padding
    sampleX = canvas.width - padding - wmWidth
    sampleY = canvas.height - padding - wmHeight
  } else if (wmPos === 'bottom-left') {
    // 左下角
    ctx.textAlign = 'left'
    ctx.textBaseline = 'bottom'
    drawX = padding
    drawY = canvas.height - padding
    sampleX = padding
    sampleY = canvas.height - padding - wmHeight
  } else if (wmPos === 'top-right') {
    // 右上角
    ctx.textAlign = 'right'
    ctx.textBaseline = 'top'
    drawX = canvas.width - padding
    drawY = padding
    sampleX = canvas.width - padding - wmWidth
    sampleY = padding
  } else {
    // 左上角
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
    drawX = padding
    drawY = padding
    sampleX = padding
    sampleY = padding
  }

  // 智能分析水印区域背景色，选择对比色
  const smartColor = analyzeAreaColor(ctx, sampleX, sampleY, wmWidth, wmHeight)

  // 半透明描边增强可读性
  ctx.shadowColor = 'rgba(0,0,0,0.4)'
  ctx.shadowBlur = 6
  ctx.globalAlpha = 0.65
  ctx.fillStyle = smartColor
  ctx.fillText(payload.watermarkText, drawX, drawY)
  ctx.restore()
}

/**
 * @description 完整导出视频
 * @param {Object} payload - 导出参数对象
 * @param {string} payload.videoData - 视频源（base64 data URL，视频或图片）
 * @param {string} payload.audioData - 音频源
 * @param {string} payload.fontFamily - 字体名称
 * @param {boolean} [payload.pingPong=false] - 是否启用往返循环播放逻辑
 * @param {Object[]} payload.subtitleData - 字幕数组，每条包含 start、end、words
 * @param {Object} payload.overlaySettings - 叠加区域配置
 * @param {string} payload.highlightBg - 高亮颜色
 * @param {string} [payload.fontColor='#ffffff'] - 字体颜色
 * @param {number} payload.fontSize - 字体大小比例
 * @param {number} payload.lineHeightMult - 行高倍数
 * @param {number} payload.bgScale - 高亮背景缩放比例
 * @param {string} [payload.watermarkText] - 水印文本
 * @param {string} [payload.watermarkPosition='bottom-right'] - 水印位置
 * @param {string} [payload.particleEffect='none'] - 粒子特效类型
 * @param {number} [payload.batchIndex=0] - 批量导出索引
 * @returns {Promise} 导出完成后通过 chrome.runtime 消息发送 Blob URL
 */
async function startExport (payload) {
  const { pingPong } = payload

  // 判断是否为图片文件
  const isImage = payload.videoData.startsWith('data:image/')

  // 加载字体
  await loadFont(payload.fontFamily)

  // 设置音频源
  audioSource.src = payload.audioData

  let imgElement = null

  if (isImage) {
    // 图片直接加载为 HTMLImageElement
    imgElement = await new Promise((resolve, reject) => {
      const img = new Image()
      img.onload = () => resolve(img)
      img.onerror = reject
      img.src = payload.videoData
    })
    canvas.width = imgElement.naturalWidth
    canvas.height = imgElement.naturalHeight
    // 只等音频元数据
    await new Promise(res => {
      audioSource.onloadedmetadata = res
    })
  } else {
    // 设置视频源并等待视频和音频元数据加载完成
    videoSource.src = payload.videoData
    await Promise.all([
      new Promise(res => {
        videoSource.onloadedmetadata = res
      }),
      new Promise(res => {
        audioSource.onloadedmetadata = res
      })
    ])
    // 设置 canvas 尺寸与视频一致
    canvas.width = videoSource.videoWidth
    canvas.height = videoSource.videoHeight
  }

  // 重新注册一次字体，避免字体失效
  await reAddFonts()

  const audioDuration = audioSource.duration
  const videoDuration = videoSource.duration
  const FPS = 30
  const sampleRate = 44100
  const totalFrames = Math.ceil(audioDuration * FPS)

  // 预渲染音频为 PCM buffer
  console.log('预渲染音频...')
  const rawAudioBuffer = await dataURLToArrayBuffer(payload.audioData)
  const offlineCtx = new OfflineAudioContext(2, Math.ceil(audioDuration * sampleRate), sampleRate)
  const decodedAudio = await offlineCtx.decodeAudioData(rawAudioBuffer)
  const offlineSrc = offlineCtx.createBufferSource()
  offlineSrc.buffer = decodedAudio
  offlineSrc.connect(offlineCtx.destination)
  offlineSrc.start()
  const renderedAudioBuffer = await offlineCtx.startRendering()
  console.log('音频预渲染完成', renderedAudioBuffer.duration.toFixed(2), 's')

  // 提取左右声道 PCM 数据
  const leftChannel = renderedAudioBuffer.getChannelData(0)
  const rightChannel = renderedAudioBuffer.numberOfChannels > 1 ? renderedAudioBuffer.getChannelData(1) : leftChannel

  // 初始化 WebM Muxer
  const muxer = new WebMMuxer.Muxer({
    target: new WebMMuxer.ArrayBufferTarget(),
    video: {
      codec: 'V_VP9',
      width: canvas.width,
      height: canvas.height,
      frameRate: FPS
    },
    audio: {
      codec: 'A_OPUS',
      sampleRate,
      numberOfChannels: 2
    },
    firstTimestampBehavior: 'offset'
  })

  // 初始化 VideoEncoder
  const videoEncoder = new VideoEncoder({
    output: (chunk, meta) => {
      muxer.addVideoChunk(chunk, meta)
    },
    error: e => console.error('VideoEncoder 错误:', e)
  })

  videoEncoder.configure({
    codec: 'vp09.00.10.08',
    width: canvas.width,
    height: canvas.height,
    bitrate: 10_000_000,
    framerate: FPS
  })

  // 初始化 AudioEncoder
  const audioChunkFrames = 960
  const audioEncoder = new AudioEncoder({
    output: (chunk, meta) => {
      muxer.addAudioChunk(chunk, meta)
    },
    error: e => console.error('AudioEncoder 错误:', e)
  })

  audioEncoder.configure({
    codec: 'opus',
    sampleRate,
    numberOfChannels: 2,
    bitrate: 128_000
  })

  // 把音频 chunk 传入 AudioEncoder 编码
  console.log('编码音频...')
  const totalAudioSamples = leftChannel.length
  for (let offset = 0; offset < totalAudioSamples; offset += audioChunkFrames) {
    const frameCount = Math.min(audioChunkFrames, totalAudioSamples - offset)
    const timestampUs = Math.round((offset / sampleRate) * 1_000_000)

    const planar = new Float32Array(frameCount * 2)
    planar.set(leftChannel.subarray(offset, offset + frameCount), 0)
    planar.set(rightChannel.subarray(offset, offset + frameCount), frameCount)

    const audioData = new AudioData({
      format: 'f32-planar',
      sampleRate,
      numberOfFrames: frameCount,
      numberOfChannels: 2,
      timestamp: timestampUs,
      data: planar
    })

    audioEncoder.encode(audioData)
    audioData.close()

    // 每隔一定数量帧让出主线程
    if (offset % (audioChunkFrames * 100) === 0) {
      await new Promise(res => setTimeout(res, 0))
    }
  }

  await audioEncoder.flush()
  console.log('音频编码完成')

  // 初始化粒子（导出渲染用，与预览粒子数量一致）
  const effect = payload.particleEffect || 'none'
  const exportParticleCount = 160
  const exportParticles = effect !== 'none' ? Array.from({ length: exportParticleCount }, () => new Particle(canvas.width, canvas.height, effect, true)) : []

  // 逐帧渲染视频
  console.log('开始渲染视频帧...')

  // 图片模式不需要 seek，视频模式初始化到第 0 帧
  if (!isImage) {
    videoSource.currentTime = 0
    await seekTo(0)
  }

  let debugFrameDone = false

  for (let frameIndex = 0; frameIndex < totalFrames; frameIndex++) {
    const elapsed = frameIndex / FPS
    const timestampUs = Math.round(elapsed * 1_000_000)
    const durationUs = Math.round(1_000_000 / FPS)

    if (isImage) {
      // 图片每帧直接绘制，不需要 seek
      ctx.drawImage(imgElement, 0, 0, canvas.width, canvas.height)
    } else {
      // 支持正反循环逻辑
      let videoT = elapsed % videoDuration
      if (pingPong) {
        const cycle = Math.floor(elapsed / videoDuration)
        videoT = cycle % 2 === 1 ? videoDuration - (elapsed % videoDuration) : elapsed % videoDuration
      }
      await seekTo(videoT)
      ctx.drawImage(videoSource, 0, 0, canvas.width, canvas.height)
    }

    // 绘制粒子特效层
    if (effect !== 'none') {
      exportParticles.forEach(p => {
        p.update(1)
        p.draw(ctx)
      })
    }

    drawSubtitle(elapsed, payload)

    // 绘制字幕与水印
    drawWatermark(payload)

    if (!debugFrameDone && elapsed > 0.5) {
      debugFrameDone = true
    }

    // 每隔 30 帧插入一个关键帧
    const keyFrame = frameIndex % 30 === 0

    const videoFrame = new VideoFrame(canvas, {
      timestamp: timestampUs,
      duration: durationUs
    })

    videoEncoder.encode(videoFrame, { keyFrame })
    videoFrame.close()

    // 当前视频渲染进度
    chrome.runtime.sendMessage({
      type: 'export-progress',
      progress: elapsed / audioDuration
    })

    // 每帧让出主线程，防止阻塞
    await new Promise(r => setTimeout(r, 0))
  }

  await videoEncoder.flush()
  console.log('视频帧编码完成')

  // 封装并导出 WebM
  muxer.finalize()

  const { buffer } = muxer.target
  const blob = new Blob([buffer], { type: 'video/webm' })
  const blobUrl = URL.createObjectURL(blob)

  console.log('完成，大小:', (blob.size / 1024 / 1024).toFixed(2), 'MB')

  // 将 blob URL 和批次信息发送给 background.js 下载
  chrome.runtime.sendMessage({
    type: 'export-done',
    blobUrl,
    batchIndex: payload.batchIndex !== undefined ? payload.batchIndex : 0
  })
}

chrome.runtime.onMessage.addListener(msg => {
  if (msg.type === 'do-export') {
    console.log('do-export', Object.keys(msg.payload))
    startExport(msg.payload)
  }
})
