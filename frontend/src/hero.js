// Hero scene: game controller over a lit pedestal (docs/frontend.md → 3D scenes).
// Arena Night palette: volt + purple ring accents on near-black. The controller
// is built from primitives (low-poly, zero downloads — a .glb can replace it
// later without touching the mount contract). Drag to rotate + pointer parallax.
import {
  AmbientLight,
  BufferGeometry,
  CanvasTexture,
  CapsuleGeometry,
  Color,
  CylinderGeometry,
  DirectionalLight,
  Float32BufferAttribute,
  Group,
  Mesh,
  MeshStandardMaterial,
  PerspectiveCamera,
  PointLight,
  Points,
  PointsMaterial,
  Scene,
  SphereGeometry,
  TorusGeometry,
  WebGLRenderer,
} from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { persistTier } from "./tiers.js";

// Logo palette (design rev 4): cyan + magenta accents on navy.
const VOLT = 0x3ec7d6;
const PURPLE = 0xc9479b;
const BODY = 0x1a2c49;
const DPR_CAP = { HIGH: 2.0, MID: 1.5 };
const PARTICLES = { HIGH: 140, MID: 50 };

function buildController() {
  const g = new Group();
  const shell = new MeshStandardMaterial({ color: BODY, roughness: 0.45, metalness: 0.3 });
  const dark = new MeshStandardMaterial({ color: 0x0e1a2e, roughness: 0.6, metalness: 0.2 });
  const volt = new MeshStandardMaterial({ color: VOLT, emissive: VOLT, emissiveIntensity: 0.55 });
  const purple = new MeshStandardMaterial({
    color: PURPLE,
    emissive: PURPLE,
    emissiveIntensity: 0.55,
  });

  const body = new Mesh(new RoundedBoxGeometry(2.6, 1.0, 0.55, 4, 0.24), shell);
  g.add(body);

  for (const side of [-1, 1]) {
    const grip = new Mesh(new CapsuleGeometry(0.34, 0.8, 4, 12), shell);
    grip.position.set(side * 1.05, -0.55, 0.1);
    grip.rotation.z = side * 0.45;
    grip.rotation.x = -0.25;
    g.add(grip);
  }

  // Analog sticks: ring base + stem + cap.
  for (const [x, accent] of [
    [-0.62, purple],
    [0.3, volt],
  ]) {
    const base = new Mesh(new CylinderGeometry(0.21, 0.24, 0.1, 20), dark);
    base.position.set(x, 0.1, 0.32);
    base.rotation.x = Math.PI / 2;
    const stem = new Mesh(new CylinderGeometry(0.07, 0.07, 0.22, 10), dark);
    stem.position.set(x, 0.1, 0.42);
    stem.rotation.x = Math.PI / 2;
    const cap = new Mesh(new SphereGeometry(0.15, 16, 12), accent);
    cap.scale.z = 0.55;
    cap.position.set(x, 0.1, 0.52);
    g.add(base, stem, cap);
  }

  // D-pad: two crossed bars.
  for (const rot of [0, Math.PI / 2]) {
    const bar = new Mesh(new RoundedBoxGeometry(0.46, 0.15, 0.1, 2, 0.04), dark);
    bar.position.set(-1.0, 0.22, 0.3);
    bar.rotation.z = rot;
    g.add(bar);
  }

  // Face buttons: diamond of four.
  const buttonMats = [volt, purple, dark, dark];
  [
    [1.0, 0.44],
    [1.0, 0.0],
    [0.78, 0.22],
    [1.22, 0.22],
  ].forEach(([x, y], i) => {
    const b = new Mesh(new CylinderGeometry(0.09, 0.09, 0.08, 16), buttonMats[i]);
    b.position.set(x, y, 0.3);
    b.rotation.x = Math.PI / 2;
    g.add(b);
  });

  return g;
}

function buildPedestal() {
  const g = new Group();
  const top = new Mesh(
    new CylinderGeometry(1.55, 1.7, 0.22, 48),
    new MeshStandardMaterial({ color: 0x13223a, roughness: 0.35, metalness: 0.5 }),
  );
  const voltRing = new Mesh(
    new TorusGeometry(1.56, 0.035, 10, 64),
    new MeshStandardMaterial({ color: VOLT, emissive: VOLT, emissiveIntensity: 1.2 }),
  );
  voltRing.rotation.x = Math.PI / 2;
  voltRing.position.y = 0.12;
  const purpleRing = new Mesh(
    new TorusGeometry(1.95, 0.025, 10, 64),
    new MeshStandardMaterial({ color: PURPLE, emissive: PURPLE, emissiveIntensity: 1.1 }),
  );
  purpleRing.rotation.x = Math.PI / 2;
  purpleRing.position.y = -0.1;
  g.add(top, voltRing, purpleRing);
  return g;
}

function buildParticles(count) {
  const positions = [];
  for (let i = 0; i < count; i++) {
    const r = 1.4 + Math.random() * 1.6;
    const a = Math.random() * Math.PI * 2;
    positions.push(Math.cos(a) * r, Math.random() * 3.2 - 0.8, Math.sin(a) * r);
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new Float32BufferAttribute(positions, 3));
  // Tiny radial-gradient sprite so points render as soft glows, not squares.
  const sprite = document.createElement("canvas");
  sprite.width = sprite.height = 32;
  const ctx = sprite.getContext("2d");
  const grad = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
  grad.addColorStop(0, "rgba(62,199,214,0.9)");
  grad.addColorStop(1, "rgba(62,199,214,0)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 32, 32);
  return new Points(
    geometry,
    new PointsMaterial({
      size: 0.1,
      map: new CanvasTexture(sprite),
      transparent: true,
      depthWrite: false,
      color: 0xffffff,
    }),
  );
}

export function mountHero(frame, startTier) {
  let tier = startTier;
  const poster = frame.querySelector("svg");
  const canvas = document.createElement("canvas");
  let renderer;
  try {
    renderer = new WebGLRenderer({ canvas, antialias: true, alpha: true });
  } catch {
    return; // context creation failed after all: poster stays
  }

  const scene = new Scene();
  const camera = new PerspectiveCamera(38, 1, 0.1, 30);
  camera.position.set(0, 1.1, 6.2);
  camera.lookAt(0, 0.3, 0);

  scene.add(new AmbientLight(0x3a4c6e, 0.9));
  const key = new DirectionalLight(0xf2f4ff, 1.1);
  key.position.set(3, 5, 4);
  scene.add(key);
  const voltLight = new PointLight(VOLT, 18, 9);
  voltLight.position.set(0, -0.4, 1.6);
  const purpleLight = new PointLight(PURPLE, 28, 11);
  purpleLight.position.set(-2.4, 2.4, -1.6);
  scene.add(voltLight, purpleLight);

  const controller = buildController();
  controller.position.y = 0.55;
  controller.rotation.x = -0.35;
  const pedestal = buildPedestal();
  pedestal.position.y = -1.15;
  let particles = buildParticles(PARTICLES[tier]);
  scene.add(controller, pedestal, particles);
  scene.background = null;

  // ---- sizing --------------------------------------------------------------
  function resize() {
    const w = frame.clientWidth;
    const h = frame.clientHeight;
    if (!w || !h) return;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, DPR_CAP[tier] || 1.5));
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(frame);

  // ---- input: drag-to-rotate + pointer parallax ------------------------------
  let targetYaw = 0;
  let targetPitch = 0;
  let dragging = false;
  let lastX = 0;
  let lastY = 0;
  let parallaxX = 0;
  let parallaxY = 0;
  canvas.style.touchAction = "pan-y"; // vertical page scroll still works on touch
  canvas.addEventListener("pointerdown", (e) => {
    dragging = true;
    lastX = e.clientX;
    lastY = e.clientY;
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener("pointermove", (e) => {
    if (dragging) {
      targetYaw += (e.clientX - lastX) * 0.008;
      targetPitch = Math.max(-0.7, Math.min(0.7, targetPitch + (e.clientY - lastY) * 0.006));
      lastX = e.clientX;
      lastY = e.clientY;
    } else {
      const r = frame.getBoundingClientRect();
      parallaxX = ((e.clientX - r.left) / r.width - 0.5) * 2;
      parallaxY = ((e.clientY - r.top) / r.height - 0.5) * 2;
    }
  });
  const stopDrag = () => {
    dragging = false;
  };
  canvas.addEventListener("pointerup", stopDrag);
  canvas.addEventListener("pointercancel", stopDrag);

  // ---- render loop: pauses off-screen and on hidden tab ----------------------
  let visible = true;
  let pageShown = !document.hidden;
  let raf = 0;
  let frames = 0;
  let probeStart = 0;
  let probed = false;

  function loop(now) {
    raf = requestAnimationFrame(loop);
    const t = now / 1000;
    if (!dragging) targetYaw += 0.0012; // idle spin
    controller.rotation.y += (targetYaw - controller.rotation.y) * 0.08;
    controller.rotation.x += (-0.35 + targetPitch - controller.rotation.x) * 0.08;
    controller.position.y = 0.55 + Math.sin(t * 1.1) * 0.06; // gentle bob
    camera.position.x += (parallaxX * 0.25 - camera.position.x) * 0.04;
    camera.position.y += (1.1 - parallaxY * 0.2 - camera.position.y) * 0.04;
    camera.lookAt(0, 0.3, 0);
    particles.rotation.y = t * 0.05;
    renderer.render(scene, camera);

    // FPS probe: average over the first 3 s, move one tier, persist (tiers doc).
    if (!probed) {
      if (!probeStart) probeStart = now;
      frames++;
      if (now - probeStart >= 3000) {
        probed = true;
        const fps = frames / ((now - probeStart) / 1000);
        if (fps < 30) {
          if (tier === "HIGH") {
            tier = "MID";
            scene.remove(particles);
            particles = buildParticles(PARTICLES.MID);
            scene.add(particles);
            resize();
          } else {
            // MID below 30 fps → LOW: stop entirely, poster shows again.
            persistTier("LOW");
            stop();
            canvas.remove();
            if (poster) poster.style.opacity = "";
            return;
          }
        } else if (fps > 50 && tier === "MID") {
          tier = "HIGH";
          resize();
        }
        persistTier(tier);
      }
    }
  }

  function playPause() {
    const run = visible && pageShown;
    if (run && !raf) raf = requestAnimationFrame(loop);
    if (!run && raf) {
      cancelAnimationFrame(raf);
      raf = 0;
    }
  }
  function stop() {
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    visible = false;
    renderer.dispose();
  }
  new IntersectionObserver((entries) => {
    visible = entries[0].isIntersecting;
    playPause();
  }).observe(frame);
  document.addEventListener("visibilitychange", () => {
    pageShown = !document.hidden;
    playPause();
  });

  // Mount after the poster SVG so the badge/hint stay on top; cross-fade.
  poster ? poster.after(canvas) : frame.prepend(canvas);
  resize();
  requestAnimationFrame(() => {
    canvas.classList.add("on");
    if (poster) poster.style.opacity = "0";
  });
  playPause();
}
