import init, { HwpDocument } from "./rhwp-core/rhwp.js";

const params = new URLSearchParams(window.location.search);
const sessionId = params.get("session") || "";
const token = params.get("token") || "";
const apiBase = params.get("apiBase") || window.location.origin;

let canvasContext = null;
let lastFont = "";
globalThis.measureTextWidth = (font, text) => {
  if (!canvasContext) {
    canvasContext = document.createElement("canvas").getContext("2d");
  }
  if (font !== lastFont) {
    canvasContext.font = font;
    lastFont = font;
  }
  return canvasContext.measureText(text).width;
};

const state = {
  doc: null,
  fileName: "",
  sourceFormat: "",
  pageCount: 0,
  currentPage: 0,
  dirty: false,
  qtBridge: null,
};

const els = {
  documentName: document.getElementById("document-name"),
  documentState: document.getElementById("document-state"),
  viewer: document.getElementById("viewer"),
  loading: document.getElementById("loading"),
  pageIndicator: document.getElementById("page-indicator"),
  formatValue: document.getElementById("format-value"),
  pageCountValue: document.getElementById("page-count-value"),
  saveValue: document.getElementById("save-value"),
  insertText: document.getElementById("insert-text"),
};

function setStatus(message, isError = false) {
  els.documentState.textContent = message;
  els.documentState.style.color = isError ? "#f85149" : "#8b949e";
}

function setLoading(message, visible = true) {
  els.loading.textContent = message;
  els.loading.hidden = !visible;
}

function documentUrl() {
  return `${apiBase}/api/sessions/${encodeURIComponent(sessionId)}/document?token=${encodeURIComponent(token)}`;
}

function stateUrl() {
  return `${apiBase}/api/sessions/${encodeURIComponent(sessionId)}/state?token=${encodeURIComponent(token)}`;
}

function saveUrl(mode, format, targetPath = "") {
  const url = new URL(`${apiBase}/api/sessions/${encodeURIComponent(sessionId)}/save`);
  url.searchParams.set("token", token);
  url.searchParams.set("mode", mode);
  url.searchParams.set("format", format);
  if (targetPath) {
    url.searchParams.set("target", targetPath);
  }
  return url.toString();
}

async function postState(extra = {}) {
  await fetch(stateUrl(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      dirty: state.dirty,
      page_count: state.pageCount,
      source_format: state.sourceFormat,
      status_message: els.documentState.textContent || "",
      ...extra,
    }),
  });
}

function refreshChrome() {
  els.documentName.textContent = state.fileName || "문서 편집기";
  els.pageIndicator.textContent = state.pageCount
    ? `${state.currentPage + 1} / ${state.pageCount}`
    : "0 / 0";
  els.formatValue.textContent = state.sourceFormat ? state.sourceFormat.toUpperCase() : "-";
  els.pageCountValue.textContent = state.pageCount ? `${state.pageCount}` : "-";
  els.saveValue.textContent = state.dirty ? "수정됨" : "저장됨";
  document.title = `${state.dirty ? "*" : ""}${state.fileName || "HWP Master Editor"}`;
}

function markDirty(dirty = true) {
  state.dirty = dirty;
  refreshChrome();
  postState().catch(() => {});
}

function currentExportFormat(targetPath = "") {
  const suffix = (targetPath.split(".").pop() || "").toLowerCase();
  if (suffix === "hwpx" || suffix === "hwp") {
    return suffix;
  }
  return state.sourceFormat === "hwpx" ? "hwpx" : "hwp";
}

function exportBytes(format) {
  if (!state.doc) {
    throw new Error("열린 문서가 없습니다.");
  }
  if (format === "hwpx") {
    return state.doc.exportHwpx();
  }
  return state.doc.exportHwp();
}

async function renderCurrentPage() {
  if (!state.doc) return;
  const page = Math.max(0, Math.min(state.currentPage, state.pageCount - 1));
  state.currentPage = page;
  setLoading("페이지 렌더링 중...", true);
  await new Promise((resolve) => setTimeout(resolve, 0));
  els.viewer.innerHTML = state.doc.renderPageSvg(page);
  setLoading("", false);
  refreshChrome();
}

async function loadQtBridge() {
  if (!window.qt || !window.QWebChannel) {
    return;
  }
  await new Promise((resolve) => {
    new window.QWebChannel(window.qt.webChannelTransport, (channel) => {
      state.qtBridge = channel.objects.hwpMaster || null;
      resolve();
    });
  });
}

async function loadDocument() {
  if (!sessionId || !token) {
    throw new Error("편집 세션 정보가 없습니다.");
  }

  setLoading("WASM 초기화 중...", true);
  await init({ module_or_path: "./rhwp-core/rhwp_bg.wasm" });
  await loadQtBridge();

  setLoading("문서 다운로드 중...", true);
  const response = await fetch(documentUrl());
  if (!response.ok) {
    throw new Error(await response.text());
  }

  const dispositionName = response.headers.get("X-HwpMaster-File-Name");
  state.fileName = dispositionName ? decodeURIComponent(dispositionName) : "document.hwp";
  state.sourceFormat = (state.fileName.split(".").pop() || "hwp").toLowerCase();

  setLoading("문서 파싱 중...", true);
  const data = new Uint8Array(await response.arrayBuffer());
  state.doc = new HwpDocument(data);
  state.pageCount = state.doc.pageCount();
  state.currentPage = 0;
  state.dirty = false;

  setStatus("문서가 열렸습니다.");
  refreshChrome();
  await postState();
  await renderCurrentPage();
}

async function requestSave(mode, targetPath = "") {
  try {
    const format = currentExportFormat(targetPath);
    setStatus("저장 중...");
    const bytes = exportBytes(format);
    const response = await fetch(saveUrl(mode, format, targetPath), {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream" },
      body: bytes,
    });
    const payload = await response.json();
    if (!response.ok || !payload.success) {
      throw new Error(payload.error || "저장 실패");
    }
    if (payload.path) {
      state.fileName = payload.path.split(/[\\/]/).pop() || state.fileName;
      state.sourceFormat = currentExportFormat(payload.path);
    }
    if (mode !== "recovery") {
      markDirty(false);
    }
    setStatus(mode === "recovery" ? "복구본 저장 완료" : "저장 완료");
    return payload;
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error), true);
    throw error;
  }
}

async function requestSaveAs(path = "") {
  let targetPath = path;
  if (!targetPath && state.qtBridge && state.qtBridge.requestSaveAs) {
    targetPath = await new Promise((resolve) => {
      state.qtBridge.requestSaveAs(state.fileName || "document.hwp", resolve);
    });
  }
  if (!targetPath) {
    setStatus("다른 이름 저장이 취소되었습니다.");
    return;
  }
  await requestSave("save_as", targetPath);
}

async function insertTextAtStart() {
  const text = els.insertText.value;
  if (!text.trim()) {
    setStatus("삽입할 텍스트를 입력해주세요.", true);
    return;
  }
  if (!state.doc) return;
  state.doc.insertText(0, 0, 0, text);
  els.insertText.value = "";
  markDirty(true);
  setStatus("텍스트가 삽입되었습니다.");
  await renderCurrentPage();
}

function bindToolbar() {
  document.querySelectorAll("[data-command]").forEach((button) => {
    button.addEventListener("click", async () => {
      const command = button.getAttribute("data-command");
      try {
        if (command === "prev") {
          state.currentPage -= 1;
          await renderCurrentPage();
        } else if (command === "next") {
          state.currentPage += 1;
          await renderCurrentPage();
        } else if (command === "insert") {
          await insertTextAtStart();
        } else if (command === "save") {
          await requestSave("current");
        } else if (command === "save-as") {
          await requestSaveAs();
        } else if (command === "recovery") {
          await requestSave("recovery");
        }
      } catch {
        // Status is already displayed by the command handler.
      }
    });
  });

  document.addEventListener("keydown", async (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      try {
        await requestSave("current");
      } catch {
        // Status is already displayed by requestSave.
      }
    }
  });
}

window.HwpMasterEditor = {
  requestSave,
  requestSaveAs,
  markDirty,
};

bindToolbar();
loadDocument().catch((error) => {
  setLoading("", false);
  setStatus(error instanceof Error ? error.message : String(error), true);
});
