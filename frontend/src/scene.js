/* Hero 3D scene: game controller over a lit pedestal (docs/frontend.md).

   Performance rules implemented here (all FIXED in docs/frontend.md):
   - imports only the three.js parts used (tree-shaken)
   - model is glTF with meshopt geometry + WebP textures (scripts/optimize-model.mjs)
   - DPR capped per tier (HIGH 2.0, MID 1.5), MSAA on both; no post-processing (owner asked for
     no neon beams, so bloom is not used even on HIGH)
   - render loop pauses when off-screen and when the tab is hidden
   - 3 s FPS probe: < 30 → one tier down (MID → LOW removes the canvas, poster stays),
     > 50 on MID → HIGH; the result is saved so revisits skip the probe
   - the canvas fades in over the poster only after the first real frame
   - start-up work is split into small steps with a yield between each (environment,
     shader compile via compileAsync, one texture upload per step) so no single task
     blocks scrolling or taps — measured: no long task > 200 ms on a 4×-slowed phone */

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
const MODEL_WIDTH = 2.5; // world units the controller is scaled to fit
// Rest pose (radians), tuned to the model file: face toward the camera, top tipped back.
const MODEL_REST = { x: -0.35, y: 0, z: 0 };
// Idle motion: a slow sway that keeps the face visible (a full spin mostly shows the side).
const SWAY = { amp: 0.42, period: 7000 };
const IDLE_AFTER_DRAG = 2500; // ms before the sway takes over again

// Give the browser a breather between heavy start-up steps (input, scrolling, paint).
const yieldToMain = () =>
  new Promise((resolve) =>
    "requestIdleCallback" in window ? requestIdleCallback(() => resolve(), { timeout: 200 }) : setTimeout(resolve, 16),
  );

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
  // MSAA on every 3D tier: at DPR ≤ 1.5 it is cheap on current phone GPUs and removes jaggies
  const renderer = new WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
  if (!renderer.capabilities.isWebGL2) {
    renderer.dispose();
    throw new Error("no WebGL2");
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, DPR_CAP[tier]));
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.92;
  const canvas = renderer.domElement;
  canvas.className = "scene-canvas";
  canvas.setAttribute("aria-hidden", "true");

  // --- scene ----------------------------------------------------------------------
  const scene = new Scene();

  const camera = new PerspectiveCamera(32, 1, 0.1, 50);
  camera.position.set(0, 1.4, 7.4);
  camera.lookAt(0, -0.4, 0);

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
  pedestal.position.y = -1.2;
  const disc = new Mesh(
    new CylinderGeometry(1.45, 1.6, 0.22, 64),
    new MeshStandardMaterial({ color: 0x0a1220, metalness: 0.35, roughness: 0.75 }),
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
  MeshoptDecoder.useWorkers(1); // geometry decompression off the main thread
  loader.setMeshoptDecoder(MeshoptDecoder);
  await yieldToMain(); // WebGL context creation and model parsing in separate tasks
  performance.mark("es2:load-start");
  const gltf = await loader.loadAsync(modelUrl);
  performance.mark("es2:model");
  await yieldToMain();

  // reflections: a small (64 px) room environment is plenty for a hero object
  const pmrem = new PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04, 0.1, 100, { size: 64 }).texture;
  pmrem.dispose();
  performance.mark("es2:env");
  await yieldToMain();
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
  const state = { rotY: 0, rotX: 0, velY: 0, dragging: false, lastDrag: -1e9, lastX: 0, lastY: 0, tiltX: 0, tiltY: 0 };
  const still = location.hash === "#hero-still"; // debug: freeze at the rest pose (screenshots)
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
    state.lastDrag = performance.now();
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
    if (!state.dragging && !still) {
      state.velY *= 0.94; // drag inertia dies out…
      state.rotY += state.velY;
      state.rotX *= 0.95;
      if (now - state.lastDrag > IDLE_AFTER_DRAG) {
        // …then ease back into the sway (shortest way round after a full spin)
        const sway = Math.sin((now / SWAY.period) * Math.PI * 2) * SWAY.amp;
        const turns = Math.round((state.rotY - sway) / (Math.PI * 2));
        state.rotY += (sway + turns * Math.PI * 2 - state.rotY) * 0.03;
      }
    }
    spin.rotation.y = state.rotY + state.tiltY;
    spin.rotation.x = state.rotX + state.tiltX;
    spin.position.y = 0.12 + (still ? 0 : Math.sin(now / 1400) * 0.05); // hover above the pedestal + gentle float
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

  // warm-up off the critical path: compile shaders without blocking (KHR_parallel_shader_compile),
  // then upload textures to the GPU one per step instead of all inside the first frame
  await renderer.compileAsync(scene, camera);
  performance.mark("es2:compiled");
  await yieldToMain();
  const textures = new Set();
  scene.traverse((o) => {
    if (!o.material) return;
    for (const v of Object.values(o.material)) if (v && v.isTexture) textures.add(v);
  });
  for (const t of textures) {
    renderer.initTexture(t);
    await yieldToMain();
  }

  // first frame, then reveal (CSS fades the canvas in and the poster out)
  performance.mark("es2:textures");
  frame.appendChild(canvas);
  spin.position.y = 0.12;
  renderer.render(scene, camera);
  performance.mark("es2:first-frame");
  requestAnimationFrame(() => frame.classList.add("has-3d"));
  play();
}
