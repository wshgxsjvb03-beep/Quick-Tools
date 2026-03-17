// 粒子类
class Particle {
  /**
   * @param {number} w - Canvas 宽度（用于边界判断）
   * @param {number} h - Canvas 高度
   * @param {string} type - 粒子类型
   * @param {boolean} isInitial - 是否为初始化阶段
   *   true - 在画布内随机分布
   *   false - 从边缘生成
   */
  constructor (w, h, type, isInitial = false) {
    this.w = w
    this.h = h
    this.type = type

    // 根据粒子类型决定运动方向
    // 上浮、下落或随机方向
    const directionMap = {
      'golden-dust': 'up',
      hearts: 'up',
      balloons: 'up',
      notes: 'up',
      bubbles: 'up',

      sakura: 'down',
      feathers: 'down',
      snowflakes: 'down',
      'sakura-flower': 'down'
    }

    this.direction = directionMap[type] || 'random'

    // 呼吸动画的初始相位随机错开，避免同步闪烁
    this.phase = Math.random() * Math.PI * 2
    this.opacity = 1
    this.reset(isInitial)
  }

  /**
   * @description 重置粒子属性
   * @param {boolean} isInitial - 是否在画布内随机生成
   */
  reset (isInitial = false) {
    // 初始旋转角度
    this.rotation = Math.random() * Math.PI * 2
    // 每帧旋转速度
    this.rotateSpeed = (Math.random() - 0.5) * 0.04

    // 基础尺寸
    this.baseSize = Math.random() * 6 + 4
    this.size = this.baseSize

    // 呼吸动画参数
    this.opacityBase = Math.random() * 0.08 + 0.38
    this.opacityRange = Math.random() * 0.12 + 0.2
    // 呼吸频率
    this.breatheSpeed = Math.random() * 0.18 + 0.22
    // 随呼吸产生的尺寸脉冲幅度
    this.scalePulse = Math.random() * 0.06 + 0.02

    // 水平摇摆参数，模拟飘落和飘升时的自然晃动
    this.swingPhase = Math.random() * Math.PI * 2
    this.swingSpeed = Math.random() * 1.0 + 0.35
    this.swingAmp = Math.random() * 0.8 + 0.2

    // 边缘外的缓冲生成区域
    const spawnPadding = 120
    // 生成区域的纵深范围
    const spawnBand = Math.max(220, this.h * 0.3)

    // 决定粒子的初始坐标
    if (isInitial) {
      // 在整个画布内随机分布，避免画面初始时粒子为空
      this.x = Math.random() * this.w
      this.y = Math.random() * this.h
    } else {
      // 根据运动方向从对应边缘外生成
      if (this.direction === 'up') {
        this.x = Math.random() * this.w
        // 从底部外侧生成
        this.y = this.h + spawnPadding + Math.random() * spawnBand
      } else if (this.direction === 'down') {
        this.x = Math.random() * this.w
        // 从顶部外侧生成
        this.y = -spawnPadding - Math.random() * spawnBand
      } else {
        // 随机方向
        const side = Math.floor(Math.random() * 4)
        if (side === 0) {
          this.x = Math.random() * this.w
          this.y = -spawnPadding - Math.random() * spawnBand
        } else if (side === 1) {
          this.x = this.w + spawnPadding + Math.random() * spawnBand
          this.y = Math.random() * this.h
        } else if (side === 2) {
          this.x = Math.random() * this.w
          this.y = this.h + spawnPadding + Math.random() * spawnBand
        } else {
          this.x = -spawnPadding - Math.random() * spawnBand
          this.y = Math.random() * this.h
        }
      }
    }

    // 各粒子类型的独立配置
    switch (this.type) {
      case 'golden-dust': // 金色斑点
        this.shape = 'circle'
        this.color = '255, 215, 0'
        this.speedY = -(Math.random() * 1.5 + 0.5) // 负值 = 向上
        this.speedX = (Math.random() - 0.5) * 0.5
        this.opacityBase = 0.42
        this.opacityRange = 0.84
        this.breatheSpeed = Math.random() * 0.12 + 0.22
        this.scalePulse = 0.045
        break

      case 'starlight': // 白色五角星
        this.shape = 'star'
        this.color = '255, 255, 255'
        this.speedY = (Math.random() - 0.5) * 0.4
        this.speedX = (Math.random() - 0.5) * 0.4
        this.opacityBase = 0.4
        this.opacityRange = 0.86
        this.breatheSpeed = Math.random() * 0.14 + 0.24
        this.scalePulse = 0.055
        break

      case 'fireflies': // 萤火虫
        this.shape = 'circle'
        this.color = '173, 255, 47'
        this.speedY = (Math.random() - 0.5) * 0.8
        this.speedX = (Math.random() - 0.5) * 0.8
        this.opacityBase = 0.4
        this.opacityRange = 0.86
        this.breatheSpeed = Math.random() * 0.14 + 0.22
        this.scalePulse = 0.05
        break

      case 'sakura': // 樱花花瓣
        this.shape = 'leaf'
        this.color = '255, 183, 197'
        this.speedY = Math.random() * 1.5 + 0.5 // 正值 = 向下
        this.speedX = (Math.random() - 0.2) * 1.0 // 略微偏右飘落
        this.opacityBase = 0.4
        this.opacityRange = 0.84
        this.breatheSpeed = Math.random() * 0.08 + 0.14
        this.scalePulse = 0.02
        break

      case 'sakura-flower': // 樱花花朵
        this.shape = 'flower'
        this.color = '255, 192, 203'
        this.speedY = Math.random() * 1.0 + 0.4
        this.speedX = Math.sin(Math.random()) * 0.8
        this.baseSize = Math.random() * 10 + 10
        this.size = this.baseSize
        this.opacityBase = 0.42
        this.opacityRange = 0.82
        this.breatheSpeed = Math.random() * 0.08 + 0.14
        this.scalePulse = 0.018
        break

      case 'feathers': // 羽毛
        this.shape = 'feather'
        this.color = '255, 255, 255'
        this.speedY = Math.random() * 0.8 + 0.3
        this.speedX = (Math.random() - 0.5) * 0.6
        this.baseSize = Math.random() * 10 + 6
        this.size = this.baseSize
        this.opacityBase = 0.5
        this.opacityRange = 0.8
        this.breatheSpeed = Math.random() * 0.06 + 0.12
        this.scalePulse = 0.015
        break

      case 'hearts': // 爱心
        this.shape = 'heart'
        this.color = '255, 50, 50'
        this.speedY = -(Math.random() * 1.5 + 0.5)
        this.speedX = (Math.random() - 0.5) * 0.6
        this.opacityBase = 0.44
        this.opacityRange = 0.81
        this.breatheSpeed = Math.random() * 0.08 + 0.18
        this.scalePulse = 0.03
        break

      case 'snowflakes': // 雪花
        this.shape = 'flake'
        this.color = '200, 240, 255'
        this.speedY = Math.random() * 2.0 + 0.5
        this.speedX = (Math.random() - 0.5) * 1.5
        this.opacityBase = 0.36
        this.opacityRange = 0.82
        this.breatheSpeed = Math.random() * 0.06 + 0.12
        this.scalePulse = 0.018
        break

      case 'balloons': // 彩色气球
        this.shape = 'circle'
        {
          const cs = ['255,99,71', '135,206,235', '255,215,0']
          this.color = cs[Math.floor(Math.random() * cs.length)] // 随机选红/蓝/黄
        }
        this.speedY = -(Math.random() * 2.0 + 1.0)
        this.speedX = Math.sin(this.y * 0.01) * 0.8 // 水平速度随 y 坐标正弦变化，模拟飘动
        this.baseSize = Math.random() * 12 + 8
        this.size = this.baseSize
        this.opacityBase = 0.24
        this.opacityRange = 0.48
        this.breatheSpeed = Math.random() * 0.06 + 0.12
        this.scalePulse = 0.015
        break

      case 'notes': // 音符
        this.shape = 'text'
        {
          const ns = ['♪', '♫', '♬']
          this.text = ns[Math.floor(Math.random() * ns.length)]
        }
        this.color = '255, 255, 255'
        this.speedY = -(Math.random() * 1.2 + 0.5)
        this.speedX = (Math.random() - 0.5) * 1.0
        this.baseSize = 24
        this.size = this.baseSize
        this.opacityBase = 0.3
        this.opacityRange = 0.75
        this.breatheSpeed = Math.random() * 0.08 + 0.16
        this.scalePulse = 0.025
        break

      case 'bubbles': // 气泡
        this.shape = 'ring'
        this.color = '255, 255, 255'
        this.speedY = -(Math.random() * 2.0 + 0.5)
        this.speedX = (Math.random() - 0.5) * 0.5
        this.baseSize = Math.random() * 10 + 5
        this.size = this.baseSize
        this.opacityBase = 0.12
        this.opacityRange = 0.8
        this.breatheSpeed = Math.random() * 0.06 + 0.12
        this.scalePulse = 0.018
        break

      case 'pixels': // 像素方块
        this.shape = 'rect'
        this.color = '255,255,255'
        this.speedY = (Math.random() - 0.5) * 1.2
        this.speedX = (Math.random() - 0.5) * 1.2
        this.baseSize = Math.random() * 8 + 4
        this.size = this.baseSize
        this.opacityBase = 0.16
        this.opacityRange = 0.76
        this.breatheSpeed = Math.random() * 0.08 + 0.16
        this.scalePulse = 0.125 // 尺寸脉冲更明显，产生闪烁感
        break

      case 'golden-rays': // 星芒
        this.shape = 'rays'
        this.color = '255, 210, 50'
        this.speedY = (Math.random() - 0.5) * 0.6
        this.speedX = (Math.random() - 0.5) * 0.6
        this.baseSize = Math.random() * 12 + 8
        this.size = this.baseSize
        this.opacityBase = 0.55
        this.opacityRange = 0.35
        this.breatheSpeed = Math.random() * 0.1 + 0.18
        this.scalePulse = 0.08
        this.rotateSpeed = (Math.random() - 0.5) * 0.012 // 缓慢旋转
        break

      default: // 默认向上的白色圆点
        this.shape = 'circle'
        this.color = '255,255,255'
        this.speedY = -(Math.random() * 0.6 + 0.2)
        this.speedX = (Math.random() - 0.5) * 0.2
        break
    }

    this.opacity = this.opacityBase
  }

  /**
   * @description 每帧更新粒子状态
   * @param {number} dt - 时间增量
   */
  update (dt = 1) {
    // 推进呼吸动画和摇摆动画的相位
    this.phase += 0.014 * this.breatheSpeed * dt
    this.swingPhase += 0.012 * this.swingSpeed * dt
    this.rotation += this.rotateSpeed * dt

    // 计算本帧水平漂移量
    const driftX = Math.sin(this.swingPhase) * this.swingAmp * 0.03
    this.y += this.speedY * dt
    this.x += (this.speedX + driftX) * dt

    // 用余弦缓动使 opacity/size 变化更平滑
    const pulse = (Math.sin(this.phase) + 1) / 2
    const eased = 0.5 - 0.5 * Math.cos(pulse * Math.PI)

    this.opacity = this.opacityBase + eased * this.opacityRange
    this.size = this.baseSize * (1 + eased * this.scalePulse)

    // 判断粒子是否已飞出画布边界
    const pad = Math.max(220, this.size * 8)
    const out = this.x < -pad || this.x > this.w + pad || this.y < -pad || this.y > this.h + pad

    if (out) this.reset(false) // 飞出边界后从另一侧边缘重新生成
  }

  /**
   * @description 将粒子绘制到 Canvas 上
   * @param {CanvasRenderingContext2D} ctx
   */
  draw (ctx) {
    ctx.save()
    // 移动原点到粒子位置
    ctx.translate(this.x, this.y)
    ctx.rotate(this.rotation)

    // 限制透明度下限
    const alpha = Math.max(0.22, Math.min(1, this.opacity))
    ctx.globalAlpha = alpha
    ctx.fillStyle = `rgba(${this.color}, ${Math.min(1, alpha * 0.96 + 0.05)})`
    ctx.strokeStyle = `rgba(${this.color}, ${Math.min(1, alpha * 0.97)})`
    // 发光效果半径与粒子尺寸成比例
    ctx.shadowBlur = this.size * 1.0
    ctx.shadowColor = `rgba(${this.color}, ${Math.max(0.35, alpha)})`

    // 羽毛和星芒不需要太强的发光，减弱 shadowBlur
    if (this.shape === 'rays' || this.shape === 'feather') {
      ctx.shadowBlur = this.size * 0.4
    }

    // 根据形状类型调用对应的绘制逻辑
    switch (this.shape) {
      case 'circle': // 实心圆
        ctx.beginPath()
        ctx.arc(0, 0, this.size, 0, Math.PI * 2)
        ctx.fill()
        break

      case 'star': // 五角星
        this.drawStar(ctx, 0, 0, 5, this.size, this.size / 2)
        ctx.fill()
        break

      case 'heart': // 心形
        this.drawHeart(ctx, 0, 0, this.size)
        ctx.fill()
        break

      case 'flower': // 花朵
        this.drawFlower(ctx, 0, 0, 5, this.size)
        ctx.fill()
        break

      case 'leaf': // 叶片/花瓣
        ctx.beginPath()
        ctx.ellipse(0, 0, this.size, this.size / 2, 0, 0, Math.PI * 2)
        ctx.fill()
        break

      case 'feather': // 羽毛
        this.drawFeather(ctx, 0, 0, this.size)
        break

      case 'text': // 文字粒子
        ctx.font = `bold ${this.size}px Arial`
        ctx.fillText(this.text, 0, 0)
        break

      case 'flake': // 雪花
        this.drawStar(ctx, 0, 0, 6, this.size, this.size / 4)
        ctx.lineWidth = 2
        ctx.stroke()
        break

      case 'ring': // 空心圆环
        ctx.beginPath()
        ctx.arc(0, 0, this.size, 0, Math.PI * 2)
        ctx.lineWidth = 2
        ctx.stroke()
        break

      case 'rect': // 方块
        ctx.fillRect(-this.size / 2, -this.size / 2, this.size, this.size)
        break

      case 'rays': // 星芒
        this.drawRays(ctx, 0, 0, this.size)
        break
    }

    ctx.restore()
  }

  /**
   * @description 绘制多角星形路径
   * @param {number} spikes - 角的数量
   * @param {number} outer - 外半径
   * @param {number} inner - 内半径
   */
  drawStar (ctx, x, y, spikes, outer, inner) {
    // 从顶部开始绘制
    let rot = (Math.PI / 2) * 3
    const step = Math.PI / spikes
    ctx.beginPath()
    ctx.moveTo(x, y - outer)
    for (let i = 0; i < spikes; i++) {
      // 外顶点
      ctx.lineTo(x + Math.cos(rot) * outer, y + Math.sin(rot) * outer)
      rot += step
      // 内凹点
      ctx.lineTo(x + Math.cos(rot) * inner, y + Math.sin(rot) * inner)
      rot += step
    }
    ctx.closePath()
  }

  /**
   * @description 绘制心形路径
   * @param {number} size - 心形尺寸
   */
  drawHeart (ctx, x, y, size) {
    ctx.beginPath()
    ctx.moveTo(x, y + size / 4)
    // 左半心
    ctx.bezierCurveTo(x, y, x - size, y, x - size, y + size / 2)
    ctx.bezierCurveTo(x - size, y + size, x, y + size * 1.5, x, y + size * 1.5)
    // 右半心
    ctx.bezierCurveTo(x, y + size * 1.5, x + size, y + size, x + size, y + size / 2)
    ctx.bezierCurveTo(x + size, y, x, y, x, y + size / 4)
  }

  /**
   * @description 绘制花朵路径
   * @param {number} petals - 花瓣数量
   * @param {number} size - 花朵尺寸
   */
  drawFlower (ctx, x, y, petals, size) {
    ctx.beginPath()
    for (let i = 0; i < petals; i++) {
      ctx.save()
      // 每片花瓣均匀旋转分布
      ctx.rotate((i * 2 * Math.PI) / petals)
      ctx.moveTo(0, 0)
      ctx.bezierCurveTo(-size / 2, -size / 2, -size, size / 4, 0, size)
      ctx.bezierCurveTo(size, size / 4, size / 2, -size / 2, 0, 0)
      ctx.restore()
    }
    ctx.closePath()
  }

  /**
   * @description 绘制羽毛形状
   * @param {number} size - 羽毛基础尺寸
   */
  drawFeather (ctx, x, y, size) {
    // 羽毛总长度
    const len = size * 2.2
    // 羽毛最大宽度
    const width = size * 0.55

    // 外轮廓（羽片）
    ctx.beginPath()
    ctx.moveTo(x, y + len / 2)
    ctx.bezierCurveTo(x - width, y + len * 0.2, x - width * 0.6, y - len * 0.15, x, y - len / 2)
    ctx.bezierCurveTo(x + width * 0.6, y - len * 0.15, x + width, y + len * 0.2, x, y + len / 2)
    ctx.closePath()
    ctx.fill()

    ctx.beginPath()
    ctx.moveTo(x, y + len / 2)
    ctx.quadraticCurveTo(x + size * 0.1, y, x, y - len / 2)
    ctx.lineWidth = size * 0.07
    ctx.globalAlpha = Math.min(1, ctx.globalAlpha * 1.3)
    ctx.stroke()
  }

  /**
   * @description 绘制星芒效果
   * @param {number} size - 光芒基础半径
   */
  drawRays (ctx, x, y, size) {
    const spikes = 8
    // 每条光芒之间的角度间隔
    const step = (Math.PI * 2) / spikes

    // 外层长芒
    ctx.beginPath()
    for (let i = 0; i < spikes; i++) {
      const angle = i * step
      // 芒尖坐标
      const ox = x + Math.cos(angle) * size * 2.2
      const oy = y + Math.sin(angle) * size * 2.2
      // 芒根左侧
      const lx1 = x + Math.cos(angle - 0.12) * size * 0.3
      const ly1 = y + Math.sin(angle - 0.12) * size * 0.3
      // 芒根右侧
      const lx2 = x + Math.cos(angle + 0.12) * size * 0.3
      const ly2 = y + Math.sin(angle + 0.12) * size * 0.3
      ctx.moveTo(lx1, ly1)
      ctx.lineTo(ox, oy)
      ctx.lineTo(lx2, ly2)
      ctx.closePath()
    }
    ctx.fill()

    // 内层短星芒
    // 内层更透明
    ctx.globalAlpha = ctx.globalAlpha * 0.6
    ctx.beginPath()
    for (let i = 0; i < spikes; i++) {
      // 错位半长
      const angle = i * step + step / 2
      const ox = x + Math.cos(angle) * size * 1.2
      const oy = y + Math.sin(angle) * size * 1.2
      const lx1 = x + Math.cos(angle - 0.15) * size * 0.2
      const ly1 = y + Math.sin(angle - 0.15) * size * 0.2
      const lx2 = x + Math.cos(angle + 0.15) * size * 0.2
      const ly2 = y + Math.sin(angle + 0.15) * size * 0.2
      ctx.moveTo(lx1, ly1)
      ctx.lineTo(ox, oy)
      ctx.lineTo(lx2, ly2)
      ctx.closePath()
    }
    ctx.fill()

    // 中心圆核
    // 恢复到内层前的透明度
    ctx.globalAlpha = Math.min(1, ctx.globalAlpha / 0.6)
    ctx.beginPath()
    ctx.arc(x, y, size * 0.28, 0, Math.PI * 2)
    ctx.fill()
  }
}

/**
 * @description 分析区域颜色并返回合适的水印颜色
 * @param {CanvasRenderingContext2D} ctx - Canvas 2D 绘图上下文
 * @param {number} x - 分析区域左上角的 X 坐标
 * @param {number} y - 分析区域左上角的 Y 坐标
 * @param {number} width - 分析区域宽度
 * @param {number} height - 分析区域高度
 * @returns {string} 根据背景颜色计算得到的适合显示水印的 RGB 颜色字符串
 */
function analyzeAreaColor (ctx, x, y, width, height) {
  // 确保分析区域在画布范围内
  x = Math.max(0, x)
  y = Math.max(0, y)
  width = Math.min(ctx.canvas.width - x, width)
  height = Math.min(ctx.canvas.height - y, height)

  // 如果区域太小，返回默认颜色
  if (width <= 0 || height <= 0) {
    return '#ffffff'
  }

  const imageData = ctx.getImageData(x, y, width, height)
  const data = imageData.data
  let totalR = 0
  let totalG = 0
  let totalB = 0

  // 计算区域平均颜色
  for (let i = 0; i < data.length; i += 4) {
    totalR += data[i]
    totalG += data[i + 1]
    totalB += data[i + 2]
  }

  const pixels = data.length / 4
  const avgR = totalR / pixels
  const avgG = totalG / pixels
  const avgB = totalB / pixels

  // 计算亮度 (使用相对亮度公式)
  const brightness = (avgR * 0.299 + avgG * 0.587 + avgB * 0.114) / 255

  // 计算背景色的HSL值
  const [h, s, l] = rgbToHsl(avgR, avgG, avgB)

  // 根据背景颜色决定水印颜色并增加对比度
  if (brightness > 0.5) {
    // 如果背景偏亮，使用深色水印
    // 保持色相，增加饱和度，大幅降低亮度
    const [r, g, b] = hslToRgb(h, 0.8, 0.1)
    return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`
  } else {
    // 如果背景偏暗，使用亮色水印
    // 保持色相，降低饱和度，大幅提高亮度
    const [r, g, b] = hslToRgb(h, 0.2, 0.9)
    return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`
  }
}

/**
 * @description 将 RGB 转换为 HSL
 * @param {number} r - 红色通道值，范围 0 到 255
 * @param {number} g - 绿色通道值，范围 0 到 255
 * @param {number} b - 蓝色通道值，范围 0 到 255
 * @returns {number[]} 返回 HSL 数组，包含色相 h、饱和度 s、亮度 l，范围均为 0 到 1
 */
function rgbToHsl (r, g, b) {
  r /= 255
  g /= 255
  b /= 255

  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  let h
  let s
  const l = (max + min) / 2

  if (max === min) {
    h = s = 0
  } else {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)

    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0)
        break
      case g:
        h = (b - r) / d + 2
        break
      case b:
        h = (r - g) / d + 4
        break
    }

    h /= 6
  }

  return [h, s, l]
}

/**
 * @description 将 HSL 转换为 RGB
 * @param {number} h - 色相值，范围 0 到 1
 * @param {number} s - 饱和度值，范围 0 到 1
 * @param {number} l - 亮度值，范围 0 到 1
 * @returns {number[]} 返回 RGB 数组，包含 r、g、b 三个通道值，范围 0 到 255
 */
function hslToRgb (h, s, l) {
  let r, g, b

  if (s === 0) {
    r = g = b = l
  } else {
    const hue2rgb = (p, q, t) => {
      if (t < 0) t += 1
      if (t > 1) t -= 1
      if (t < 1 / 6) return p + (q - p) * 6 * t
      if (t < 1 / 2) return q
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6
      return p
    }

    const q = l < 0.5 ? l * (1 + s) : l + s - l * s
    const p = 2 * l - q

    r = hue2rgb(p, q, h + 1 / 3)
    g = hue2rgb(p, q, h)
    b = hue2rgb(p, q, h - 1 / 3)
  }

  return [r * 255, g * 255, b * 255]
}
