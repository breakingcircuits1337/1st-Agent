var PRESETS = {
  home: {
    q: "dim the bedroom lights to 20 percent",
    tools: [
      {
        name: "set_lights",
        description: "Set light brightness for a room.",
        parameters: {
          type: "object",
          properties: {
            room: { type: "string", enum: ["bedroom", "kitchen", "living room", "office"] },
            brightness: { type: "integer", minimum: 0, maximum: 100 },
          },
          required: ["room", "brightness"],
        },
      },
      {
        name: "set_thermostat",
        description: "Set the thermostat target temperature.",
        parameters: {
          type: "object",
          properties: {
            temperature_c: { type: "number", minimum: 10, maximum: 32 },
          },
          required: ["temperature_c"],
        },
      },
    ],
  },
  media: {
    q: "play plastic love on the living room speaker at volume 4",
    tools: [
      {
        name: "play_media",
        description: "Start playback of a track or playlist on a speaker target.",
        parameters: {
          type: "object",
          properties: {
            query: { type: "string" },
            target: { type: "string", enum: ["living room speaker", "bedroom speaker", "kitchen speaker"] },
            volume: { type: "integer", minimum: 1, maximum: 10 },
          },
          required: ["query"],
        },
      },
      {
        name: "pause_media",
        description: "Pause current playback.",
        parameters: { type: "object", properties: {} },
      },
    ],
  },
  productivity: {
    q: "schedule a sync with Sarah tomorrow at 3pm for 30 minutes",
    tools: [
      {
        name: "create_event",
        description: "Create a new calendar event.",
        parameters: {
          type: "object",
          properties: {
            title: { type: "string" },
            start_iso: { type: "string" },
            duration_minutes: { type: "integer" },
          },
          required: ["title", "start_iso"],
        },
      },
      {
        name: "send_message",
        description: "Send a message to a recipient.",
        parameters: {
          type: "object",
          properties: {
            recipient: { type: "string" },
            body: { type: "string" },
          },
          required: ["recipient", "body"],
        },
      },
    ],
  },
  extraction: {
    q: "Invoice INV-2026-882 from Acme Corp, total $1,200.00, due 2026-09-01",
    tools: [
      {
        name: "Invoice",
        description: "Extract structured invoice metadata from text.",
        parameters: {
          type: "object",
          properties: {
            vendor: { type: "string" },
            invoice_id: { type: "string" },
            total: { type: "number" },
            due_date: { type: "string" },
          },
          required: ["vendor", "total"],
        },
      },
    ],
  },
};

var LABELS = {
  home: "Smart Home",
  media: "Media Player",
  productivity: "Productivity",
  extraction: "Structured Extraction",
};

var toastTimer = null;

function showError(msg) {
  var t = document.getElementById("toast");
  document.getElementById("toastMsg").textContent = msg;
  t.classList.add("visible");
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(dismissToast, 6000);
}

function dismissToast() {
  var t = document.getElementById("toast");
  t.classList.remove("visible");
  if (toastTimer) { clearTimeout(toastTimer); toastTimer = null; }
}

function fetchModelName() {
  fetch("/model")
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.name) document.getElementById("modelName").textContent = d.name;
    })
    .catch(function () {});
}

function formatToolsJson() {
  var toolsEl = document.getElementById("tools");
  var val = toolsEl.value.trim();
  if (!val) return;
  try {
    var parsed = JSON.parse(val);
    toolsEl.value = JSON.stringify(parsed, null, 2);
  } catch (e) {
    showError("Invalid tools JSON: " + e.message);
  }
}

function loadToolsFile(input) {
  var file = input.files && input.files[0];
  if (!file) return;
  var reader = new FileReader();
  reader.onload = function (e) {
    var content = e.target.result;
    try {
      var json = JSON.parse(content);
      document.getElementById("tools").value = JSON.stringify(json, null, 2);
    } catch (err) {
      showError("Invalid JSON in uploaded file: " + err.message);
    }
  };
  reader.readAsText(file);
  input.value = "";
}

function loadModelFile(input) {
  var file = input.files && input.files[0];
  if (!file) return;
  var name = document.getElementById("modelName");
  name.textContent = "loading " + file.name + "...";
  fetch("/load-model", { method: "POST", headers: { "X-Filename": file.name }, body: file })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.error) { showError(d.error); fetchModelName(); }
      else { name.textContent = d.name; newChat(); }
    })
    .catch(function (e) { showError("Upload failed: " + e.message); fetchModelName(); });
  input.value = "";
}

var conversation = document.getElementById("conversation");
var emptyState = document.getElementById("emptyState");

function copyToClipboard(text, btnEl) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(function() {
      var orig = btnEl.textContent;
      btnEl.textContent = "Copied!";
      setTimeout(function() { btnEl.textContent = orig; }, 1500);
    }).catch(function() {
      showError("Copy failed");
    });
  }
}

function addTurn(query, data) {
  if (emptyState) { emptyState.remove(); emptyState = null; }
  var turn = document.createElement("div");
  turn.className = "turn";

  var q = document.createElement("div");
  q.className = "turn-query";
  q.textContent = query;
  turn.appendChild(q);

  var resultWrap = document.createElement("div");
  resultWrap.className = "turn-result-wrap";

  var copyBtn = document.createElement("button");
  copyBtn.className = "turn-copy-btn";
  copyBtn.textContent = "Copy";

  var pre = document.createElement("pre");
  pre.className = "turn-result";
  var calls = data.function_calls;
  var formattedResult = "";
  if (data.type === "refuse" || (Array.isArray(calls) && calls.length === 0)) {
    pre.classList.add("refused");
    formattedResult = "no tool call (off-topic / refused)";
    pre.textContent = formattedResult;
  } else {
    formattedResult = JSON.stringify(calls || data, null, 2);
    pre.textContent = formattedResult;
  }

  copyBtn.onclick = function() { copyToClipboard(formattedResult, copyBtn); };

  resultWrap.appendChild(copyBtn);
  resultWrap.appendChild(pre);
  turn.appendChild(resultWrap);

  if (data.reasoning) {
    var reason = document.createElement("div");
    reason.className = "turn-reasoning";
    var label = document.createElement("div");
    label.className = "turn-reasoning-label";
    label.textContent = "Reasoning trace";
    var body = document.createElement("div");
    body.className = "turn-reasoning-body";
    body.textContent = data.reasoning;
    reason.appendChild(label);
    reason.appendChild(body);
    turn.appendChild(reason);
  }

  var bits = [];
  if (data.confidence !== undefined && data.confidence !== null) {
    bits.push("confidence " + Number(data.confidence).toFixed(4));
  }
  if (data.decode_tps) {
    bits.push(Math.round(data.decode_tps) + " tok/s");
  }
  if (bits.length) {
    var meta = document.createElement("div");
    meta.className = "turn-meta";
    meta.textContent = bits.join("  ·  ");
    turn.appendChild(meta);
  }

  conversation.appendChild(turn);
  conversation.scrollTop = conversation.scrollHeight;
}

async function send() {
  var input = document.getElementById("query");
  var btn = document.getElementById("sendBtn");
  var query = input.value.trim();
  if (!query) return;
  var tools = document.getElementById("tools").value.trim() || "[]";
  try { JSON.parse(tools); } catch (e) { showError("Invalid tools JSON"); return; }

  input.disabled = true;
  btn.disabled = true;
  var origBtnText = btn.textContent;
  btn.textContent = "Running...";

  try {
    var r = await fetch("/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, tools: tools }),
    });
    var data = await r.json();
    if (data.error) { showError(data.error); }
    else { addTurn(query, data); input.value = ""; }
  } catch (e) {
    showError("Request failed: " + e.message);
  } finally {
    input.disabled = false;
    btn.disabled = false;
    btn.textContent = origBtnText;
    input.focus();
  }
}

function newChat() {
  fetch("/reset", { method: "POST" }).catch(function () {});
  conversation.innerHTML = "";
  emptyState = document.createElement("div");
  emptyState.className = "empty";
  emptyState.id = "emptyState";
  emptyState.textContent = "Pick a preset or type a query, then Run.";
  conversation.appendChild(emptyState);
}

function applyPreset(key) {
  var p = PRESETS[key];
  document.getElementById("tools").value = JSON.stringify(p.tools, null, 2);
  document.getElementById("query").value = p.q;
  newChat();
  document.getElementById("query").focus();
}

var presetBox = document.getElementById("presets");
Object.keys(LABELS).forEach(function (key) {
  if (!PRESETS[key]) return;
  var b = document.createElement("button");
  b.className = "preset-btn";
  b.textContent = LABELS[key];
  b.onclick = function () { applyPreset(key); };
  presetBox.appendChild(b);
});

function togglePanel() {
  var sidebar = document.getElementById("sidebar");
  sidebar.classList.toggle("open");
  document.querySelector(".tools-toggle span").textContent =
    sidebar.classList.contains("open") ? "Query" : "Tools";
}

var _pollTimer = null;
var _ftRunning = false;

function openFinetuneModal() {
  var tools = document.getElementById("tools").value.trim() || "[]";
  try { JSON.parse(tools); } catch (e) { showError("Invalid tools JSON"); return; }
  _resetModal();
  document.getElementById("modalOverlay").classList.add("visible");
  document.getElementById("ftApiKey").focus();
}

function closeModal(e) {
  if (e && e.target && e.target !== document.getElementById("modalOverlay")) return;
  if (_ftRunning) return;
  document.getElementById("modalOverlay").classList.remove("visible");
}

function _resetModal() {
  document.getElementById("ftSteps").classList.remove("visible");
  document.getElementById("ftProgress").textContent = "";
  var start = document.getElementById("ftStartBtn");
  start.disabled = false;
  start.textContent = "Start Finetune";
  start.style.display = "";
  document.getElementById("modalCloseBtn").style.display = "";
  var dl = document.getElementById("ftDownload");
  if (dl) dl.remove();
  document.querySelectorAll(".modal-step").forEach(function (s) {
    s.classList.remove("active", "done");
  });
}

async function startFinetune() {
  var apiKey = document.getElementById("ftApiKey").value.trim();
  if (!apiKey) { showError("OpenRouter API key is required"); return; }
  var tools = document.getElementById("tools").value.trim() || "[]";
  try { JSON.parse(tools); } catch (e) { showError("Invalid tools JSON"); return; }
  var samples = parseInt(document.getElementById("ftSamples").value, 10) || 200;

  var btn = document.getElementById("ftStartBtn");
  btn.disabled = true;
  btn.textContent = "Starting...";
  document.getElementById("modalCloseBtn").style.display = "none";
  document.getElementById("ftSteps").classList.add("visible");
  _ftRunning = true;

  try {
    var r = await fetch("/finetune", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tools: tools, api_key: apiKey, samples: samples }),
    });
    var data = await r.json();
    if (data.error) { showError(data.error); _ftRunning = false; _resetModal(); return; }
    _pollTimer = setInterval(pollFinetune, 2000);
  } catch (e) {
    showError("Request failed: " + e.message);
    _ftRunning = false;
    _resetModal();
  }
}

function _updateSteps(current) {
  var steps = document.querySelectorAll(".modal-step");
  var past = true;
  steps.forEach(function (s) {
    var name = s.getAttribute("data-step");
    s.classList.remove("active", "done");
    if (name === current) { s.classList.add("active"); past = false; }
    else if (past) { s.classList.add("done"); }
  });
}

var _stepLabels = {
  "generating data": "Generating data...",
  "training": "Training...",
  "building": "Building .cact...",
};

async function pollFinetune() {
  try {
    var r = await fetch("/finetune/status");
    var data = await r.json();
    _updateSteps(data.step);
    var btn = document.getElementById("ftStartBtn");
    btn.textContent = _stepLabels[data.step] || data.step;
    if (data.log && data.log.length)
      document.getElementById("ftProgress").textContent = data.log[data.log.length - 1];

    if (!data.running) {
      clearInterval(_pollTimer);
      _pollTimer = null;
      _ftRunning = false;
      document.getElementById("modalCloseBtn").style.display = "";
      if (data.step === "done") {
        document.querySelectorAll(".modal-step").forEach(function (s) {
          s.classList.remove("active"); s.classList.add("done");
        });
        btn.style.display = "none";
        fetchModelName();
        if (data.checkpoint) {
          var dl = document.createElement("a");
          dl.id = "ftDownload";
          dl.className = "modal-download";
          dl.href = "/download/" + data.checkpoint;
          dl.download = data.checkpoint;
          dl.textContent = "Download " + data.checkpoint;
          document.getElementById("ftFooter").appendChild(dl);
        }
      } else {
        showError("Finetune failed — " + (data.error || "unknown error"));
        btn.textContent = "Retry";
        btn.disabled = false;
      }
    }
  } catch (e) {
    clearInterval(_pollTimer);
    _pollTimer = null;
    _ftRunning = false;
    document.getElementById("modalCloseBtn").style.display = "";
    showError("Lost connection to server");
    document.getElementById("ftStartBtn").textContent = "Retry";
    document.getElementById("ftStartBtn").disabled = false;
  }
}

document.getElementById("query").addEventListener("keydown", function (e) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeModal(); });

(function () {
  var handle = document.getElementById("resizeHandle");
  var sidebar = document.getElementById("sidebar");
  var dragging = false;
  handle.addEventListener("mousedown", function (e) {
    if (window.innerWidth <= 768) return;
    e.preventDefault();
    dragging = true;
    handle.classList.add("active");
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  });
  window.addEventListener("mousemove", function (e) {
    if (!dragging) return;
    sidebar.style.width = Math.min(Math.max(e.clientX, 200), window.innerWidth * 0.6) + "px";
  });
  window.addEventListener("mouseup", function () {
    if (!dragging) return;
    dragging = false;
    handle.classList.remove("active");
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  });
  window.addEventListener("resize", function () {
    if (window.innerWidth <= 768) sidebar.style.width = "";
  });
})();

fetchModelName();
applyPreset("home");
