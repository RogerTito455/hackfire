import type { FireForecast } from '../hooks/useFireForecast'
import type { FireReplay } from '../hooks/useFireReplay'
import type { LeadTimeView } from '../hooks/useLeadTime'
import type { LiveMode } from '../hooks/useLiveFires'
import type { MapMode } from '../hooks/useMapMode'
import type { SelectedRoute } from '../hooks/useSelectedRoute'
import type { Orders } from '../hooks/useOrders'
import type { TextTriage } from '../hooks/useTextTriage'
import type { Campaign } from '../hooks/useCampaign'
import type { Conversations } from '../hooks/useConversation'
import type { VoiceCapabilities } from '../domain/voice'
import type { Triage } from '../hooks/useTriage'
import { CrewAlerts } from './CrewAlerts'
import { Icon } from './Icon'
import { OrdersPanel } from './OrdersPanel'
import { TextTriagePanel } from './TextTriagePanel'
import { LeadTimeCard } from './LeadTimeCard'
import { LiveStatus } from './LiveStatus'
import { ModeToggle } from './ModeToggle'
import { ReplayControls } from './ReplayControls'
import { RescueQueue } from './RescueQueue'
import { RoutePanel } from './RoutePanel'
import { TalkPanel } from './TalkPanel'
import { AskAgentPanel } from './AskAgentPanel'
import { SpreadLegend } from './SpreadLegend'
import { StatusCounts } from './StatusCounts'
import { TriageMap } from './TriageMap'
import { ZonesAtRisk } from './ZonesAtRisk'
import './dashboard.css'

interface DashboardProps {
  triage: Triage
  replay: FireReplay
  mode: MapMode
  onModeChange: (mode: MapMode) => void
  live: LiveMode
  selection: SelectedRoute
  forecast: FireForecast
  leadTime: LeadTimeView
  orders: Orders
  textTriage: TextTriage
  voice: VoiceCapabilities
  campaign: Campaign
  conversation: Conversations
  /** The coordinator's own conversation with the coordinator agent (#10). */
  coordinatorCall: Conversations
}

// Presentation only: everything arrives through props, nothing is fetched here.
export function Dashboard({
  triage,
  replay,
  mode,
  onModeChange,
  live,
  selection,
  forecast,
  leadTime,
  orders,
  textTriage,
  voice,
  campaign,
  conversation,
  coordinatorCall,
}: DashboardProps) {
  const { neighbors, rescues, alerts, counts, online, reset } = triage
  const selected = neighbors.find((neighbor) => neighbor.id === selection.neighborId) ?? null
  return (
    <div className="layout">
      <aside className="panel">
        <header>
          <h1 className="brand">
            <Icon name="logo" size={28} />
            HackFire
          </h1>
          <p className={online ? 'conn ok' : 'conn down'}>
            {online ? 'Backend connected' : 'Backend unreachable'}
          </p>
        </header>

        <section>
          <h2>Triage</h2>
          <StatusCounts counts={counts} />
        </section>

        {mode === 'replay' && (
          <>
            <section>
              <h2>Lead time</h2>
              <LeadTimeCard view={leadTime} />
            </section>

            <section>
              <h2 className="icon-button">
                <Icon name="flame" size={16} />
                Where the fire is heading
              </h2>
              {forecast.status === 'ready' && <SpreadLegend issuedAt={forecast.issuedAt} />}
              <ZonesAtRisk
                status={forecast.status}
                zones={forecast.zonesAtRisk}
                hasForecast={forecast.issuedAt !== null}
              />
            </section>
          </>
        )}

        <section>
          <h2 className="icon-button">
            <Icon name="flag" size={16} />
            Evacuation orders
          </h2>
          <OrdersPanel
            orders={orders.orders}
            safePoints={orders.safePoints}
            saving={orders.saving}
            onApprove={orders.approve}
            phoneCalls={voice.phone_calls}
            calling={campaign.calling}
            campaign={campaign.result}
            onCall={campaign.call}
          />
        </section>

        <section>
          <h2 className="icon-button">
            <Icon name="route" size={16} />
            Evacuation route
          </h2>
          <RoutePanel
            neighbor={selected}
            mode={selection.mode}
            route={selection.route}
            status={selection.status}
            avoids={selection.fireArea}
            onModeChange={selection.setMode}
            onClose={() => selection.select(null)}
          />
        </section>

        {selected !== null && (
          <section>
            <h2 className="icon-button">
              <Icon name="live" size={16} />
              Talk to the agent
            </h2>
            <TalkPanel
              neighbor={selected}
              available={voice.web_sessions}
              orderApproved={orders.orders.some((order) => order.zone === selected.zone && order.approved)}
              activeId={conversation.neighborId}
              state={conversation.state}
              onTalk={() => conversation.start(selected.id)}
              onHangUp={conversation.hangUp}
            />
          </section>
        )}

        {selected !== null && (
          <section>
            <h2>Typed answer (backup)</h2>
            <TextTriagePanel key={selected.id} neighbor={selected} triage={textTriage} />
          </section>
        )}

        <section>
          <h2 className="icon-button">
            <Icon name="lifebuoy" size={16} />
            Rescue queue
          </h2>
          <AskAgentPanel
            available={voice.coordinator}
            state={coordinatorCall.state}
            onAsk={() => coordinatorCall.start('coordinator')}
            onHangUp={coordinatorCall.hangUp}
          />
          <RescueQueue rescues={rescues} />
        </section>

        <section>
          <h2 className="icon-button">
            <Icon name="bell" size={16} />
            Crew alerts
          </h2>
          <CrewAlerts
            alerts={alerts}
            onShowRoute={(neighborId) => {
              onModeChange('replay')
              selection.showRescue(neighborId)
            }}
          />
        </section>

        <button type="button" className="reset icon-button" onClick={reset}>
          <Icon name="reset" size={16} />
          Reset demo
        </button>
      </aside>
      <div className="map-area">
        <TriageMap
          mode={mode}
          neighbors={neighbors}
          hotspots={replay.hotspots}
          time={replay.time}
          live={live.data}
          selectedNeighborId={selection.neighborId}
          route={selection.route}
          routeKind={selection.mode}
          fireArea={selection.fireArea}
          onSelectNeighbor={selection.select}
          spread={forecast.spread}
          zones={forecast.zonesAtRisk}
        />
        <ModeToggle mode={mode} onChange={onModeChange} />
        {mode === 'replay' ? (
          <ReplayControls
            status={replay.status}
            range={replay.range}
            time={replay.time}
            observedCount={replay.observedCount}
            playing={replay.playing}
            onTimeChange={replay.setTime}
            onTogglePlay={replay.togglePlay}
          />
        ) : (
          <LiveStatus {...live} />
        )}
      </div>
    </div>
  )
}
