/* Hero 3D scene: game controller over a lit pedestal (docs/frontend.md).

   Performance rules implemented here (all FIXED in docs/frontend.md):
   - imports only the three.js parts used (tree-shaken)
   - model is glTF with meshopt geometry + WebP textures (scripts/optimize-model.mjs)
   - DPR capped per tier (HIGH 2.0, MID 1.5); no post-processing (owner asked for
     no neon beams, so bloom is not used even on HIGH)
   - render loop pauses when off-screen and when the tab is hidden
   - 3 s FPS probe: < 30 → one tier down (MID → LOW removes the canvas, poster stays),
     > 50 on MID → HIGH; the result is saved so revisits skip the probe
   - the canvas fades in over the poster only after the first real frame */

import {
  ACESFilmicToneMapping,
  Box3,
  CylinderGeometry,
  DirectionalLight,
  Group,
  HemisphereLight,
  MathUtils,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  PerspectiveCamera,
  PMREMGenerator,
  PointLight,
  Scene,
  SRGBColorSpace,
  TorusGeometry,
  Vector3,
  WebGLRenderer,
} from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";

// Brand colours (docs/frontend.md rev 4) — keep in sync with static/css/base.css :root.
const CYAN = 0x3cd6e0;
const MAGENTA = 0xd15eb9;
const NAVY = 0x050a14;

const DPR_CAP = { high: 2, mid: 1.5 };
const MODEL_WIDTH = 2.4; // world units the controller is scaled to fit
// Orientation of the controller in its rest pose (radians). Tuned to the model file.
const MODEL_REST = { x: 0.55, y: 0, z: 0 };

function saveTier(key, tier) {
  try {
    localStorage.setItem(key, tier);
  } catch {
    /* storage blocked: the probe simply runs again next visit */
  }
}

export async function start(mount, { tier, modelUrl, tierKey }) {
  const frame = mount.querySelector(".scene-frame") || mount;

  // --- renderer (failure here = FALLBACK tier: poster stays) ---------------------
  const renderer = new WebGLRenderer({ antialias: tier === "high", alpha: true, powerPreference: "high-performance" });
  if (!renderer.capabilities.isWebGL2) {
    renderer.dispose();
    throw new Error("no WebGL2");
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, DPR_CAP[tier]));
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  const canvas = renderer.domElement;
  canvas.className = "scene-canvas";
  canvas.setAttribute("aria-hidden", "true");

  // --- scene ----------------------------------------------------------------------
  const scene = new Scene();
  const pmrem = new PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  pmrem.dispose();

  const camera = new PerspectiveCamera(32, 1, 0.1, 50);
  camera.position.set(0, 1.5, 7);
  camera.lookAt(0, -0.15, 0);

  scene.add(new HemisphereLight(0xdfe9f5, NAVY, 0.6));
  const key = new DirectionalLight(0xffffff, 1.6);
  key.position.set(2.5, 4, 3);
  scene.add(key);
  const rimCyan = new PointLight(CYAN, 18, 9, 2);
  rimCyan.position.set(-2.8, 1.2, -1.5);
  scene.add(rimCyan);
  const rimMagenta = new PointLight(MAGENTA, 14, 9, 2);
  rimMagenta.position.set(2.8, 0.6, -1.2);
  scene.add(rimMagenta);

  // pedestal: dark metal disc + two thin brand rings (soft, not neon)
  const pedestal = new Group();
  pedestal.position.y = -0.95;
  const disc = new Mesh(
    new CylinderGeometry(1.45, 1.6, 0.22, 64),
    new MeshStandardMaterial({ color: 0x0d1626, metalness: 0.6, roughness: 0.5 }),
  );
  pedestal.add(disc);
  const ringA = new Mesh(new TorusGeometry(1.5, 0.018, 8, 96), new MeshBasicMaterial({ color: CYAN }));
  ringA.rotation.x = Math.PI / 2;
  ringA.position.y = 0.115;
  pedestal.add(ringA);
  const ringB = new Mesh(
    new TorusGeometry(1.78, 0.012, 8, 96),
    new MeshBasicMaterial({ color: MAGENTA, transparent: true, opacity: 0.7 }),
  );
  ringB.rotation.x = Math.PI / 2;
  ringB.position.y = -0.09;
  pedestal.add(ringB);
  scene.add(pedestal);

  // --- model ----------------------------------------------------------------------
  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  const gltf = await loader.loadAsync(modelUrl);
  const model = gltf.scene;
  // normalise: centre at origin, scale to MODEL_WIDTH
  const box = new Box3().setFromObject(model);
  const size = box.getSize(new Vector3());
  const centre = box.getCenter(new Vector3());
  model.position.sub(centre);
  const holder = new Group(); // rotation happens on holder, model stays centred
  holder.add(model);
  holder.scale.setScalar(MODEL_WIDTH / Math.max(size.x, size.z, 1e-6));
  const spin = new Group(); // user rotation (drag) + idle spin
  spin.add(holder);
  holder.rotation.set(MODEL_REST.x, MODEL_REST.y, MODEL_REST.z);
  scene.add(spin);

  // --- interaction: drag to rotate, pointer parallax -----------------------------
  const state = { rotY: 0, rotX: 0, velY: 0.004, dragging: false, lastX: 0, lastY: 0, tiltX: 0, tiltY: 0 };
  canvas.addEventListener("pointerdown", (e) => {
    state.dragging = true;
    state.lastX = e.clientX;
    state.lastY = e.clientY;
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener("pointermove", (e) => {
    if (!state.dragging) return;
    const dx = e.clientX - state.lastX;
    const dy = e.clientY - state.lastY;
    state.lastX = e.clientX;
    state.lastY = e.clientY;
    state.velY = dx * 0.008;
    state.rotY += state.velY;
    state.rotX = MathUtils.clamp(state.rotX + dy * 0.006, -0.5, 0.5);
  });
  const release = () => {
    state.dragging = false;
  };
  canvas.addEventListener("pointerup", release);
  canvas.addEventListener("pointercancel", release);
  const hero = mount.closest(".hero") || mount;
  hero.addEventListener("pointermove", (e) => {
    if (e.pointerType !== "mouse") return;
    const r = hero.getBoundingClientRect();
    state.tiltY = ((e.clientX - r.left) / r.width - 0.5) * 0.25;
    state.tiltX = ((e.clientY - r.top) / r.height - 0.5) * 0.12;
  });

  // --- sizing ----------------------------------------------------------------------
  function resize() {
    const w = frame.clientWidth;
    const h = frame.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(frame);
  resize();

  // --- loop: runs only while visible ---------------------------------------------
  let onScreen = true;
  let running = false;
  let rafId = 0;
  let probe = { start: 0, frames: 0, done: false };

  function frameTick(now) {
    rafId = requestAnimationFrame(frameTick);
    if (!state.dragging) {
      state.velY += (0.004 - state.velY) * 0.03; // inertia settles into a slow idle spin
      state.rotY += state.velY;
      state.rotX *= 0.95;
    }
    spin.rotation.y = state.rotY + state.tiltY;
    spin.rotation.x = state.rotX + state.tiltX;
    spin.position.y = Math.sin(now / 1400) * 0.05; // gentle float
    renderer.render(scene, camera);

    if (!probe.done) {
      if (!probe.start) probe.start = now;
      probe.frames++;
      if (now - probe.start >= 3000) {
        probe.done = true;
        settleTier((probe.frames * 1000) / (now - probe.start));
      }
    }
  }

  function play() {
    if (running || !onScreen || document.hidden) return;
    running = true;
    probe = { start: 0, frames: 0, done: probe.done }; // never probe across a pause
    rafId = requestAnimationFrame(frameTick);
  }
  function pause() {
    running = false;
    cancelAnimationFrame(rafId);
  }

  function teardown() {
    pause();
    canvas.remove();
    frame.classList.remove("has-3d");
    renderer.dispose();
  }

  function settleTier(fps) {
    if (fps < 30) {
      if (tier === "high") {
        tier = "mid";
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, DPR_CAP.mid));
        resize();
      } else {
        saveTier(tierKey, "low");
        teardown(); // LOW: poster only
        return;
      }
    } else if (fps > 50 && tier === "mid") {
      tier = "high";
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, DPR_CAP.high));
      resize();
    }
    saveTier(tierKey, tier);
  }

  new IntersectionObserver((entries) => {
    onScreen = entries[0].isIntersecting;
    onScreen ? play() : pause();
  }).observe(frame);
  document.addEventListener("visibilitychange", () => (document.hidden ? pause() : play()));

  // first frame, then reveal (CSS fades the canvas in and the poster out)
  frame.appendChild(canvas);
  renderer.render(scene, camera);
  requestAnimationFrame(() => frame.classList.add("has-3d"));
  play();
}
