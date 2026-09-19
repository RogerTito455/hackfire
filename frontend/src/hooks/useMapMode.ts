// Which story the map tells: the 23 July replay or the fires burning right now.

import { useState } from 'react'

export type MapMode = 'replay' | 'live'

export function useMapMode(): [MapMode, (mode: MapMode) => void] {
  return useState<MapMode>('replay')
}
