// 插件ID
const extensionID = document.getElementById('elevenlabs').outerText
// 后台通信
const sendBackground = data => new Promise(resolve => chrome.runtime.sendMessage(extensionID, data, res => { resolve(res) }))
// 清空徽标
sendBackground({ action: 'mark', text: '' })
// 备份原生 fetch
const originalFetch = window.fetch

// fetch 监听
function apiListener () {
  const interceptFetch = () => {
    window.fetch = async (url, options) => {
      try {
        if (typeof url === 'string' && url.includes('identitytoolkit.googleapis.com/v1/accounts:lookup')) {
          if (options && options.body) {
            let payload
            if (options.body instanceof FormData) {
              payload = {}
              options.body.forEach((value, key) => {
                payload[key] = value
              })
            } else {
              try {
                payload = JSON.parse(options.body)
              } catch (error) {
                payload = options.body.toString()
              }
            }
            console.log(payload.idToken)
            // 发送 token 到后台
            await sendBackground({
              action: 'token',
              token: payload.idToken
            })
            // 徽标提示已储存 token
            await sendBackground({
              action: 'mark',
              text: '存'
            })
          }
          const response = await originalFetch(url, options)
          return response
        } else {
          return originalFetch(url, options)
        }
      } catch (error) {
        console.error(error)
      }
    }
  }
  const restoreFetch = () => {
    window.fetch = originalFetch
  }
  return {
    hook: interceptFetch,
    unhook: restoreFetch
  }
}
// 默认加载页面后就启用
apiListener().hook()
