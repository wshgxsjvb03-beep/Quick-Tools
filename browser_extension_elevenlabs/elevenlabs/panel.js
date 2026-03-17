// ElevenLabs 极简助手 (独立软件增强版 v3.1)
(function() {
  console.log("ElevenLabs Minimalist standalone-ready UI Loaded.");

  let state = {
    tasks: [],
    isProcessing: false,
    isConnected: false,
    defaultVoiceId: "JBFqnCBsd6RMkjVDRZzb",
    defaultModelId: "eleven_v3"
  };

  async function init() {
    if (document.getElementById('qt-elevenlabs-panel')) return;
    
    // 1. 从存储恢复任务
    const saved = await chrome.storage.local.get(['qt_batch_tasks']);
    if (saved.qt_batch_tasks) {
      state.tasks = saved.qt_batch_tasks;
    }

    injectUI();
    bindEvents();
    render();
    
    // 2. 持续监测连接状态
    checkConnection();
    setInterval(checkConnection, 5000);
  }

  function injectUI() {
    const trigger = document.createElement('div');
    trigger.className = 'qt-toggle-trigger';
    trigger.innerText = '批量助手';
    trigger.onclick = () => document.getElementById('qt-elevenlabs-panel').classList.toggle('minimized');
    document.body.appendChild(trigger);

    const panel = document.createElement('div');
    panel.id = 'qt-elevenlabs-panel';
    panel.className = 'qt-elevenlabs-panel minimized';
    panel.innerHTML = `
      <div class="qt-header">
        <span id="qt-header-title">🚀 批量生成 (就绪)</span>
        <div style="display:flex; align-items:center; gap:8px;">
           <div id="qt-conn-indicator" style="width:8px; height:8px; border-radius:50%; background:#555;" title="检查主程序连接..."></div>
           <button id="qt-hide-btn" style="background:none; border:none; color:#888; cursor:pointer; font-size:16px;">✖</button>
        </div>
      </div>
      
      <div class="qt-toolbar">
         <button class="qt-btn" id="qt-add-btn">➕ 新建任务</button>
         <button class="qt-btn" id="qt-batch-btn">🚀 批量导入</button>
         <div style="flex:1"></div>
         <button class="qt-btn" id="qt-clear-btn" style="background:#822;">🧹 清空列表</button>
      </div>

      <div class="qt-table-container">
        <table class="qt-table" id="qt-task-table">
          <thead>
            <tr>
              <th width="100">文件名</th>
              <th width="300">文案内容</th>
              <th width="120">Voice ID</th>
              <th width="40">操作</th>
            </tr>
          </thead>
          <tbody id="qt-tbody"></tbody>
        </table>
      </div>

      <div class="qt-footer">
        <div id="qt-status" style="font-size:12px; color:#888;">正在加载...</div>
        <button class="qt-btn qt-btn-run" id="qt-start-btn">开始排列生成音频</button>
      </div>
    `;
    document.body.appendChild(panel);
    makeDraggable(panel, panel.querySelector('.qt-header'));
  }

  function bindEvents() {
    document.getElementById('qt-hide-btn').onclick = () => document.getElementById('qt-elevenlabs-panel').classList.add('minimized');
    
    document.getElementById('qt-add-btn').onclick = () => {
      state.tasks.push({ id: Date.now(), name: 'audio_' + (state.tasks.length+1), content: '', voice_id: state.defaultVoiceId, status: 'pending' });
      saveState();
      render();
    };

    document.getElementById('qt-batch-btn').onclick = () => {
      const text = prompt("请按：'文件名|文案' 格式导入，一行一个：\n例如：\n001|第一句话 \n002|第二句话");
      if (!text) return;
      text.split('\n').forEach(line => {
        if (!line.trim()) return;
        const p = line.split('|');
        state.tasks.push({
          id: Math.random(),
          name: p[0] ? p[0].trim() : 'audio',
          content: p[1] ? p[1].trim() : line.trim(),
          voice_id: state.defaultVoiceId,
          status: 'pending'
        });
      });
      saveState();
      render();
    };

    document.getElementById('qt-clear-btn').onclick = () => {
      if(confirm("确定清空任务列表吗？")) {
        state.tasks = [];
        saveState();
        render();
      }
    };

    document.getElementById('qt-start-btn').onclick = startBatchOperation;
  }

  function saveState() {
     chrome.storage.local.set({ qt_batch_tasks: state.tasks });
  }

  function checkConnection() {
    chrome.runtime.sendMessage({ action: "get_status" }, (res) => {
      if (res) {
        state.isConnected = res.connected;
        const indicator = document.getElementById('qt-conn-indicator');
        const title = document.getElementById('qt-header-title');
        
        if (state.isConnected) {
          indicator.style.background = '#10b981'; // 绿色
          indicator.title = "已同步主程序：音频将保存至本地文件夹";
          title.innerText = "🚀 批量生成 (已同步本地)";
        } else {
          indicator.style.background = '#fbbf24'; // 黄色
          indicator.title = "独立模式：音频将保存至下载目录";
          title.innerText = "🚀 批量生成 (独立软件模式)";
        }
      }
    });
  }

  function render() {
    const tbody = document.getElementById('qt-tbody');
    tbody.innerHTML = '';

    state.tasks.forEach(task => {
      const tr = document.createElement('tr');
      tr.className = task.status;
      tr.innerHTML = `
        <td><input class="qt-cell-edit" data-id="${task.id}" data-field="name" value="${task.name}"></td>
        <td><input class="qt-cell-edit" data-id="${task.id}" data-field="content" value="${task.content}"></td>
        <td><input class="qt-cell-edit" data-id="${task.id}" data-field="voice_id" value="${task.voice_id || ''}" placeholder="默认"></td>
        <td align="center"><button class="qt-del-btn" data-id="${task.id}" style="background:none; border:none; cursor:pointer;">🗑️</button></td>
      `;

      tr.querySelectorAll('.qt-cell-edit').forEach(input => {
        input.oninput = (e) => {
          const t = state.tasks.find(x => x.id == e.target.dataset.id);
          if (t) {
            t[e.target.dataset.field] = e.target.value;
            saveState();
          }
        };
      });

      tr.querySelector('.qt-del-btn').onclick = (e) => {
        state.tasks = state.tasks.filter(x => x.id != e.target.dataset.id);
        saveState();
        render();
      };
      tbody.appendChild(tr);
    });

    document.getElementById('qt-status').innerText = `任务: ${state.tasks.length} | 完成: ${state.tasks.filter(t=>t.status==='success').length}`;
    const startBtn = document.getElementById('qt-start-btn');
    startBtn.disabled = state.isProcessing || state.tasks.length === 0;
    startBtn.innerText = state.isProcessing ? "☕ 生成并下载中..." : "开始排列生成音频";
  }

  async function startBatchOperation() {
    if (state.isProcessing) return;
    state.isProcessing = true;
    render();

    for (let i = 0; i < state.tasks.length; i++) {
      let t = state.tasks[i];
      if (t.status === 'success') continue;

      t.status = 'processing';
      render();

      try {
        const result = await new Promise(resolve => {
          chrome.runtime.sendMessage({
            action: "generate_audio_request",
            text: t.content,
            name: t.name,
            voiceId: t.voice_id || state.defaultVoiceId,
            modelId: state.defaultModelId
          }, res => resolve(res || {status: 'error'}));
        });
        t.status = result.status === 'success' ? 'success' : 'error';
        saveState();
      } catch (e) {
        t.status = 'error';
      }
      render();
      await new Promise(r => setTimeout(r, 600));
    }

    state.isProcessing = false;
    render();
    alert(state.isConnected ? "所有音频已同步保存到本地程序。" : "独立模式：所有音频已保存到浏览器下载目录。");
  }

  function makeDraggable(el, handle) {
    let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
    handle.onmousedown = (e) => {
      e.preventDefault();
      pos3 = e.clientX;
      pos4 = e.clientY;
      document.onmouseup = () => { document.onmouseup = null; document.onmousemove = null; };
      document.onmousemove = (e) => {
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;
        el.style.top = (el.offsetTop - pos2) + "px";
        el.style.left = (el.offsetLeft - pos1) + "px";
      };
    };
  }

  setTimeout(init, 500);
})();
