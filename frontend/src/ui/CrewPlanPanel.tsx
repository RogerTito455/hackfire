import { byCrew, type CrewAssignment, type CrewPlan, type Verdict } from '../domain/crewPlan'
import { useI18n } from './i18n'
import { formatMinutes } from './theme'

interface CrewPlanPanelProps {
  plan: CrewPlan | null
  crews: number
  onCrewsChange: (crews: number) => void
  /** Open the crew's route to this resident on the map. */
  onShowRoute: (neighborId: string) => void
}

const VERDICT_CLASS: Record<Verdict, string> = {
  in_time: 'verdict in-time',
  tight: 'verdict tight',
  late: 'verdict late',
  no_route: 'verdict no-route',
}

// Which crew goes where, in what order, and who they reach before the fire.
export function CrewPlanPanel({ plan, crews, onCrewsChange, onShowRoute }: CrewPlanPanelProps) {
  const { t } = useI18n()

  // Recommended by Norma — fixed with Claude Opus 5 via Claude Code
  // The verdict line for one stop, as four cases read in order: no route at all, no forecast to
  // compare against, in time by that margin, or late by it. It was one four-deep ternary.
  const verdictText = (step: CrewAssignment) => {
    if (step.verdict === 'no_route') return t('crewPlan.noRoute')
    if (step.margin_min === null) return t('crewPlan.noForecast')
    if (step.margin_min >= 0) return t(`crewPlan.${step.verdict}`, { time: formatMinutes(step.margin_min) })
    return t('crewPlan.late', { time: formatMinutes(-step.margin_min) })
  }

  return (
    <div className="crew-plan">
      <label className="crew-count">
        {t('crewPlan.crews')}
        <button type="button" onClick={() => onCrewsChange(crews - 1)} disabled={crews <= 1} aria-label={t('crewPlan.fewer')}>
          −
        </button>
        <strong>{crews}</strong>
        <button type="button" onClick={() => onCrewsChange(crews + 1)} aria-label={t('crewPlan.more')}>
          +
        </button>
      </label>
      {!plan || plan.assignments.length === 0 ? (
        <p className="empty">{t('crewPlan.empty')}</p>
      ) : (
        byCrew(plan).map((steps, index) => (
          <div key={index} className="crew">
            <h3>{t('crewPlan.crew', { number: index + 1 })}</h3>
            {steps.length === 0 ? (
              <p className="empty">{t('crewPlan.standBy')}</p>
            ) : (
              <ol>
                {steps.map((step) => (
                  <li key={step.rescue_id}>
                    <button type="button" className="crew-step" onClick={() => onShowRoute(step.neighbor_id)}>
                      <strong>{step.name}</strong>
                      <span>
                        {step.depart_min === 0
                          ? t('crewPlan.leavesNow')
                          : t('crewPlan.leavesIn', { time: formatMinutes(step.depart_min) })}
                        {step.eta_min !== null && ` · ${t('crewPlan.arrivesIn', { time: formatMinutes(step.eta_min) })}`}
                      </span>
                      <span className={VERDICT_CLASS[step.verdict]}>{verdictText(step)}</span>
                    </button>
                  </li>
                ))}
              </ol>
            )}
          </div>
        ))
      )}
    </div>
  )
}
