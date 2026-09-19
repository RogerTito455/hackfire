// The fire crews' plan: which crew goes to which rescue, in order, and whether it arrives before the
// fire. Types and pure functions only.

export type Verdict = 'in_time' | 'tight' | 'late' | 'no_route'

/** One rescue in the plan. Minutes count from now. */
export interface CrewAssignment {
  rescue_id: string
  neighbor_id: string
  name: string
  address: string
  people: number | null
  crew: number
  depart_min: number
  drive_min: number | null
  eta_min: number | null
  minutes_to_impact: number | null
  /** Time to impact minus arrival; negative means after the fire. */
  margin_min: number | null
  verdict: Verdict
}

export interface CrewPlan {
  crews: number
  on_scene_min: number
  assignments: CrewAssignment[]
}

/** The plan as each crew reads it: its rescues in the order it does them. */
export function byCrew(plan: CrewPlan): CrewAssignment[][] {
  const crews: CrewAssignment[][] = Array.from({ length: plan.crews }, () => [])
  for (const step of plan.assignments) crews[step.crew - 1]?.push(step)
  return crews
}
