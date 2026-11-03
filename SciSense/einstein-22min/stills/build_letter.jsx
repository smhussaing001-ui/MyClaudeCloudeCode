// Builds the "Besso letter" document as separate PNG layers for a Magnates-style 3D document shot.
#target photoshop
app.displayDialogs = DialogModes.NO;
app.preferences.rulerUnits = Units.PIXELS;
app.preferences.typeUnits = TypeUnits.PIXELS;
var OUT = "D:/Claude/SciSense/einstein-22min/stills/letter/";
new Folder(OUT).create();
var W = 2000, H = 2600;
var log = [];

function rgb(r,g,b){ var c = new SolidColor(); c.rgb.red=r; c.rgb.green=g; c.rgb.blue=b; return c; }
function savePNG(doc, name){ var o = new PNGSaveOptions(); o.compression = 6; doc.saveAs(new File(OUT + name), o, true, Extension.LOWERCASE); }
function only(doc, keep){ for (var i=0;i<doc.layers.length;i++) doc.layers[i].visible = false; for (var j=0;j<keep.length;j++) keep[j].visible = true; }
function textLayer(doc, name, str, font, size, color, x, y, w, h){
  var l = doc.artLayers.add(); l.kind = LayerKind.TEXT; l.name = name;
  var t = l.textItem; t.kind = TextType.PARAGRAPHTEXT; t.contents = str; t.font = font; t.size = size;
  t.color = color; t.position = [x, y]; t.width = w; t.height = h; t.leading = size * 1.55; t.useAutoLeading = false;
  return l;
}

try {
  var doc = app.documents.add(W, H, 72, "BessoLetter", NewDocumentMode.RGB, DocumentFill.TRANSPARENT);
  // --- paper ---
  var paper = doc.artLayers.add(); paper.name = "Paper";
  doc.selection.selectAll(); doc.selection.fill(rgb(232,222,198)); doc.selection.deselect();
  paper.applyAddNoise(7, NoiseDistribution.GAUSSIAN, true);
  paper.applyGaussianBlur(0.6);
  // stains / uneven ageing
  var stain = doc.artLayers.add(); stain.name = "Ageing";
  app.foregroundColor = rgb(120,95,60); app.backgroundColor = rgb(232,222,198);
  stain.applyClouds(); stain.blendMode = BlendMode.MULTIPLY; stain.opacity = 22;
  // --- header (readable, factual) ---
  var hdr = textLayer(doc, "Header", "Princeton, March 1955", "CourierNewPSMT", 44, rgb(40,32,24), 1080, 230, 760, 120);
  // --- body: illegible filler, blurred so it can't be read ---
  var filler = "";
  for (var k=0;k<60;k++) filler += "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ";
  var body1 = textLayer(doc, "BodyTop", filler, "CourierNewPSMT", 40, rgb(45,36,28), 180, 420, 1640, 780);
  var body2 = textLayer(doc, "BodyBottom", filler, "CourierNewPSMT", 40, rgb(45,36,28), 180, 1560, 1640, 820);
  body1.rasterize(RasterizeType.ENTIRELAYER); body1.applyGaussianBlur(7); body1.applyMotionBlur(0, 18); body1.opacity = 70;
  body2.rasterize(RasterizeType.ENTIRELAYER); body2.applyGaussianBlur(7); body2.applyMotionBlur(0, 18); body2.opacity = 70;
  // --- key line (crisp), 3 point-text lines ---
  var lines = ["\u2026for us physicists, the distinction", "between past, present and future is", "only a stubbornly persistent illusion."];
  var ys = [1300, 1390, 1480];
  var keyLayers = [];
  for (var i=0;i<lines.length;i++){
    var l = doc.artLayers.add(); l.kind = LayerKind.TEXT; l.name = "KeyLine" + (i+1);
    var t = l.textItem; t.kind = TextType.POINTTEXT; t.contents = lines[i]; t.font = "CourierNewPSMT"; t.size = 56; t.color = rgb(25,18,12);
    t.position = [180, ys[i]];
    keyLayers.push(l);
  }
  // --- highlighter strokes sized to each line ---
  var hl = doc.artLayers.add(); hl.name = "Highlight";
  app.foregroundColor = rgb(242,205,70);
  for (var j=0;j<keyLayers.length;j++){
    var b = keyLayers[j].bounds; // [left, top, right, bottom]
    var x0 = b[0].as("px") - 14, x1 = b[2].as("px") + 14, y0 = b[1].as("px") - 10, y1 = b[3].as("px") + 12;
    doc.selection.select([[x0, y0+3],[x1, y0],[x1-4, y1],[x0+3, y1-2]]);
    doc.selection.fill(app.foregroundColor);
  }
  doc.selection.deselect();
  hl.applyGaussianBlur(2.0);
  // merge key lines into one raster layer
  for (var m=keyLayers.length-1;m>0;m--){ keyLayers[m].rasterize(RasterizeType.ENTIRELAYER); }
  keyLayers[0].rasterize(RasterizeType.ENTIRELAYER);
  var keySet = doc.layerSets.add(); keySet.name = "Key";
  for (var n=keyLayers.length-1;n>=0;n--){ keyLayers[n].move(keySet, ElementPlacement.INSIDE); }
  var key = keySet.merge(); key.name = "KeyLine";

  // --- export layers ---
  only(doc, [paper, stain, hdr, body1, body2]); savePNG(doc, "letter_paper.png");
  only(doc, [key]); savePNG(doc, "letter_keyline.png");
  only(doc, [hl]); savePNG(doc, "letter_highlight.png");
  only(doc, [paper, stain, hdr, body1, body2, hl, key]); hl.blendMode = BlendMode.MULTIPLY; hl.opacity = 75; savePNG(doc, "letter_preview.png");
  var psd = new PhotoshopSaveOptions(); psd.layers = true;
  doc.saveAs(new File(OUT + "letter.psd"), psd, true, Extension.LOWERCASE);
  doc.close(SaveOptions.DONOTSAVECHANGES);
  log.push("ok");
} catch(e) { log.push("ERR " + e.message + " line " + e.line); }
log.join("|");
