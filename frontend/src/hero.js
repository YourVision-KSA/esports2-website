// Hero scene: game controller over a lit pedestal (docs/frontend.md → 3D scenes).
// Arena Night palette: volt + purple ring accents on near-black. The controller
// is built from primitives (low-poly, zero downloads — a .glb can replace it
// later without touching the mount contract). Drag to rotate + pointer parallax.
import {
  AmbientLight,
  BufferGeometry,
  CanvasTexture,
  CylinderGeometry,
  DirectionalLight,
  ExtrudeGeometry,
  Float32BufferAttribute,
  Group,
  Mesh,
  MeshStandardMaterial,
  PerspectiveCamera,
  PointLight,
  Points,
  PointsMaterial,
  Scene,
  Shape,
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

function bodyOutline() {
  // Top-view silhouette of a real dual-grip gamepad (symmetric, PS-style):
  // wide rounded top, shoulders flaring out, grips sweeping down and in,
  // a thumb valley across the lower middle. Units ≈ the old model's scale.
  const s = new Shape();
  s.moveTo(0, 0.6);
  s.bezierCurveTo(0.55, 0.6, 0.95, 0.56, 1.3, 0.44); // top edge → right shoulder
  s.bezierCurveTo(1.66, 0.3, 1.76, 0.04, 1.72, -0.22); // shoulder round-off
  s.bezierCurveTo(1.68, -0.78, 1.54, -1.32, 1.24, -1.46); // outer grip sweep
  s.bezierCurveTo(0.99, -1.58, 0.77, -1.44, 0.67, -1.1); // grip bottom
  s.bezierCurveTo(0.59, -0.82, 0.48, -0.58, 0.2, -0.5); // inner thumb valley
  s.lineTo(-0.2, -0.5);
  s.bezierCurveTo(-0.48, -0.58, -0.59, -0.82, -0.67, -1.1); // mirrored left side
  s.bezierCurveTo(-0.77, -1.44, -0.99, -1.58, -1.24, -1.46);
  s.bezierCurveTo(-1.54, -1.32, -1.68, -0.78, -1.72, -0.22);
  s.bezierCurveTo(-1.76, 0.04, -1.66, 0.3, -1.3, 0.44);
  s.bezierCurveTo(-0.95, 0.56, -0.55, 0.6, 0, 0.6);
  return s;
}

function buildController() {
  const g = new Group();
  // Real-controller materials: matte dark plastic, rubberized sticks,
  // brand-colored face buttons as the only accents.
  const plastic = new MeshStandardMaterial({ color: 0x1b202b, roughness: 0.52, metalness: 0.12 });
  const plasticDark = new MeshStandardMaterial({ color: 0x0e1218, roughness: 0.62, metalness: 0.1 });
  const rubber = new MeshStandardMaterial({ color: 0x0b0e13, roughness: 0.9, metalness: 0 });
  const cyan = new MeshStandardMaterial({ color: VOLT, emissive: VOLT, emissiveIntensity: 0.35 });
  const magenta = new MeshStandardMaterial({
    color: PURPLE,
    emissive: PURPLE,
    emissiveIntensity: 0.35,
  });

  const bodyGeometry = new ExtrudeGeometry(bodyOutline(), {
    depth: 0.3,
    bevelEnabled: true,
    bevelThickness: 0.17,
    bevelSize: 0.15,
    bevelSegments: 6,
    curveSegments: 32,
  });
  bodyGeometry.translate(0, 0, -0.15); // center the depth; x/y stay as authored
  g.add(new Mesh(bodyGeometry, plastic));
  const FRONT = 0.32; // depth/2 + bevelThickness

  // D-pad on the left lobe: raised cross on a recessed disc.
  const dpadBase = new Mesh(new CylinderGeometry(0.3, 0.32, 0.05, 24), plasticDark);
  dpadBase.position.set(-1.02, 0.02, FRONT);
  dpadBase.rotation.x = Math.PI / 2;
  g.add(dpadBase);
  for (const rot of [0, Math.PI / 2]) {
    const bar = new Mesh(new RoundedBoxGeometry(0.44, 0.15, 0.08, 2, 0.035), rubber);
    bar.position.set(-1.02, 0.02, FRONT + 0.05);
    bar.rotation.z = rot;
    g.add(bar);
  }

  // Face buttons on the right lobe: diamond of four, cyan top / magenta bottom.
  const buttonMats = [cyan, magenta, plasticDark, plasticDark];
  [
    [1.02, 0.26],
    [1.02, -0.22],
    [0.8, 0.02],
    [1.24, 0.02],
  ].forEach(([x, y], i) => {
    const well = new Mesh(new CylinderGeometry(0.105, 0.115, 0.03, 20), plasticDark);
    well.position.set(x, y, FRONT);
    well.rotation.x = Math.PI / 2;
    const b = new Mesh(new CylinderGeometry(0.085, 0.09, 0.06, 20), buttonMats[i]);
    b.position.set(x, y, FRONT + 0.04);
    b.rotation.x = Math.PI / 2;
    g.add(well, b);
  });

  // Symmetric analog sticks in the lower middle: recess ring, stem,
  // concave rubber cap (flattened sphere + raised rim reads as concave).
  for (const x of [-0.44, 0.44]) {
    const recess = new Mesh(new TorusGeometry(0.21, 0.045, 10, 28), plasticDark);
    recess.position.set(x, -0.42, FRONT);
    const stem = new Mesh(new CylinderGeometry(0.065, 0.075, 0.2, 14), plasticDark);
    stem.position.set(x, -0.42, FRONT + 0.1);
    stem.rotation.x = Math.PI / 2;
    const cap = new Mesh(new SphereGeometry(0.155, 20, 14), rubber);
    cap.scale.z = 0.38;
    cap.position.set(x, -0.42, FRONT + 0.2);
    const rim = new Mesh(new TorusGeometry(0.135, 0.028, 10, 24), rubber);
    rim.position.set(x, -0.42, FRONT + 0.23);
    g.add(recess, stem, cap, rim);
  }

  // Center column, PlayStation-style: wide touchpad with a thin light bar
  // above it, slim home button below.
  const touchpad = new Mesh(new RoundedBoxGeometry(0.72, 0.34, 0.05, 3, 0.06), plasticDark);
  touchpad.position.set(0, 0.28, FRONT + 0.02);
  const lightBar = new Mesh(new RoundedBoxGeometry(0.5, 0.045, 0.04, 2, 0.02), cyan);
  lightBar.position.set(0, 0.5, FRONT);
  const home = new Mesh(new CylinderGeometry(0.05, 0.05, 0.05, 16), cyan);
  home.position.set(0, -0.08, FRONT + 0.01);
  home.rotation.x = Math.PI / 2;
  g.add(touchpad, lightBar, home);

  // Shoulder bumpers wrapping the top edge.
  for (const side of [-1, 1]) {
    const bumper = new Mesh(new RoundedBoxGeometry(0.62, 0.16, 0.28, 3, 0.06), plasticDark);
    bumper.position.set(side * 0.98, 0.56, 0.05);
    bumper.rotation.z = side * -0.18;
    g.add(bumper);
  }

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
  const key = new DirectionalLight(0xf2f4ff, 1.4);
  key.position.set(3, 5, 4);
  scene.add(key);
  const fill = new DirectionalLight(0xbfd6e7, 0.45); // soft front fill, plastic reads matte
  fill.position.set(-2, 1, 6);
  scene.add(fill);
  const voltLight = new PointLight(VOLT, 18, 9);
  voltLight.position.set(0, -0.4, 1.6);
  const purpleLight = new PointLight(PURPLE, 28, 11);
  purpleLight.position.set(-2.4, 2.4, -1.6);
  scene.add(voltLight, purpleLight);

  const controller = buildController();
  controller.scale.setScalar(0.68); // owner feedback: the gamepad read far too large
  controller.position.y = 0.72; // body extends downward from its y=0 top edge
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
    controller.position.y = 0.72 + Math.sin(t * 1.1) * 0.05; // gentle bob
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
