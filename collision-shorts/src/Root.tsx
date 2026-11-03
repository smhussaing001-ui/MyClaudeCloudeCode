import { Composition, Folder } from "remotion";
import { Cradle, Galton, PiBlocks, RingArt, Xylo } from "./scenes";
import { Accretion, AsteroidDoubling, BodeOrbits, LaplaceRhythm, MoonBounce } from "./scenes-solar";
import { MarsWeave, MercuryRosette, SaturnWeave, VenusFromEarth, VenusWeave } from "./scenes-orbit";
import { FPS, FRAMES, H, W } from "./sims";

const SHORTS = [
  { id: "01-Cradle", component: Cradle },
  { id: "02-RingArt", component: RingArt },
  { id: "03-PiBlocks", component: PiBlocks },
  { id: "04-Galton", component: Galton },
  { id: "05-Xylophone", component: Xylo },
];

const SOLAR = [
  { id: "06-BodeOrbits", component: BodeOrbits },
  { id: "07-LaplaceRhythm", component: LaplaceRhythm },
  { id: "08-AsteroidDoubling", component: AsteroidDoubling },
  { id: "09-Accretion", component: Accretion },
  { id: "10-MoonBounce", component: MoonBounce },
];

const ORBIT = [
  { id: "11-VenusWeave", component: VenusWeave },
  { id: "12-SaturnWeave", component: SaturnWeave },
  { id: "13-MarsWeave", component: MarsWeave },
  { id: "14-VenusFromEarth", component: VenusFromEarth },
  { id: "15-MercuryRosette", component: MercuryRosette },
];

export const RemotionRoot = () => (
  <>
    <Folder name="Collisions">
      {SHORTS.map((s) => (
        <Composition key={s.id} id={s.id} component={s.component} durationInFrames={FRAMES} fps={FPS} width={W} height={H} />
      ))}
    </Folder>
    <Folder name="OrbitGeometry">
      {ORBIT.map((s) => (
        <Composition key={s.id} id={s.id} component={s.component} durationInFrames={FRAMES} fps={FPS} width={W} height={H} />
      ))}
    </Folder>
    <Folder name="SolarProgression">
      {SOLAR.map((s) => (
        <Composition key={s.id} id={s.id} component={s.component} durationInFrames={FRAMES} fps={FPS} width={W} height={H} />
      ))}
    </Folder>
  </>
);
