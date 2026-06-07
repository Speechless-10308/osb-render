/* ============================================================
   OSBoard — Application Logic
   ============================================================ */

const state = {
  rendering: false,
  linkLocked: true,
  aspectRatio: 1920 / 1080,
  pollTimer: null,
  saveTimeout: null,
  config: null,
  logBuffer: [],
};

let $ = () => {};

// ------------------------------------------------------------------
// Init
// ------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
  $ = (sel) => document.querySelector(sel);

  try { state.config = await pywebview.api.load_config(); } catch (e) {}

  const theme = (state.config && state.config.app && state.config.app.theme) || "dark";
  applyTheme(theme);

  try {
    const init = await pywebview.api.get_initial_state();
    applyInitialState(init);
  } catch (e) {}

  bindNavButtons();
  bindSidebarToggle();
  bindThemeToggle();
  bindHomePage();
  bindSettingsPage();
});

// ------------------------------------------------------------------
// Initial state
// ------------------------------------------------------------------
function applyInitialState(init) {
  if (!init) return;
  setVal("#osuPath", init.osu_path || "");
  setVal("#outputPath", init.output_path || "");
  setVal("#resWidth", init.width || 1920);
  setVal("#resHeight", init.height || 1080);
  setVal("#fpsSpin", init.fps || 60);
  if ($("#gpuCheck")) $("#gpuCheck").checked = init.use_gpu !== false;
  setSelect("#presetCombo", init.encoder_preset || "medium");
  setVal("#crfSpin", init.crf || 20);
  if (init.width && init.height) state.aspectRatio = init.width / Math.max(init.height, 1);
  setVal("#ffmpegPath", init.ffmpeg_path || "");
  if ($("#ffmpegDisplay")) {
    $("#ffmpegDisplay").textContent = init.ffmpeg_display || "";
  }
  // Sync audio checkbox from config
  const audioEnabled = (state.config && state.config.renderer && state.config.renderer.enable_audio !== false);
  if ($("#audioCheckHome")) $("#audioCheckHome").checked = audioEnabled;
  if ($("#audioEnable")) $("#audioEnable").checked = audioEnabled;
  setStatus("Ready");
}

// ------------------------------------------------------------------
// Navigation
// ------------------------------------------------------------------
function bindNavButtons() {
  document.querySelectorAll("#sidebar .nav-btn[data-page]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#sidebar .nav-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const pageId = "page-" + btn.dataset.page;
      document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
      const page = document.getElementById(pageId);
      if (page) page.classList.add("active");
      if (btn.dataset.page === "settings") loadSettingsFromConfig();
    });
  });
}

// ------------------------------------------------------------------
// Sidebar
// ------------------------------------------------------------------
function bindSidebarToggle() {
  $("#hamburgerBtn")?.addEventListener("click", () => {
    $("#sidebar")?.classList.toggle("collapsed");
  });
}

// ------------------------------------------------------------------
// Theme
// ------------------------------------------------------------------
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const d = $("#themeIconDark"), l = $("#themeIconLight");
  if (d && l) { d.style.display = theme === "dark" ? "" : "none"; l.style.display = theme === "light" ? "" : "none"; }
}

function bindThemeToggle() {
  $("#themeBtn")?.addEventListener("click", async () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(next);
    try {
      if (!state.config) state.config = {};
      if (!state.config.app) state.config.app = {};
      state.config.app.theme = next;
      await pywebview.api.save_config(state.config);
    } catch (e) {}
  });
}

// ------------------------------------------------------------------
// Home Page
// ------------------------------------------------------------------
function bindHomePage() {
  $("#browseOsuBtn")?.addEventListener("click", async () => {
    const path = await pywebview.api.select_file("Select .osu file", "OSU Files (*.osu)");
    if (path) { setVal("#osuPath", path); setVal("#outputPath", path.replace(/\.[^.]+$/, "") + ".mp4"); }
  });
  $("#browseOutBtn")?.addEventListener("click", async () => {
    const path = await pywebview.api.save_file("Save Output Video", "MP4 Files (*.mp4)");
    if (path) setVal("#outputPath", path);
  });

  // Aspect ratio lock
  $("#linkBtn")?.addEventListener("click", () => {
    state.linkLocked = !state.linkLocked;
    const btn = $("#linkBtn");
    if (state.linkLocked) btn.classList.add("locked"); else btn.classList.remove("locked");
  });
  $("#resWidth")?.addEventListener("input", () => {
    if (!state.linkLocked) return;
    setVal("#resHeight", Math.round((parseInt($("#resWidth").value) || 1920) / state.aspectRatio));
  });
  $("#resHeight")?.addEventListener("input", () => {
    if (!state.linkLocked) return;
    setVal("#resWidth", Math.round((parseInt($("#resHeight").value) || 1080) * state.aspectRatio));
  });

  // Audio: sync home checkbox ↔ settings checkbox, save immediately
  $("#audioCheckHome")?.addEventListener("change", () => {
    const checked = $("#audioCheckHome").checked;
    if ($("#audioEnable")) $("#audioEnable").checked = checked;
    // Persist immediately so settings page picks it up
    if (!state.config) state.config = { renderer: {} };
    if (!state.config.renderer) state.config.renderer = {};
    state.config.renderer.enable_audio = checked;
    pywebview.api.save_config(state.config).catch(() => {});
  });

  // Start / Stop
  $("#startBtn")?.addEventListener("click", startRendering);
  $("#stopBtn")?.addEventListener("click", stopRendering);
}

async function startRendering() {
  if (state.rendering) return;
  const osuPath = $("#osuPath")?.value || "";
  if (!osuPath) { setStatus("Please select a .osu file", true); return; }

  setRenderingState(true);
  state.logBuffer = [];
  updateProgress(0, 1);
  setStatus("Initializing...");

  const params = {
    osu_path: osuPath,
    output_path: $("#outputPath")?.value || "",
    width: parseInt($("#resWidth")?.value) || 1920,
    height: parseInt($("#resHeight")?.value) || 1080,
    fps: parseInt($("#fpsSpin")?.value) || 60,
    use_gpu: $("#gpuCheck")?.checked !== false,
    encoder_preset: $("#presetCombo")?.value || "fast",
    crf: parseInt($("#crfSpin")?.value) || 20,
    ffmpeg_path: $("#ffmpegPath")?.value || "",
    enable_audio: $("#audioCheckHome")?.checked !== false,
  };

  addLog("Starting rendering...", "INFO");
  try {
    await pywebview.api.start_rendering(params);
    state.pollTimer = setInterval(pollEvents, 100);
  } catch (e) {
    addLog("Error: " + e, "ERROR");
    setRenderingState(false);
    setStatus("Failed to start", true);
  }
}

async function stopRendering() {
  try {
    await pywebview.api.stop_rendering();
    addLog("Stop requested...", "WARNING");
    setStatus("Stopping...");
    if ($("#stopBtn")) $("#stopBtn").disabled = true;
  } catch (e) { addLog("Error: " + e, "ERROR"); }
}

function setRenderingState(running) {
  state.rendering = running;
  const inputs = [
    "#osuPath", "#outputPath", "#browseOsuBtn", "#browseOutBtn",
    "#resWidth", "#resHeight", "#linkBtn", "#fpsSpin",
    "#gpuCheck", "#audioCheckHome", "#presetCombo", "#crfSpin",
  ];
  inputs.forEach((sel) => { const el = $(sel); if (el) el.disabled = running; });
  if ($("#startBtn")) $("#startBtn").disabled = running;
  if ($("#stopBtn")) $("#stopBtn").disabled = !running;
  // Swap button widths: when rendering, stop gets equal width
  const row = $("#actionRow");
  if (row) {
    if (running) row.classList.add("rendering");
    else row.classList.remove("rendering");
  }
}

// ------------------------------------------------------------------
// Polling
// ------------------------------------------------------------------
async function pollEvents() {
  let events;
  try { events = await pywebview.api.poll_events(); } catch (e) { return; }
  if (!events || events.length === 0) return;

  for (const evt of events) {
    switch (evt.type) {
      case "progress": updateProgress(evt.current, evt.total); break;
      case "log": addLog(evt.message, evt.level); break;
      case "finished":
        if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
        addLog(evt.success ? "Render completed." : "Render failed.", evt.success ? "INFO" : "ERROR");
        setStatus(evt.success ? "Completed" : "Failed", !evt.success);
        setRenderingState(false);
        break;
    }
  }
}

// ------------------------------------------------------------------
// Progress & Status
// ------------------------------------------------------------------
function updateProgress(current, total) {
  const bar = $("#progressBar"); if (bar) { bar.max = total; bar.value = current; }
  const pct = $("#progressPct");
  if (pct) pct.textContent = total > 0 ? Math.round((current / total) * 100) + "%" : "0%";
  if (total > 0 && current < total) setStatus(`Rendering frames (${current}/${total})`);
}

function setStatus(msg, isError) {
  const el = $("#statusText");
  if (el) { el.textContent = msg; el.style.color = isError ? "var(--danger)" : "var(--text-muted)"; }
}

function addLog(message, level) {
  state.logBuffer.push({ time: Date.now(), level: level || "INFO", message });
  const st = $("#logStatus");
  if (st) st.textContent = state.logBuffer.length + " entries";
}

// ------------------------------------------------------------------
// Settings
// ------------------------------------------------------------------
function bindSettingsPage() {
  $("#browseFfmpegBtn")?.addEventListener("click", async () => {
    const path = await pywebview.api.select_ffmpeg_exe();
    if (path) { setVal("#ffmpegPath", path); if ($("#ffmpegDisplay")) $("#ffmpegDisplay").textContent = path; autoSaveSettings(); }
  });
  $("#ffmpegPath")?.addEventListener("input", () => {
    const p = $("#ffmpegPath").value;
    if ($("#ffmpegDisplay")) $("#ffmpegDisplay").textContent = p || "(auto-detect)";
    autoSaveSettings();
  });

  const inputs = ["#setPreset","#setCrf","#setSample","#setPixFmt","#setTuning","#setGop","#setBframes","#audioEnable","#audioCodec","#audioBitrate"];
  inputs.forEach((sel) => {
    const el = $(sel); if (!el) return;
    el.addEventListener("change", autoSaveSettings);
    el.addEventListener("input", autoSaveSettings);
  });

  // Audio: sync settings checkbox → home checkbox, save immediately
  $("#audioEnable")?.addEventListener("change", () => {
    const checked = $("#audioEnable").checked;
    if ($("#audioCheckHome")) $("#audioCheckHome").checked = checked;
    if (!state.config) state.config = { renderer: {} };
    if (!state.config.renderer) state.config.renderer = {};
    state.config.renderer.enable_audio = checked;
    pywebview.api.save_config(state.config).catch(() => {});
  });

  $("#changeConfigDirBtn")?.addEventListener("click", async () => {
    const dir = await pywebview.api.select_directory("Select Config Directory");
    if (dir) {
      if (!state.config) state.config = {};
      if (!state.config.app) state.config.app = {};
      state.config.app.config_dir = dir;
      $("#configPathDisplay").textContent = dir + "/config.yaml";
      try { await pywebview.api.save_config(state.config); } catch (e) {}
    }
  });

  $("#resetDefaultsBtn")?.addEventListener("click", async () => {
    if (!confirm("Reset all settings to defaults?")) return;
    const defaults = {
      renderer: { encoder_preset:"fast",crf:20,sample_method:"linear",pixel_format:"yuv420p",preset_tuning:"default",gop_size:12,b_frames:2,enable_audio:true,audio_codec:"aac",audio_bitrate:"192k",ffmpeg_path:"",width:1280,height:720,fps:60,use_gpu:true },
      app: { theme: document.documentElement.dataset.theme || "dark", config_dir: "" },
    };
    try { await pywebview.api.save_config(defaults); state.config = defaults; } catch (e) {}
    loadSettingsFromConfig();
  });

  $("#exportLogBtn")?.addEventListener("click", async () => {
    if (state.logBuffer.length === 0) { if ($("#logStatus")) $("#logStatus").textContent = "No log data"; return; }
    const lines = state.logBuffer.map((e) => `[${new Date(e.time).toISOString()}] [${e.level}] ${e.message}`);
    const path = await pywebview.api.save_file("Export Log", "Log Files (*.log)");
    if (path) {
      try { await pywebview.api.save_log_file(path, lines.join("\n")); if ($("#logStatus")) $("#logStatus").textContent = "Exported"; }
      catch (e) { if ($("#logStatus")) $("#logStatus").textContent = "Export failed"; }
    }
  });
}

function loadSettingsFromConfig() {
  const r = (state.config && state.config.renderer) || {};
  setSelect("#setPreset", r.encoder_preset || "fast");
  setVal("#setCrf", r.crf ?? 20);
  setSelect("#setSample", r.sample_method || "linear");
  setSelect("#setPixFmt", r.pixel_format || "yuv420p");
  setSelect("#setTuning", r.preset_tuning || "default");
  setVal("#setGop", r.gop_size ?? 12);
  setVal("#setBframes", r.b_frames ?? 2);
  const ae = r.enable_audio !== false;
  if ($("#audioEnable")) $("#audioEnable").checked = ae;
  if ($("#audioCheckHome")) $("#audioCheckHome").checked = ae;
  setSelect("#audioCodec", r.audio_codec || "aac");
  setSelect("#audioBitrate", r.audio_bitrate || "192k");
  setVal("#ffmpegPath", r.ffmpeg_path || "");
  if ($("#logStatus")) $("#logStatus").textContent = state.logBuffer.length > 0 ? state.logBuffer.length + " entries" : "No log data yet";
  try {
    pywebview.api.get_default_ffmpeg().then((d) => { if ($("#ffmpegDisplay") && !r.ffmpeg_path) $("#ffmpegDisplay").textContent = d || "(auto-detect)"; });
    pywebview.api.load_config().then((cfg) => { if ($("#configPathDisplay") && cfg.app) { const dir = cfg.app.config_dir || ""; $("#configPathDisplay").textContent = dir ? dir + "/config.yaml" : "(default)"; } });
  } catch (e) {}
}

function autoSaveSettings() {
  if (state.saveTimeout) clearTimeout(state.saveTimeout);
  state.saveTimeout = setTimeout(saveSettingsNow, 500);
}

async function saveSettingsNow() {
  if (!state.config) state.config = await pywebview.api.load_config().catch(() => ({}));
  if (!state.config.renderer) state.config.renderer = {};
  const r = state.config.renderer;
  r.encoder_preset = $("#setPreset")?.value || "fast";
  r.crf = parseInt($("#setCrf")?.value) || 20;
  r.sample_method = $("#setSample")?.value || "linear";
  r.pixel_format = $("#setPixFmt")?.value || "yuv420p";
  r.preset_tuning = $("#setTuning")?.value || "default";
  r.gop_size = parseInt($("#setGop")?.value) || 12;
  r.b_frames = parseInt($("#setBframes")?.value) || 2;
  r.enable_audio = $("#audioEnable")?.checked !== false;
  r.audio_codec = $("#audioCodec")?.value || "aac";
  r.audio_bitrate = $("#audioBitrate")?.value || "192k";
  // Sync home checkbox
  if ($("#audioCheckHome")) $("#audioCheckHome").checked = r.enable_audio;
  try { await pywebview.api.save_config(state.config); } catch (e) {}
}

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------
function setVal(sel, v) { const el = $(sel); if (el) el.value = v; }
function setSelect(sel, v) {
  const el = $(sel); if (!el) return;
  for (const o of el.options) { if (o.value === v) { el.value = v; return; } }
}
