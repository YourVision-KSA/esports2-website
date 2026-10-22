/* The hero game controller, built in code (no model file, no third-party licence,
   no brand marks). Styled after the event logo: silver body, cyan D-pad, magenta face
   buttons, navy sticks and shoulders. Faces +Z; roughly 3 units wide, centred. */

import {
  CylinderGeometry,
  ExtrudeGeometry,
  Group,
  Mesh,
  MeshStandardMaterial,
  Shape,
  TorusGeometry,
} from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";

// Brand colours (docs/frontend.md rev 4) — keep in sync with static/css/base.css :root.
const SILVER = 0x9eaabb;
const SILVER_LIGHT = 0xc3ccd8;
const NAVY = 0x0b1322;
const CYAN = 0x3cd6e0;
const MAGENTA = 0xd15eb9;
// deeper tones for parts sitting on the silver body (legibility, like the logo emblem)
const CYAN_DEEP = 0x13a9b7;
const MAGENTA_DEEP = 0xb2379a;

/** Top-view outline: wide body, two flared grips, a soft arch between them. */
function bodyShape() {
  const s = new Shape();
  s.moveTo(0, 0.78);
  s.bezierCurveTo(0.6, 0.8, 1.15, 0.86, 1.38, 0.6); // top edge → right shoulder
  s.bezierCurveTo(1.62, 0.35, 1.72, -0.3, 1.56, -0.86); // right side down the grip
  s.bezierCurveTo(1.46, -1.22, 1.02, -1.3, 0.88, -1.0); // rounded grip end
  s.bezierCurveTo(0.74, -0.7, 0.55, -0.44, 0, -0.44); // inner grip → centre arch
  s.bezierCurveTo(-0.55, -0.44, -0.74, -0.7, -0.88, -1.0); // mirror for the left half
  s.bezierCurveTo(-1.02, -1.3, -1.46, -1.22, -1.56, -0.86);
  s.bezierCurveTo(-1.72, -0.3, -1.62, 0.35, -1.38, 0.6);
  s.bezierCurveTo(-1.15, 0.86, -0.6, 0.8, 0, 0.78);
  return s;
}

export function buildController() {
  const mat = {
    body: new MeshStandardMaterial({ color: SILVER, metalness: 0.7, roughness: 0.3 }),
    panel: new MeshStandardMaterial({ color: SILVER_LIGHT, metalness: 0.5, roughness: 0.22 }),
    dark: new MeshStandardMaterial({ color: NAVY, metalness: 0.2, roughness: 0.6 }),
    cyan: new MeshStandardMaterial({ color: CYAN_DEEP, emissive: CYAN, emissiveIntensity: 0.12, roughness: 0.3 }),
    magenta: new MeshStandardMaterial({ color: MAGENTA_DEEP, emissive: MAGENTA, emissiveIntensity: 0.1, roughness: 0.3 }),
    light: new MeshStandardMaterial({ color: CYAN, emissive: CYAN, emissiveIntensity: 0.7 }),
  };
  const g = new Group();

  // body: extruded outline with a generous bevel so it reads as moulded plastic
  const DEPTH = 0.36;
  const BEVEL = 0.14;
  const bodyGeo = new ExtrudeGeometry(bodyShape(), {
    depth: DEPTH,
    bevelEnabled: true,
    bevelThickness: BEVEL,
    bevelSize: 0.12,
    bevelSegments: 5,
    curveSegments: 28,
  });
  bodyGeo.translate(0, 0, -DEPTH / 2);
  g.add(new Mesh(bodyGeo, mat.body));
  const FRONT = DEPTH / 2 + BEVEL; // z of the face surface

  // touch panel + light strips either side (the cyan "light bar")
  const panel = new Mesh(new RoundedBoxGeometry(0.98, 0.5, 0.06, 4, 0.05), mat.panel);
  panel.position.set(0, 0.36, FRONT + 0.01);
  g.add(panel);
  for (const x of [-0.53, 0.53]) {
    const strip = new Mesh(new RoundedBoxGeometry(0.035, 0.42, 0.04, 2, 0.015), mat.light);
    strip.position.set(x, 0.36, FRONT + 0.01);
    g.add(strip);
  }

  // D-pad (cyan), left
  const dpad = new Group();
  dpad.add(new Mesh(new RoundedBoxGeometry(0.44, 0.14, 0.08, 3, 0.035), mat.cyan));
  dpad.add(new Mesh(new RoundedBoxGeometry(0.14, 0.44, 0.08, 3, 0.035), mat.cyan));
  dpad.position.set(-0.98, 0.22, FRONT + 0.02);
  g.add(dpad);

  // face buttons (magenta), right — plain discs, no symbols
  const btnGeo = new CylinderGeometry(0.085, 0.085, 0.08, 32);
  btnGeo.rotateX(Math.PI / 2);
  for (const [dx, dy] of [
    [0, 0.17],
    [0, -0.17],
    [-0.17, 0],
    [0.17, 0],
  ]) {
    const b = new Mesh(btnGeo, mat.magenta);
    b.position.set(0.98 + dx, 0.22 + dy, FRONT + 0.03);
    g.add(b);
  }

  // thumbsticks (navy cap on a silver collar)
  const collarGeo = new TorusGeometry(0.2, 0.035, 12, 48);
  const capGeo = new CylinderGeometry(0.17, 0.19, 0.16, 40);
  capGeo.rotateX(Math.PI / 2);
  for (const x of [-0.5, 0.5]) {
    const collar = new Mesh(collarGeo, mat.panel);
    collar.position.set(x, -0.2, FRONT + 0.01);
    g.add(collar);
    const cap = new Mesh(capGeo, mat.dark);
    cap.position.set(x, -0.2, FRONT + 0.08);
    g.add(cap);
  }

  // shoulder buttons (navy), along the top edge
  for (const x of [-1.0, 1.0]) {
    const sh = new Mesh(new RoundedBoxGeometry(0.62, 0.16, 0.3, 3, 0.06), mat.dark);
    sh.position.set(x, 0.74, -0.02);
    sh.rotation.z = x > 0 ? -0.12 : 0.12;
    g.add(sh);
  }

  return g;
}
