#!/usr/bin/env node
/** Rasterize SVG to PNG via @resvg/resvg-js (stdout). Usage: node render_svg_to_png.js <width> <svg-path> */
const fs = require("fs");
const path = require("path");

const width = parseInt(process.argv[2], 10);
const svgPath = process.argv[3];
if (!width || !svgPath) {
  console.error("usage: node render_svg_to_png.js <width> <svg-path>");
  process.exit(1);
}

const resvgRoot = path.resolve(__dirname, "..", "node_modules", "@resvg/resvg-js");
const { Resvg } = require(resvgRoot);
const svg = fs.readFileSync(svgPath);
const resvg = new Resvg(svg, { fitTo: { mode: "width", value: width } });
const png = resvg.render().asPng();
process.stdout.write(png);
