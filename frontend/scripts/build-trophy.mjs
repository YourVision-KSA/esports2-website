// Builds static/models/trophy.glb procedurally (docs/frontend.md → 3D scenes).
//
//   npm run model:trophy
//
// The trophy is an original, code-built model (no third-party asset, no licence):
// a classic cup is a solid of revolution, so a smooth LatheGeometry profile +
// polished-metal PBR materials reads as realistic under the scene's environment
// reflections — unlike the faceted low-poly model it replaced (owner asked for a
// realistic, crisp trophy, 2026-11-17).
//
// Parts: square dark plinth + gold plaque → lathe-turned foot/stem/knop/bowl with
// a folded-over rim (visible wall thickness) → two mirrored tube handles.
// Output is compressed like every scene model: weld + quantize + meshopt.
import { resolve } from "node:path";
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS, EXTMeshoptCompression } from "@gltf-transform/extensions";
import { dedup, prune, quantize, reorder, weld } from "@gltf-transform/functions";
import { MeshoptEncoder } from "meshoptimizer";
import {
  BoxGeometry,
  CatmullRomCurve3,
  CubicBezierCurve3,
  Group,
  LatheGeometry,
  Mesh,
  MeshStandardMaterial,
  Scene,
  TubeGeometry,
  Vector2,
  Vector3,
} from "three";
import { GLTFExporter } from "three/examples/jsm/exporters/GLTFExporter.js";

const OUT = resolve(import.meta.dirname, "../../static/models/trophy.glb");

// GLTFExporter assembles the .glb with the browser FileReader API; shim it for Node.
globalThis.FileReader ??= class {
  readAsArrayBuffer(blob) {
    blob.arrayBuffer().then((buf) => {
      this.result = buf;
      this.onloadend?.();
    });
  }
};

// Palette (keep in sync with static/css/base.css :root): rich gold, navy plinth.
const gold = new MeshStandardMaterial({ color: 0xe3b54a, metalness: 1.0, roughness: 0.24 });
const goldMatte = new MeshStandardMaterial({ color: 0xd9a441, metalness: 1.0, roughness: 0.38 });
const plinth = new MeshStandardMaterial({ color: 0x101a2e, metalness: 0.2, roughness: 0.45 });

// --- cup body: smooth revolve ---------------------------------------------------
// Control points (radius, height) of the outer silhouette, bottom → rim.
const outer = [
  [0.001, 0.0],
  [0.4, 0.0],
  [0.46, 0.05],
  [0.44, 0.12],
  [0.3, 0.18],
  [0.17, 0.26],
  [0.13, 0.38],
  [0.12, 0.52],
  [0.19, 0.62], // knop (decorative bead on the stem)
  [0.13, 0.72],
  [0.15, 0.8],
  [0.28, 0.95],
  [0.44, 1.18],
  [0.54, 1.45],
  [0.58, 1.72],
  [0.575, 1.92],
];
// Sample a Catmull-Rom through the silhouette so the lathe is smooth, not segmented.
const spine = new CatmullRomCurve3(outer.map(([r, y]) => new Vector3(r, y, 0)));
const pts = spine.getSpacedPoints(90).map((p) => new Vector2(Math.max(p.x, 0.001), p.y));
// Folded-over rim: small outward lip, then down the inner wall (visible thickness).
pts.push(new Vector2(0.615, 1.97), new Vector2(0.62, 2.02), new Vector2(0.6, 2.04));
for (const [r, y] of [
  [0.555, 1.98],
  [0.52, 1.8],
  [0.46, 1.55],
  [0.34, 1.18],
  [0.22, 0.98],
  [0.001, 0.93],
])
  pts.push(new Vector2(r, y));
const cup = new Mesh(new LatheGeometry(pts, 128), gold);

// --- handles: mirrored curved tubes ----------------------------------------------
function handle(side) {
  const curve = new CubicBezierCurve3(
    new Vector3(side * 0.5, 1.82, 0),
    new Vector3(side * 1.05, 1.95, 0),
    new Vector3(side * 1.02, 1.25, 0),
    new Vector3(side * 0.46, 1.12, 0),
  );
  return new Mesh(new TubeGeometry(curve, 48, 0.05, 20), goldMatte);
}

// --- plinth + plaque --------------------------------------------------------------
const base = new Mesh(new BoxGeometry(1.5, 0.34, 1.5), plinth);
base.position.y = -0.34;
const step = new Mesh(new BoxGeometry(1.14, 0.1, 1.14), plinth);
step.position.y = -0.05;
const plaque = new Mesh(new BoxGeometry(0.62, 0.18, 0.02), goldMatte);
plaque.position.set(0, -0.33, 0.755);

const trophy = new Group();
trophy.add(cup, handle(1), handle(-1), base, step, plaque);
const scene = new Scene();
scene.add(trophy);

// --- export + compress ------------------------------------------------------------
const glb = await new GLTFExporter().parseAsync(scene, { binary: true });
await MeshoptEncoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ "meshopt.encoder": MeshoptEncoder });
const doc = await io.readBinary(new Uint8Array(glb));
await doc.transform(weld(), dedup(), prune(), reorder({ encoder: MeshoptEncoder }), quantize());
doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({
  method: EXTMeshoptCompression.EncoderMethod.QUANTIZE,
});
await io.write(OUT, doc);
const tris = doc
  .getRoot()
  .listMeshes()
  .flatMap((m) => m.listPrimitives())
  .reduce((n, p) => n + (p.getIndices()?.getCount() ?? 0) / 3, 0);
console.log(`written ${OUT}\n  triangles: ${Math.round(tris).toLocaleString()}`);
