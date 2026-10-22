/* QR decoding off the main thread (fallback for browsers without BarcodeDetector).
   Receives { data, width, height } (RGBA pixels), replies with the decoded text or null. */
import jsQR from "jsqr";

self.onmessage = (e) => {
  const { data, width, height } = e.data;
  const code = jsQR(data, width, height, { inversionAttempts: "dontInvert" });
  self.postMessage(code ? code.data : null);
};
