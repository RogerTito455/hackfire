import { Composition } from 'remotion'
import { HackFireVideo } from './HackFireVideo'
import { TOTAL } from './timeline'
import { FPS, H, W } from './theme'

export function Root() {
  return <Composition id="HackFire" component={HackFireVideo} durationInFrames={TOTAL} fps={FPS} width={W} height={H} />
}
