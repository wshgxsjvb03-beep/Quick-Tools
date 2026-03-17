;(() => {
  const element = document.createElement('div')
  element.innerHTML = chrome.runtime.id
  element.id = 'elevenlabs'
  element.style.display = 'none'
  document.documentElement.appendChild(element)
  const script = document.createElement('script')
  script.src = chrome.runtime.getURL('/elevenlabs/injectFetch.js')
  ;(document.head || document.documentElement).appendChild(script)
})()
