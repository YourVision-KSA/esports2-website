// Photo treatment for the rev 4 palette (docs/frontend.md → Imagery note): dark
// atmosphere, desaturated, blacks pulled toward the navy ground, soft cyan/magenta
// ambient light. Run on any licensed/event photo before shipping it:
//
//   node scripts/grade-photo.mjs <in> <out> [width height] [--sat 0.6] [--bright 1.0] [--navy 0.25] [--glow 0.2]
//
// width/height crop with attention-aware framing (sharp's "attention" strategy).
// Output format follows the extension of <out> (.jpg / .webp).
import sharp from "sharp";

const args = process.argv.slice(2);
const flag = (name, dflt) => {
  const i = args.indexOf(`--${name}`);
  return i === -1 ? dflt : Number(args[i + 1]);
};
const positional = args.filter((a, i) => !a.startsWith("--") && (i === 0 || !args[i - 1].startsWith("--")));
const [input, output, width, height] = positional;
if (!input || !output) {
  console.error("usage: node scripts/grade-photo.mjs <in> <out> [width height] [--sat --bright --navy --glow]");
  process.exit(2);
}

const SAT = flag("sat", 0.6); // leftover colour after desaturation
const BRIGHT = flag("bright", 1.0);
const NAVY = flag("navy", 0.25); // strength of the navy multiply layer (deepens blacks)
const GLOW = flag("glow", 0.2); // strength of the cyan/magenta corner gradients

let img = sharp(input).rotate(); // apply EXIF orientation
if (width && height) img = img.resize(Number(width), Number(height), { fit: "cover", position: "attention" });
const { width: w, height: h } = width && height ? { width: Number(width), height: Number(height) } : await img.metadata();

// Palette washes (keep in sync with static/css/base.css :root): a navy multiply layer
// pulls the whole frame toward --bg, then faint cyan (low corner) and magenta (top
// corner) radials echo the page ground's two ambient radials.
const overlay = Buffer.from(`<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">
  <rect width="${w}" height="${h}" fill="#050A14" fill-opacity="${NAVY}"/>
  <radialGradient id="c" cx="15%" cy="90%" r="85%">
    <stop offset="0%" stop-color="#3CD6E0" stop-opacity="${GLOW}"/><stop offset="60%" stop-color="#3CD6E0" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="m" cx="88%" cy="8%" r="80%">
    <stop offset="0%" stop-color="#D15EB9" stop-opacity="${GLOW * 0.75}"/><stop offset="60%" stop-color="#D15EB9" stop-opacity="0"/>
  </radialGradient>
  <rect width="${w}" height="${h}" fill="url(#c)"/>
  <rect width="${w}" height="${h}" fill="url(#m)"/>
</svg>`);

const out = await img
  .modulate({ saturation: SAT, brightness: BRIGHT })
  .composite([{ input: overlay, blend: "over" }])
  .toFormat(output.endsWith(".webp") ? "webp" : "jpeg", { quality: 80, mozjpeg: true })
  .toFile(output);
console.log(`written ${output} ${out.width}x${out.height} ${(out.size / 1024).toFixed(0)} KB`);
