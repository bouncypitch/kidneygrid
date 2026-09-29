import { Composition } from "remotion";
import { Film, FilmProps, FPS, filmDuration, openerDuration } from "./Film";

const defaults: FilmProps = { voiceover: false, music: false, demoFootage: false, opener: false };

export const Root: React.FC = () => (
  <>
    <Composition id="KidneyGridFilm" component={Film} durationInFrames={filmDuration} fps={FPS} width={1920} height={1080} defaultProps={defaults} />
    <Composition id="KidneyGridOpener" component={Film} durationInFrames={openerDuration} fps={FPS} width={1920} height={1080} defaultProps={{ ...defaults, opener: true }} />
  </>
);
