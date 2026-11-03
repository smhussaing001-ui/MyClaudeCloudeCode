// SciSense - Marker 12 animation (33 s): "four papers... your time and my time..."
// Builds scene precomps + main comp, then renders. Log -> m12/build_log.txt
(function () {
var A = "D:/Scci sense/";
var M = "D:/Claude/SciSense/einstein-22min/m12/";
var LOG = [];
function log(s) { LOG.push(s); }
function flush() { var f = new File(M + "build_log.txt"); f.open("w"); f.write(LOG.join("\n")); f.close(); }
var W = 1920, H = 1080, FPS = 30;
var proj = app.project;
app.beginUndoGroup("Build M12");
try {
  // ---------- helpers ----------
  for (var r = proj.numItems; r >= 1; r--) { var it0 = proj.item(r); if (it0 instanceof FolderItem && it0.name === "M12_Einstein_FourPapers") it0.remove(); }
  var folder = proj.items.addFolder("M12_Einstein_FourPapers");
  function imp(path) {
    var io = new ImportOptions(new File(path));
    var it = proj.importFile(io); it.parentFolder = folder; return it;
  }
  function comp(name, dur) { var c = proj.items.addComp(name, W, H, 1, dur, FPS); c.parentFolder = folder; return c; }
  function fx(layer, match) { return layer.property("ADBE Effect Parade").addProperty(match); }
  function glow(layer, thr, rad, inten) {
    var g = fx(layer, "ADBE Glo2");
    g.property("ADBE Glo2-0002").setValue(thr);  // threshold
    g.property("ADBE Glo2-0003").setValue(rad);  // radius
    g.property("ADBE Glo2-0004").setValue(inten);// intensity
    return g;
  }
  function key(prop, times, vals) { for (var i = 0; i < times.length; i++) prop.setValueAtTime(times[i], vals[i]); }
  function ease(prop) {
    for (var k = 1; k <= prop.numKeys; k++) {
      var e = new KeyframeEase(0, 70);
      var dims = (prop.value instanceof Array) ? prop.value.length : 1;
      var arr = []; for (var d = 0; d < dims; d++) arr.push(e);
      try { prop.setTemporalEaseAtKey(k, arr, arr); } catch (err) {}
    }
  }
  function ellipseMask(layer, feather) {
    var m = layer.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
    var w = layer.width, h = layer.height, k = 0.5523, cx = w/2, cy = h/2, rx = w/2, ry = h/2;
    var sh = new Shape();
    sh.vertices = [[cx, cy-ry],[cx+rx, cy],[cx, cy+ry],[cx-rx, cy]];
    sh.inTangents = [[-rx*k,0],[0,-ry*k],[rx*k,0],[0,ry*k]];
    sh.outTangents = [[rx*k,0],[0,ry*k],[-rx*k,0],[0,-ry*k]];
    sh.closed = true; m.property("ADBE Mask Shape").setValue(sh); m.property("ADBE Mask Feather").setValue([feather, feather]);
    return m;
  }
  function solid(c, name, col, w, h) { return c.layers.addSolid(col, name, w || W, h || H, 1); }
  function cam(c, name) { var l = c.layers.addCamera(name, [W/2, H/2]); l.property("ADBE Camera Options Group").property("ADBE Camera Zoom").setValue(1600); return l; }
  function finish(c) {
    // grain + vignette on an adjustment layer
    var adj = solid(c, "Grain_Vignette", [0,0,0]); adj.adjustmentLayer = true;
    var n = fx(adj, "ADBE Noise"); n.property("ADBE Noise-0001").setValue(5);
    var v = solid(c, "Vignette", [0,0,0]);
    var mask = v.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
    var shp = new Shape(); var rx = W*0.62, ry = H*0.66, cx = W/2, cy = H/2, k = 0.5523;
    shp.vertices = [[cx, cy-ry],[cx+rx, cy],[cx, cy+ry],[cx-rx, cy]];
    shp.inTangents = [[-rx*k,0],[0,-ry*k],[rx*k,0],[0,ry*k]];
    shp.outTangents = [[rx*k,0],[0,ry*k],[-rx*k,0],[0,-ry*k]];
    shp.closed = true;
    mask.property("ADBE Mask Shape").setValue(shp);
    mask.property("ADBE Mask Feather").setValue([420,420]);
    mask.inverted = true;
    v.opacity.setValue(70);
  }

  // ---------- assets ----------
  var aAtom  = imp(A + "abstract-atom-structure-with-glowing-particle-orbi-2026-10-03-16-41-34-utc.mov");
  var aChalk = imp(A + "chalkboard-full-of-intricate-math-equations-and-gr-2026-10-02-20-23-58-utc.mov");
  var aClock = imp(A + "vintage-clock-face-time-lapse-animation-2026-10-03-06-15-31-utc.mov");
  var aLeak  = imp(A + "cinematic-sun-rays-light-leak-overlay-2026-10-03-09-17-08-utc.mov");
  var aBurn  = imp(A + "grungy-retro-film-burn-overlay-with-light-leaks-2026-10-03-10-40-06-utc.mov");
  var e04fg  = imp(M + "layers/einstein1904_fg.png");
  var e04bg  = imp(M + "layers/einstein1904_bg.png");
  var dkfg   = imp(M + "layers/einstein_desk_fg.png");
  var dkbg   = imp(M + "layers/einstein_desk_bg.png");
  var paper  = imp("D:/Claude/SciSense/einstein-22min/stills/letter/letter_paper.png");
  log("assets imported");

  // ======================= S1: light knocks electrons out of metal (3.6 s) =======================
  var s1 = comp("S1_Photoelectric", 3.6);
  solid(s1, "BG", [0.02,0.025,0.035]);
  var plate = solid(s1, "MetalPlate", [0.5,0.5,0.52], 1400, 260);
  var ramp = fx(plate, "ADBE Ramp");
  ramp.property("ADBE Ramp-0001").setValue([700, 0]); ramp.property("ADBE Ramp-0003").setValue([700, 260]);
  ramp.property("ADBE Ramp-0002").setValue([0.75,0.76,0.8]); ramp.property("ADBE Ramp-0004").setValue([0.18,0.18,0.2]);
  plate.threeDLayer = true; plate.position.setValue([W/2, 760, 0]);
  plate.property("ADBE Transform Group").property("ADBE Rotate X").setValue(-72);
  var beam = solid(s1, "LightBeam", [1,0.92,0.75], 1500, 14);
  beam.position.setValue([W/2 - 360, 420]); beam.rotation.setValue(32);
  var wipe = fx(beam, "ADBE Linear Wipe");
  wipe.property("ADBE Linear Wipe-0002").setValue(270);
  key(wipe.property("ADBE Linear Wipe-0001"), [0, 0.8], [100, 50]);
  wipe.property("ADBE Linear Wipe-0003").setValue(40);
  glow(beam, 30, 60, 2.5);
  var parts = solid(s1, "Electrons", [0,0,0]);
  var pw = fx(parts, "CC Particle World");
  try {
    key(pw.property("Birth Rate"), [0, 0.79, 0.8, 1.25, 1.26], [0, 0, 2.5, 2.5, 0]);
    pw.property("Longevity (sec)").setValue(2.2);
    pw.property("Position Y").setValue(0.12);
    pw.property("Radius X").setValue(0.02);
    pw.property("Radius Y").setValue(0.0);
    pw.property("Radius Z").setValue(0.02);
    pw.property("Velocity").setValue(1.1);
    pw.property("Gravity").setValue(0.05);
    pw.property("Birth Size").setValue(0.035);
    pw.property("Death Size").setValue(0.0);
    pw.property("Birth Color").setValue([0.6,0.9,1]);
    pw.property("Death Color").setValue([0.2,0.5,1]);
    log("S1 particles ok");
  } catch (e) { log("S1 particles partial: " + e.toString()); }
  glow(parts, 20, 30, 3);
  var flash = solid(s1, "ImpactFlash", [1,0.95,0.85], 600, 600);
  flash.position.setValue([W/2, 640]);
  ellipseMask(flash, 260);
  flash.blendingMode = BlendingMode.ADD;
  key(flash.opacity, [0.75, 0.85, 1.6], [0, 85, 0]);
  var c1 = cam(s1, "Cam");
  key(c1.position, [0, 3.6], [[W/2, H/2, -1600], [W/2, H/2+20, -1380]]); ease(c1.position);
  finish(s1); log("S1 built");

  // ======================= S2: atoms are real (2.2 s) =======================
  var s2 = comp("S2_Atoms", 2.2);
  var at = s2.layers.add(aAtom); at.audioEnabled = false;
  key(at.scale, [0, 2.2], [[112,112], [126,126]]);
  glow(at, 85, 25, 0.4);
  finish(s2); log("S2 built");

  // ======================= S3: the most famous equation (3.5 s) =======================
  var s3 = comp("S3_Equation", 3.5);
  var ch = s3.layers.add(aChalk); ch.audioEnabled = false;
  var bcx = fx(ch, "ADBE Brightness & Contrast 2"); bcx.property("ADBE Brightness & Contrast 2-0001").setValue(-45);
  var gb = fx(ch, "ADBE Gaussian Blur 2"); key(gb.property("ADBE Gaussian Blur 2-0001"), [0, 0.6], [0, 9]);
  key(ch.scale, [0, 3.5], [[100,100],[110,110]]);
  var eq = s3.layers.addText("E = mc\u00B2");
  var td = eq.property("ADBE Text Properties").property("ADBE Text Document").value;
  td.resetCharStyle(); td.fontSize = 230; td.fillColor = [0.96,0.95,0.9]; td.font = "TimesNewRomanPS-ItalicMT"; td.justification = ParagraphJustification.CENTER_JUSTIFY;
  eq.property("ADBE Text Properties").property("ADBE Text Document").setValue(td);
  eq.position.setValue([W/2, H/2 + 70]);
  var ew = fx(eq, "ADBE Linear Wipe");
  ew.property("ADBE Linear Wipe-0002").setValue(90);
  ew.property("ADBE Linear Wipe-0003").setValue(60);
  key(ew.property("ADBE Linear Wipe-0001"), [0.3, 1.5], [100, 0]);
  key(eq.scale, [0.3, 3.5], [[96,96],[106,106]]);
  glow(eq, 50, 55, 1.8);
  finish(s3); log("S3 built");

  // ======================= S4: 1904 Einstein 2.5D + 1905 manuscript (8.7 s) =======================
  var s4 = comp("S4_Einstein1904_Paper", 8.7);
  solid(s4, "Backdrop", [0.08,0.075,0.07]);
  var bg4 = s4.layers.add(e04bg); bg4.threeDLayer = true;
  var fg4 = s4.layers.add(e04fg); fg4.threeDLayer = true;
  var baseScale = H / e04fg.height * 100 * 1.02;
  fg4.position.setValue([W/2 - 120, H/2 + 30, 0]); fg4.scale.setValue([baseScale, baseScale, 100]);
  var depth = 700, camZ = -1600;
  var comp4 = (depth - camZ) / (-camZ) * 1.12;
  var cover4 = Math.max(W / e04bg.width, H / e04bg.height) * 100 * 1.18;
  bg4.position.setValue([W/2, H/2, depth]); bg4.scale.setValue([cover4*comp4, cover4*comp4, 100]);
  // warm practical glow behind him
  var halo = solid(s4, "BackLight", [1,0.78,0.5], 1300, 1300); halo.threeDLayer = true;
  halo.position.setValue([W/2 + 260, H/2 - 120, depth - 50]);
  ellipseMask(halo, 600);
  halo.blendingMode = BlendingMode.SCREEN; halo.opacity.setValue(35);
  // manuscript page drops in at 4.4 s
  var pg = s4.layers.add(paper); pg.threeDLayer = true;
  var pgScale = 26;
  pg.scale.setValue([pgScale, pgScale, 100]);
  key(pg.position, [4.4, 5.6], [[W/2 + 520, H + 700, -350], [W/2 + 330, H/2 + 120, -260]]); ease(pg.position);
  key(pg.property("ADBE Transform Group").property("ADBE Rotate X"), [4.4, 5.6], [-60, -18]); ease(pg.property("ADBE Transform Group").property("ADBE Rotate X"));
  key(pg.property("ADBE Transform Group").property("ADBE Rotate Z"), [4.4, 5.6], [-24, -6]);
  key(pg.opacity, [4.4, 4.7], [0, 100]);
  function pageText(str, size, font, y) {
    var t = s4.layers.addText(str);
    var d = t.property("ADBE Text Properties").property("ADBE Text Document").value;
    d.resetCharStyle(); d.fontSize = size; d.fillColor = [0.12,0.09,0.06]; d.font = font; d.justification = ParagraphJustification.CENTER_JUSTIFY;
    t.property("ADBE Text Properties").property("ADBE Text Document").setValue(d);
    t.threeDLayer = true; t.parent = pg;
    t.position.setValue([1000, y, -1]); t.scale.setValue([100,100,100]);
    return t;
  }
  pageText("ANNALEN DER PHYSIK", 100, "TimesNewRomanPS-BoldMT", 420);
  pageText("1905", 90, "TimesNewRomanPSMT", 560);
  pageText("Zur Elektrodynamik", 118, "TimesNewRomanPS-BoldMT", 900);
  pageText("bewegter K\u00F6rper", 150, "TimesNewRomanPS-BoldMT", 1080);
  pageText("von A. Einstein", 100, "TimesNewRomanPS-ItalicMT", 1260);
  var c4 = cam(s4, "Cam");
  key(c4.position, [0, 4.6, 8.7], [[W/2 - 60, H/2 + 10, camZ], [W/2 + 40, H/2 - 10, camZ + 260], [W/2 + 300, H/2 + 90, camZ + 470]]); ease(c4.position);
  finish(s4); log("S4 built");

  // ======================= S5: your time and my time (4.3 s) =======================
  var s5 = comp("S5_TwoClocks", 4.3);
  solid(s5, "BG", [0.03,0.03,0.035]);
  var ck1 = s5.layers.add(aClock); ck1.audioEnabled = false; ck1.scale.setValue([52,52]); ck1.position.setValue([W*0.27, H/2]);
  var ck2 = s5.layers.add(aClock); ck2.audioEnabled = false; ck2.scale.setValue([52,52]); ck2.position.setValue([W*0.73, H/2]);
  ck2.stretch = 350; ck2.startTime = 0;
  var tint2 = fx(ck2, "ADBE Tint"); tint2.property("ADBE Tint-0002").setValue([0.55,0.8,1]); tint2.property("ADBE Tint-0003").setValue(35);
  var tint1 = fx(ck1, "ADBE Tint"); tint1.property("ADBE Tint-0002").setValue([1,0.8,0.5]); tint1.property("ADBE Tint-0003").setValue(35);
  var div = solid(s5, "Divider", [1,0.95,0.85], 6, 760); div.position.setValue([W/2, H/2]);
  key(div.scale, [0, 0.6], [[100,0],[100,100]]); glow(div, 20, 40, 2);
  key(ck1.opacity, [0, 0.3], [0, 100]); key(ck2.opacity, [0.2, 0.5], [0, 100]);
  key(ck1.position, [0, 4.3], [[W*0.27, H/2],[W*0.25, H/2]]); key(ck2.position, [0, 4.3], [[W*0.73, H/2],[W*0.75, H/2]]);
  finish(s5); log("S5 built");

  // ======================= S6: this is the story... (10.7 s) =======================
  var s6 = comp("S6_EinsteinDesk", 10.7);
  solid(s6, "Backdrop", [0.05,0.045,0.04]);
  var bg6 = s6.layers.add(dkbg); bg6.threeDLayer = true;
  var fg6 = s6.layers.add(dkfg); fg6.threeDLayer = true;
  var sc6 = H / dkfg.height * 100 * 1.05;
  var d6 = 650, cz6 = -1600, comp6 = (d6 - cz6) / (-cz6) * 1.1;
  fg6.position.setValue([W/2, H/2, 0]); fg6.scale.setValue([sc6, sc6, 100]);
  bg6.position.setValue([W/2, H/2, d6]); bg6.scale.setValue([sc6*comp6, sc6*comp6, 100]);
  var dust = solid(s6, "Dust", [0,0,0]);
  var dpw = fx(dust, "CC Particle World");
  try {
    dpw.property("Birth Rate").setValue(0.25);
    dpw.property("Longevity (sec)").setValue(6);
    dpw.property("Radius X").setValue(0.6);
    dpw.property("Radius Y").setValue(0.4);
    dpw.property("Radius Z").setValue(0.4);
    dpw.property("Velocity").setValue(0.03);
    dpw.property("Gravity").setValue(-0.01);
    dpw.property("Birth Size").setValue(0.012);
    dpw.property("Death Size").setValue(0.008);
    dpw.property("Birth Color").setValue([1,0.9,0.75]);
    dpw.property("Death Color").setValue([1,0.85,0.7]);
  } catch (e) { log("S6 dust partial: " + e.toString()); }
  dust.blendingMode = BlendingMode.ADD; dust.opacity.setValue(60);
  var c6 = cam(s6, "Cam");
  key(c6.position, [0, 7.5, 10.7], [[W/2 - 80, H/2 + 20, cz6], [W/2 + 120, H/2 - 30, cz6 + 380], [W/2 + 420, H/2 - 160, cz6 + 760]]); ease(c6.position);
  var wg = solid(s6, "WindowGlow", [1,0.86,0.62], 1500, 1500); wg.position.setValue([W*0.78, H*0.3]);
  ellipseMask(wg, 650); wg.blendingMode = BlendingMode.SCREEN; key(wg.opacity, [6.5, 9.5], [0, 70]);
  var white = solid(s6, "ToWhite", [1,0.97,0.92]); key(white.opacity, [9.9, 10.7], [0, 100]);
  finish(s6); log("S6 built");

  // ======================= MAIN =======================
  var main = comp("M12_Animation", 33);
  var plan = [[s1, 0.0], [s2, 3.6], [s3, 5.8], [s4, 9.3], [s5, 18.0], [s6, 22.3]];
  for (var i = plan.length - 1; i >= 0; i--) {
    var L = main.layers.add(plan[i][0]); L.startTime = plan[i][1];
    if (i > 0) key(L.opacity, [plan[i][1], plan[i][1] + 0.2], [0, 100]);
  }
  var burn = main.layers.add(aBurn); burn.audioEnabled = false; burn.blendingMode = BlendingMode.SCREEN; burn.startTime = 8.8;
  var burn2 = main.layers.add(aBurn); burn2.audioEnabled = false; burn2.blendingMode = BlendingMode.SCREEN; burn2.startTime = 16.8; burn2.opacity.setValue(70);
  log("main comp built");

  // ---------- render ----------
  var rq = proj.renderQueue.items.add(main);
  var om = rq.outputModule(1);
  var tmpl = om.templates; var pick = null;
  for (var t = 0; t < tmpl.length; t++) { if (tmpl[t] === "High Quality") pick = tmpl[t]; }
  if (pick) om.applyTemplate(pick);
  om.file = new File(M + "M12_Animation");
  log("templates: " + tmpl.join(", "));
  proj.save(new File(M + "M12_Animation.aep"));
  log("saved project; rendering...");
  flush();
  proj.renderQueue.render();
  log("render done: " + om.file.fsName);
} catch (e) {
  log("ERROR: " + e.toString() + " line " + e.line);
}
app.endUndoGroup();
flush();
})();
