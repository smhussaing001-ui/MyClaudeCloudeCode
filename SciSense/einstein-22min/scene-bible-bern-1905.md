# Scene Bible: Young Einstein in Bern (1902–1909)

Purpose: lock one look for every Bern-era scene, then build each scene as **camera-controlled layers** with a **hand-off element** so the 3D camera can travel from one scene straight into the next.

All scenes that show Einstein are **dramatised reconstructions**. Put a small "Dramatised reconstruction" label on them in the edit.

---

## 1. Reference sheets (generate these first)

### A. Real photo anchors (public domain)
Get these from Wikimedia Commons (both published before 1931, so public domain in the US) and save them to `D:\Scci sense\refs\`:
- Einstein at his desk in the Bern patent office, **1904** (photo by Lucien Chavan).
- A studio portrait of Einstein from **1904–1905** (short dark wavy hair, moustache, high collar).

They go into Flow as **reference images**. Every Einstein image is generated *from* these so the likeness stays consistent.

### B. Character sheet: "Einstein, Bern 1905" (one Flow image, 16:9)
> Character reference sheet of a 26-year-old man in Bern in 1905, based on the attached photos: short dark wavy hair, full dark moustache, dark eyes, round face, slightly rumpled dark three-piece wool suit, high white starched collar, dark tie. Four views on one neutral grey background: front, three-quarter, profile, back. Plus close-ups of hands holding a pen and a pocket watch. Consistent soft studio light, photographic realism, early-1900s film grain, no text.

### C. Era sheet: "Bern 1905" (one or two Flow images)
> Visual reference board of Bern, Switzerland around 1905, arranged as a grid: the Kramgasse with its stone arcades and cobblestones; the Zytglogge medieval clock tower; the interior of the federal patent office with long wooden desks, ledgers, wall clock and tall windows; a modest apartment at Kramgasse 49 with an oil lamp, books and a baby's crib; an early electric tram; townspeople's clothing (bowler hats, long coats, long skirts). Muted palette of warm amber lamplight and cool blue-grey daylight, documentary photo realism, film grain, no text.

### D. Look rules (apply to every scene)
| Rule | Value |
|---|---|
| Lens | 35 mm, eye level unless noted |
| Palette | warm amber practicals + cool teal shadows (matches the Fusion grade) |
| Time of day | dusk → night → dawn across the sequence |
| Texture | early-1900s film grain, slight halation on lights |
| Composition | subject inside the middle third, **15% empty margin** on every edge for camera moves |
| Depth | always three readable layers: **foreground / Einstein / background** |

---

## 2. Scene list with camera hand-offs

Each scene enters on the previous scene's hand-off element and exits on its own. In Fusion the camera pushes *through* the hand-off, and the next scene starts from that matching element.

| # | Scene | Layers (FG / MG / BG) | Camera move | Exit hand-off → next scene |
|---|---|---|---|---|
| S1 | **Bern rooftops at dusk**, storm rolling in | chimneys & roof tiles / Zytglogge tower / stormy sky with lightning | slow push toward the tower | **Zytglogge clock face** fills frame |
| S2 | **Zytglogge clock face** macro, gears behind | clock hands / dial / turning gears | push in, slight rotate | **clock face** → match cut to office wall clock |
| S3 | **Patent office interior 1905**, Einstein at his desk | stacks of ledgers / Einstein writing / wall clock & tall windows | start on wall clock, tilt & dolly down to Einstein | his **papers** |
| S4 | **Desk top-down**: patent drawing beside his own equations | pen & inkwell / papers / desk wood | slide across the page | **window light** on the page |
| S5 | **Kramgasse 49 at night**, Einstein writing by lamp, crib in shadow | rain on window glass / Einstein / bookshelf & crib | dolly from outside, through the glass, inside | **lamp flare** |
| S6 | **Walking the Kramgasse arcades** with his friend Michele Besso | arcade pillars / two men talking / street & lamps | lateral tracking shot | **lightning flash** (white frame) |
| S7 | **Train & lightning thought experiment** (stylised, links to the existing still) | embankment grass / train / storm sky | wide crane up | **lightning** → Einstein's eyes |
| S8 | **Dawn: Einstein at the window** holding a finished manuscript, Bern below | window frame / Einstein / rooftops at dawn | slow pull back | **manuscript page** → letter/document scenes |

---

## 3. Build pipeline per scene

1. **Flow** – generate with the character + era sheets attached as references, 16:9, using the look rules above.
2. **Photoshop** (`stills/split_25d.jsx`) – split into FG / subject / BG layers, Content-Aware Fill behind each cut, export PNG layers + PSD.
3. **Fusion** – each layer on an ImagePlane3D at its own depth, one Camera3D per sequence; the camera's end position in scene N is the start position of scene N+1 (push through the hand-off element).
4. **Finish** – the same grade/glow/flicker/vignette/grain stack as the letter scene, so every scene matches.
