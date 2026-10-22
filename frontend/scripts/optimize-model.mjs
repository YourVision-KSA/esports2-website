// Raw Sketchfab download → web-ready hero model (docs/frontend.md → 3D scenes + budgets).
//
//   npm run model -- <path/to/scene.gltf> [simplifyRatio=0.4]
//
// Source: "Dualsense" by miwaVV, CC BY 4.0 (https://sketchfab.com/3d-models/dualsense-14a6fa6d7078463380cc72fe0bc5acb0).
// The licence requires credit and allows changes; the changes made here are:
//   1. brand cleanup: remove the PlayStation-logo button mesh and erase the △ ○ ✕ □
//      symbols from the face-button texture (trademarks — not ours to use)
//   2. recolour to the site palette (docs/frontend.md rev 4): white plastic → cool silver,
//      black plastic → navy, blue light bar → logo cyan
//   3. performance: drop unused UV sets/tangents, opaque materials (no alpha sorting),
//      mesh simplification, meshopt geometry compression, WebP textures ≤ 1024 px
//      (WebP, not KTX2 — see docs/frontend.md).
// Output: static/models/controller.glb. Then run: npm run budget
import { resolve } from "node:path";
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS, EXTMeshoptCompression } from "@gltf-transform/extensions";
import { dedup, prune, quantize, reorder, simplify, textureCompress, weld } from "@gltf-transform/functions";
import { MeshoptEncoder, MeshoptSimplifier } from "meshoptimizer";
import sharp from "sharp";

const [input, ratioArg = "0.4"] = process.argv.slice(2);
if (!input) {
  console.error("usage: npm run model -- <scene.gltf> [simplifyRatio]");
  process.exit(2);
}
const OUT = resolve(import.meta.dirname, "../../static/models/controller.glb");
const TEX = 1024; // texture edge after resize

// Palette (keep in sync with static/css/base.css :root)
const SILVER = [0.74, 0.79, 0.86]; // multiplier applied to white plastic (logo silver)
const NAVY = [14, 24, 40]; // replaces black plastic (scaled by original brightness)
const CYAN = [60, 214, 224];

// Face-button symbol centres in the 1024 px "GamepadStuff" base-colour texture
// (found by inspecting the texture; radius covers each glyph).
const SYMBOLS = [
  [860, 36],
  [880, 536],
  [570, 856],
  [36, 884],
];
const SYMBOL_RADIUS = 48;

const luma = (r, g, b) => 0.2126 * r + 0.7152 * g + 0.0722 * b;

async function editTexture(texture, edit) {
  if (!texture) return;
  const { data, info } = await sharp(Buffer.from(texture.getImage()))
    .resize(TEX, TEX)
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  edit(data, info.width);
  texture.setImage(await sharp(data, { raw: { width: info.width, height: info.height, channels: 4 } }).png().toBuffer());
  texture.setMimeType("image/png");
}

function recolourPlastic(px) {
  for (let i = 0; i < px.length; i += 4) {
    const l = luma(px[i], px[i + 1], px[i + 2]);
    if (l > 150) {
      // white/grey plastic → cool silver
      px[i] *= SILVER[0];
      px[i + 1] *= SILVER[1];
      px[i + 2] *= SILVER[2];
    } else if (l < 70) {
      // black plastic → navy, keeping the original shading
      const k = Math.max(l, 8) / 34;
      px[i] = Math.min(255, NAVY[0] * k);
      px[i + 1] = Math.min(255, NAVY[1] * k);
      px[i + 2] = Math.min(255, NAVY[2] * k);
    }
    px[i + 3] = 255; // opaque material: alpha unused
  }
}

function eraseSymbols(px, width) {
  for (const [cx, cy] of SYMBOLS) {
    for (let y = cy - SYMBOL_RADIUS; y <= cy + SYMBOL_RADIUS; y++) {
      for (let x = cx - SYMBOL_RADIUS; x <= cx + SYMBOL_RADIUS; x++) {
        if (x < 0 || y < 0 || x >= width || y >= width) continue;
        const i = (y * width + x) * 4;
        const l = luma(px[i], px[i + 1], px[i + 2]);
        if (l > 60 && l < 240) px[i] = px[i + 1] = px[i + 2] = 255; // grey glyph strokes → button white
      }
    }
  }
}

function cyanEmissive(px) {
  for (let i = 0; i < px.length; i += 4) {
    const v = Math.max(px[i], px[i + 1], px[i + 2]) / 255;
    px[i] = CYAN[0] * v;
    px[i + 1] = CYAN[1] * v;
    px[i + 2] = CYAN[2] * v;
  }
}

await MeshoptEncoder.ready;
await MeshoptSimplifier.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ "meshopt.encoder": MeshoptEncoder });
const doc = await io.read(resolve(input));
const root = doc.getRoot();

// 1. remove the PlayStation-logo button
for (const node of root.listNodes()) {
  if (node.getName() === "logo") node.dispose();
}

// 3a. geometry attributes the materials never read
for (const mesh of root.listMeshes()) {
  for (const prim of mesh.listPrimitives()) {
    for (const sem of ["TEXCOORD_1", "TEXCOORD_2", "TEXCOORD_3", "TANGENT"]) {
      const acc = prim.getAttribute(sem);
      if (acc) {
        prim.setAttribute(sem, null);
        if (!acc.listParents().some((p) => p !== root)) acc.dispose();
      }
    }
  }
}

// 1 + 2. textures; 3b. opaque, single-sided materials
for (const mat of root.listMaterials()) {
  mat.setAlphaMode("OPAQUE").setDoubleSided(false);
  const isButtons = mat.getName() === "GamepadStuff";
  await editTexture(mat.getBaseColorTexture(), (px, w) => {
    if (isButtons) eraseSymbols(px, w);
    recolourPlastic(px);
  });
  await editTexture(mat.getEmissiveTexture(), cyanEmissive);
}

// 3c. mesh + texture compression
await doc.transform(
  weld(),
  simplify({ simplifier: MeshoptSimplifier, ratio: Number(ratioArg), error: 0.0008 }),
  dedup(),
  prune(),
  reorder({ encoder: MeshoptEncoder }),
  quantize(),
  textureCompress({ encoder: sharp, targetFormat: "webp", resize: [TEX, TEX], quality: 82 }),
);
doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({
  method: EXTMeshoptCompression.EncoderMethod.QUANTIZE,
});

await io.write(OUT, doc);
const tris = root
  .listMeshes()
  .flatMap((m) => m.listPrimitives())
  .reduce((n, p) => n + (p.getIndices()?.getCount() ?? 0) / 3, 0);
console.log(`written ${OUT}\n  triangles: ${Math.round(tris).toLocaleString()}`);
