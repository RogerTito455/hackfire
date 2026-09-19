import type { AutopilotControl } from '../hooks/useAutopilot'
import type { FireForecast } from '../hooks/useFireForecast'
import { closedRoads } from '../domain/zones'
import type { FireReplay } from '../hooks/useFireReplay'
import type { LeadTimeView } from '../hooks/useLeadTime'
import type { LiveMode } from '../hooks/useLiveFires'
import type { MapMode } from '../hooks/useMapMode'
import type { SelectedRoute } from '../hooks/useSelectedRoute'
import type { Orders } from '../hooks/useOrders'
import type { TextTriage } from '../hooks/useTextTriage'
import type { Campaign } from '../hooks/useCampaign'
import type { Conversations, CoordinatorConversation } from '../hooks/useConversation'
import type { VoiceCapabilities } from '../domain/voice'
import type { RescueVideoControl } from '../hooks/useRescueVideo'
import type { CrewPlanView } from '../hooks/useCrewPlan'
import type { CrewRoomHost } from '../hooks/useCrewRoom'
import type { Closures } from '../hooks/useClosures'
import type { Triage } from '../hooks/useTriage'
import { AutopilotToggle } from './AutopilotToggle'
import { BottomSheet } from './BottomSheet'
import { CrewAlerts } from './CrewAlerts'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { LanguagePicker } from './LanguagePicker'
import { OrdersPanel } from './OrdersPanel'
import { TextTriagePanel } from './TextTriagePanel'
import { LeadTimeCard } from './LeadTimeCard'
import { LiveStatus } from './LiveStatus'
import { ModeToggle } from './ModeToggle'
import { ReplayControls } from './ReplayControls'
import { RescueQueue } from './RescueQueue'
import { CrewPlanPanel } from './CrewPlanPanel'
import { ClosuresPanel } from './ClosuresPanel'
import { ShareWithCrewsPanel } from './ShareWithCrewsPanel'
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
  coordinatorCall: CoordinatorConversation
  rescueVideo: RescueVideoControl
  autopilot: AutopilotControl
  crewPlan: CrewPlanView
  crewRoom: CrewRoomHost
  closures: Closures
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
  rescueVideo,
  autopilot,
  crewPlan,
  crewRoom,
  closures,
}: DashboardProps) {
  const { t } = useI18n()
  const { neighbors, rescues, alerts, counts, online, reset } = triage
  const selected = neighbors.find((neighbor) => neighbor.id === selection.neighborId) ?? null
  const watched = rescueVideo.live ? neighbors.find((neighbor) => neighbor.id === rescueVideo.live?.neighborId) : undefined
  const liveVideo =
    rescueVideo.live && watched
      ? {
          lon: watched.lon,
          lat: watched.lat,
          element: rescueVideo.live.element,
          caption: rescueVideo.live.caption,
          waiting: rescueVideo.live.state === 'waiting',
        }
      : null
  return (
    <div className="app">
      <div className="map-area">
        <TriageMap
          mode={mode}
          neighbors={neighbors}
          hotspots={replay.hotspots}
          time={replay.time}
          live={live.data}
          liveSpread={live.spread}
          selectedNeighborId={selection.neighborId}
          route={selection.route}
          routeKind={selection.mode}
          fireArea={selection.fireArea}
          onSelectNeighbor={selection.select}
          closures={closures.closures}
          closing={closures.closing}
          onMapClick={(lon, lat) => void closures.close(lon, lat)}
          spread={forecast.spread}
          zones={forecast.zonesAtRisk}
          liveVideo={liveVideo}
        />
      </div>

      <header className="topbar">
        <h1 className="brand">
          <Icon name="logo" size={26} />
          <span className="brand-name">HackFire</span>
        </h1>
        <span className={online ? 'conn ok' : 'conn down'} role="status">
          <span className="conn-dot" aria-hidden="true" />
          <span className="conn-label">{online ? t('app.connected') : t('app.offline')}</span>
        </span>
        <ModeToggle mode={mode} onChange={onModeChange} />
        <LanguagePicker />
      </header>

      <BottomSheet
        wake={selection.neighborId}
        header={
          <>
            {mode === 'replay' ? (
              <>
                <ReplayControls
                  status={replay.status}
                  range={replay.range}
                  time={replay.time}
                  observedCount={replay.observedCount}
                  playing={replay.playing}
                  onTimeChange={replay.setTime}
                  onTogglePlay={replay.togglePlay}
                />
                <AutopilotToggle
                  enabled={autopilot.enabled}
                  busy={autopilot.busy}
                  onToggle={() => autopilot.toggle(replay.time)}
                />
              </>
            ) : (
              <LiveStatus {...live} />
            )}
            <StatusCounts counts={counts} />
          </>
        }
      >
        {selected !== null && (
          <section className="group group-selected">
            <h2 className="icon-button">
              <Icon name="route" size={18} />
              {t('section.wayOut')}
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
            <h3 className="subhead icon-button">
              <Icon name="live" size={16} />
              {t('section.callResident')}
            </h3>
            <TalkPanel
              neighbor={selected}
              available={voice.web_sessions}
              order={orders.orders.find((order) => order.zone === selected.zone)}
              activeId={conversation.neighborId}
              state={conversation.state}
              onTalk={() => conversation.start(selected.id)}
              onHangUp={conversation.hangUp}
            />
            <details className="backup">
              <summary>{t('section.typedBackup')}</summary>
              <TextTriagePanel key={selected.id} neighbor={selected} triage={textTriage} />
            </details>
          </section>
        )}

        <section className="group">
          <h2 className="icon-button">
            <Icon name="lifebuoy" size={18} />
            {t('section.rescues')}
          </h2>
          <AskAgentPanel
            available={voice.coordinator}
            state={coordinatorCall.state}
            onAsk={coordinatorCall.start}
            onHangUp={coordinatorCall.hangUp}
          />
          <RescueQueue
            rescues={rescues}
            video={
              rescueVideo.capabilities.video
                ? {
                    links: rescueVideo.links,
                    requesting: rescueVideo.requesting,
                    watching: rescueVideo.live?.neighborId ?? null,
                    failed: rescueVideo.error !== null,
                    onRequest: rescueVideo.request,
                  }
                : undefined
            }
          />
        </section>

        <section className="group">
          <h2 className="icon-button">
            <Icon name="fire-truck" size={18} />
            {t('section.crewPlan')}
          </h2>
          <ShareWithCrewsPanel
            available={rescueVideo.capabilities.video}
            state={crewRoom.state}
            link={crewRoom.link}
            onShare={crewRoom.start}
            onStop={crewRoom.stop}
          />
          <CrewPlanPanel
            plan={crewPlan.plan}
            crews={crewPlan.crews}
            onCrewsChange={crewPlan.setCrews}
            onShowRoute={(neighborId) => {
              onModeChange('replay')
              selection.showRescue(neighborId)
            }}
          />
        </section>

        <section className="group">
          <h2 className="icon-button">
            <Icon name="road-closed" size={18} />
            {t('section.closures')}
          </h2>
          <ClosuresPanel
            closures={closures.closures}
            closing={closures.closing}
            saving={closures.saving}
            error={closures.error}
            onToggleClosing={() => {
              if (!closures.closing) onModeChange('replay')
              closures.setClosing(!closures.closing)
            }}
            onReopen={(closureId) => void closures.reopen(closureId)}
            nameOf={(neighborId) => neighbors.find((neighbor) => neighbor.id === neighborId)?.name ?? neighborId}
          />
        </section>

        <section className="group">
          <h2 className="icon-button">
            <Icon name="flag" size={18} />
            {t('section.orders')}
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

        {mode === 'replay' && (
          <section className="group">
            <h2 className="icon-button">
              <Icon name="flame" size={18} />
              {t('section.fire')}
            </h2>
            <LeadTimeCard view={leadTime} />
            {forecast.status === 'ready' && (
              <SpreadLegend issuedAt={forecast.issuedAt} closedRoads={closedRoads(forecast.zonesAtRisk).length} />
            )}
            <ZonesAtRisk
              status={forecast.status}
              zones={forecast.zonesAtRisk}
              hasForecast={forecast.issuedAt !== null}
            />
          </section>
        )}

        <section className="group">
          <h2 className="icon-button">
            <Icon name="bell" size={18} />
            {t('section.alerts')}
          </h2>
          <CrewAlerts
            alerts={alerts}
            onShowRoute={(neighborId) => {
              onModeChange('replay')
              selection.showRescue(neighborId)
            }}
          />
        </section>

        {selected === null && (
          <p className="hint">{t('app.tapResident')}</p>
        )}

        <button type="button" className="reset icon-button" onClick={reset}>
          <Icon name="reset" size={16} />
          {t('app.reset')}
        </button>
      </BottomSheet>
    </div>
  )
}
