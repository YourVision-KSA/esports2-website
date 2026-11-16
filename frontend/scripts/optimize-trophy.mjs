// Raw downloaded trophy → web-ready prizes-scene model (docs/frontend.md → 3D scenes + budgets).
//
//   npm run model:trophy -- <path/to/trophy-raw.glb>
//
// Source: "Trophy" by CreativeTrio on poly.pizza (https://poly.pizza/m/fLy8KmmD1t),
// licence CC0 / Public Domain — no attribution required (noted on /credits/ anyway).
// Changes made here:
//   1. recolour to the site palette (docs/frontend.md rev 4): the texture's gold is
//      already ≈ --gold #E9C15C and is kept; the grey plinth is tinted to cool silver
//   2. material: metallic/roughness tuned so the cup reads as polished gold under the
//      scene's RoomEnvironment reflections (the source is matte-stylized)
//   3. performance: opaque material, quantize + meshopt geometry compression,
//      WebP texture (128 px palette atlas — already tiny)
// Output: static/models/trophy.glb (518 triangles, a few tens of KB). Then: npm run budget
import { resolve } from "node:path";
import { NodeIO } from "@gltf-transform/core";
import { ALL_EXTENSIONS, EXTMeshoptCompression } from "@gltf-transform/extensions";
import { dedup, prune, quantize, reorder, textureCompress, weld } from "@gltf-transform/functions";
import { MeshoptEncoder } from "meshoptimizer";
import sharp from "sharp";

const [input] = process.argv.slice(2);
if (!input) {
  console.error("usage: npm run model:trophy -- <trophy-raw.glb>");
  process.exit(2);
}
const OUT = resolve(import.meta.dirname, "../../static/models/trophy.glb");

// Cool-silver multiplier for the grey plinth (keep in sync with --silver in base.css)
const SILVER = [0.78, 0.83, 0.92];

await MeshoptEncoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ "meshopt.encoder": MeshoptEncoder });
const doc = await io.read(resolve(input));
const root = doc.getRoot();

for (const mat of root.listMaterials()) {
  mat.setAlphaMode("OPAQUE").setDoubleSided(false);
  // polished metal under the scene env map; the texture supplies gold vs silver
  mat.setMetallicFactor(0.85).setRoughnessFactor(0.32);
  const tex = mat.getBaseColorTexture();
  if (tex) {
    const { data, info } = await sharp(Buffer.from(tex.getImage())).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
    for (let i = 0; i < data.length; i += 4) {
      const [r, g, b] = [data[i], data[i + 1], data[i + 2]];
      const spread = Math.max(r, g, b) - Math.min(r, g, b);
      if (spread < 24) {
        // grey (the plinth) → cool silver
        data[i] = Math.min(255, r * SILVER[0]);
        data[i + 1] = Math.min(255, g * SILVER[1]);
        data[i + 2] = Math.min(255, b * SILVER[2]);
      }
      data[i + 3] = 255; // opaque material: alpha unused
    }
    tex.setImage(await sharp(data, { raw: { width: info.width, height: info.height, channels: 4 } }).png().toBuffer());
    tex.setMimeType("image/png");
  }
}

await doc.transform(
  weld(),
  dedup(),
  prune(),
  reorder({ encoder: MeshoptEncoder }),
  quantize(),
  textureCompress({ encoder: sharp, targetFormat: "webp", quality: 90 }),
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
