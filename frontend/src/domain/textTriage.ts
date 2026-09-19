// The typed backup for a call: what the classifier made of a resident's words.

import type { TriageStatus } from './triage'

export interface TextClassification {
  status: TriageStatus
  people: number | null
  mobility: string | null
  observation: string | null
}
