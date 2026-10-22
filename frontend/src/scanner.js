/* Door-staff QR scanner for /staff/checkin/ (docs/routes.md; cut-list item 1).

   It only fills step 1 of the check-in flow: a scanned code is submitted as a LOOKUP
   (nothing is written), the server shows the guest card, staff check the ID and confirm.

   Decoding: the browser's native BarcodeDetector when it supports QR (Chrome/Android —
   fast, no download); otherwise jsQR in a Web Worker (iOS Safari), fetched only then.
   The camera is released when the tab is hidden or the page changes. After a check-in the
   next page restarts the camera by itself (permission is remembered), so the door keeps
   moving; it never auto-starts on a page that is waiting for a confirmation.
   Arabic text comes from the template (data-* / markup), never from this file. */

const root = document.querySelector("[data-scanner]");
const form = document.getElementById("lookup-form");
const SESSION_KEY = "es2.scanner";
const RECENT_KEY = "es2.scanner.last"; // ignore the code just handled for a few seconds
const RECENT_MS = 6000;
const INTERVAL_MS = 120; // ~8 decodes per second is plenty for a QR held to the camera
const WORK_WIDTH = 480; // fallback decoder works on a downscaled frame

const store = {
  get(k) {
    try {
      return sessionStorage.getItem(k);
    } catch {
      return null;
    }
  },
  set(k, v) {
    try {
      if (v === null) sessionStorage.removeItem(k);
      else sessionStorage.setItem(k, v);
    } catch {
      /* private mode: auto-restart just won't happen */
    }
  },
};

if (root && form && window.isSecureContext && navigator.mediaDevices?.getUserMedia) {
  root.hidden = false;
  const video = root.querySelector("video");
  const startBtn = root.querySelector("[data-start]");
  const stopBtn = root.querySelector("[data-stop]");
  const errorBox = root.querySelector("[data-error]");
  const tokenInput = form.querySelector("[name=token]");

  let stream = null;
  let timer = 0;
  let busy = false;
  let handled = false;
  let detector = null;
  let worker = null;
  let canvas = null;

  async function makeDecoder() {
    if ("BarcodeDetector" in window) {
      try {
        const formats = await window.BarcodeDetector.getSupportedFormats();
        if (formats.includes("qr_code")) {
          detector = new window.BarcodeDetector({ formats: ["qr_code"] });
          return;
        }
      } catch {
        /* fall through to the worker */
      }
    }
    worker = new Worker(new URL("./qr-worker.js", import.meta.url), { type: "module" });
    canvas = document.createElement("canvas");
  }

  function decodeWithWorker() {
    const w = WORK_WIDTH;
    const h = Math.round((video.videoHeight / video.videoWidth) * w) || w;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(video, 0, 0, w, h);
    const { data } = ctx.getImageData(0, 0, w, h);
    return new Promise((resolve) => {
      worker.onmessage = (e) => resolve(e.data);
      worker.postMessage({ data, width: w, height: h }, [data.buffer]);
    });
  }

  async function tick() {
    if (!stream || busy || handled || video.readyState < 2) return;
    busy = true;
    try {
      let text = null;
      if (detector) {
        const codes = await detector.detect(video);
        text = codes.length ? codes[0].rawValue : null;
      } else {
        text = await decodeWithWorker();
      }
      if (text) onCode(text.trim());
    } catch {
      /* a bad frame — try the next one */
    } finally {
      busy = false;
    }
  }

  function onCode(text) {
    const recent = (store.get(RECENT_KEY) || "").split("|");
    if (recent[0] === text && Date.now() - Number(recent[1] || 0) < RECENT_MS) return;
    handled = true;
    store.set(RECENT_KEY, `${text}|${Date.now()}`);
    if (navigator.vibrate) navigator.vibrate(60);
    root.classList.add("found");
    tokenInput.value = text;
    stop(false); // release the camera; the next page restarts it after the confirmation
    form.requestSubmit ? form.requestSubmit() : form.submit();
  }

  async function start() {
    errorBox.hidden = true;
    try {
      if (!detector && !worker) await makeDecoder();
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 } },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
      root.classList.add("live");
      startBtn.hidden = true;
      stopBtn.hidden = false;
      store.set(SESSION_KEY, "on");
      timer = setInterval(tick, INTERVAL_MS);
    } catch {
      stop(true);
      errorBox.hidden = false; // denied / no camera: manual entry and search still work
    }
  }

  function stop(forget) {
    clearInterval(timer);
    if (stream) stream.getTracks().forEach((t) => t.stop());
    stream = null;
    video.srcObject = null;
    root.classList.remove("live");
    startBtn.hidden = false;
    stopBtn.hidden = true;
    if (forget) store.set(SESSION_KEY, null);
  }

  startBtn.addEventListener("click", start);
  stopBtn.addEventListener("click", () => stop(true));
  const mayAutostart = () =>
    root.dataset.autostart === "1" && !handled && store.get(SESSION_KEY) === "on";
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && stream) stop(false); // free the camera, keep the "on" preference
    else if (!document.hidden && !stream && mayAutostart()) start();
  });
  window.addEventListener("pagehide", () => stop(false));

  // Back on the page after a check-in: carry on scanning (never while a guest card
  // is waiting for confirmation — that would rescan the same code).
  if (mayAutostart()) start();
}
