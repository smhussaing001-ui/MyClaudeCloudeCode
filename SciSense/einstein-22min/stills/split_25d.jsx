// 2.5D layer split: Subject (transparent PNG) + clean plate background (content-aware filled)
// Usage: set SRC and OUT before running (injected by the caller).
#target photoshop
app.displayDialogs = DialogModes.NO;
function sTID(s){ return stringIDToTypeID(s); }
function cTID(s){ return charIDToTypeID(s); }
function selectSubject(){ var d = new ActionDescriptor(); d.putBoolean(sTID("sampleAllLayers"), false); executeAction(sTID("autoCutout"), d, DialogModes.NO); }
function contentAwareFill(){ var d = new ActionDescriptor(); d.putEnumerated(cTID("Usng"), cTID("FlCn"), sTID("contentAware")); d.putUnitDouble(cTID("Opct"), cTID("#Prc"), 100); d.putEnumerated(cTID("Md  "), cTID("BlnM"), cTID("Nrml")); executeAction(cTID("Fl  "), d, DialogModes.NO); }
function savePNG(doc, path){ var o = new PNGSaveOptions(); o.compression = 6; doc.saveAs(new File(path), o, true, Extension.LOWERCASE); }

var log = [];
var doc = open(new File(SRC));
try {
  if (doc.layers.length === 1 && doc.activeLayer.isBackgroundLayer) { doc.activeLayer.isBackgroundLayer = false; }
  var bg = doc.activeLayer; bg.name = "Background_Plate";
  selectSubject();
  executeAction(sTID("copyToLayer"), undefined, DialogModes.NO);
  var subj = doc.activeLayer; subj.name = "Subject";
  // clean plate: fill where the subject was
  doc.activeLayer = bg;
  subj.visible = false;
  selectSubject();
  doc.selection.expand(new UnitValue(18, "px"));
  contentAwareFill();
  doc.selection.deselect();
  savePNG(doc, OUT + "_bg.png");
  subj.visible = true; bg.visible = false;
  savePNG(doc, OUT + "_fg.png");
  bg.visible = true;
  var psd = new PhotoshopSaveOptions(); psd.layers = true;
  doc.saveAs(new File(OUT + ".psd"), psd, true, Extension.LOWERCASE);
  log.push("ok");
} catch (e) { log.push("ERR " + e.message + " line " + e.line); }
doc.close(SaveOptions.DONOTSAVECHANGES);
log.join("|");
