import type { CSSProperties } from 'react'
import type { AutopilotControl } from '../hooks/useAutopilot'
import type { ScriptedCallView } from '../hooks/useScriptedCall'
import type { FireForecast } from '../hooks/useFireForecast'
import { closedRoads } from '../domain/zones'
import type { FireReplay } from '../hooks/useFireReplay'
import type { LeadTimeView } from '../hooks/useLeadTime'
import type { Bounds } from '../domain/scenario'
import type { LiveMode } from '../hooks/useLiveFires'
import type { LiveOperationsView } from '../hooks/useLiveOperations'
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
import type { ActivityLog as ActivityLogView, ServiceStatus as ServiceStatusView } from '../hooks/useOperationsLog'
import { ActivityLog } from './ActivityLog'
import { AutopilotToggle } from './AutopilotToggle'
import { BottomSheet } from './BottomSheet'
import { Console, type ConsoleSection } from './Console'
import { ConsoleDivider } from './ConsoleDivider'
import { CrewAlerts } from './CrewAlerts'
import { DataNote } from './DataNote'
import { Icon } from './Icon'
import { useI18n } from './i18n'
import { LanguagePicker } from './LanguagePicker'
import { OrdersPanel } from './OrdersPanel'
import { TextTriagePanel } from './TextTriagePanel'
import { LeadTimeCard } from './LeadTimeCard'
import { LiveOperationsPanel } from './LiveOperationsPanel'
import { LiveStatus } from './LiveStatus'
import { MapLegend } from './MapLegend'
import { ModeToggle } from './ModeToggle'
import { ReplayControls } from './ReplayControls'
import { RescueQueue } from './RescueQueue'
import { ResidentPicker } from './ResidentPicker'
import { CrewPlanPanel } from './CrewPlanPanel'
import { ClosuresPanel } from './ClosuresPanel'
import { ShareWithCrewsPanel } from './ShareWithCrewsPanel'
import { RoutePanel } from './RoutePanel'
import { ScriptedCallCard } from './ScriptedCallCard'
import { ServiceStatus } from './ServiceStatus'
import { TalkPanel } from './TalkPanel'
import { AskAgentPanel } from './AskAgentPanel'
import { SpreadLegend } from './SpreadLegend'
import { StartDemo } from './StartDemo'
import { StatusCounts } from './StatusCounts'
import { TriageMap } from './TriageMap'
import { consoleState, useConsoleLayout } from './useConsoleLayout'
import { useWideScreen } from './useWideScreen'
import { ZonesAtRisk } from './ZonesAtRisk'
import './dashboard.css'

interface DashboardProps {
  triage: Triage
  replay: FireReplay
  /** The active scenario's box, which the replay map fits; null until it has loaded. */
  replayBounds: Bounds | null
  mode: MapMode
  onModeChange: (mode: MapMode) => void
  live: LiveMode
  /** Live mode: the selected real fire's places at risk, alert drafts and roads to close. */
  liveOperations: LiveOperationsView
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
  scriptedCall: ScriptedCallView
  crewPlan: CrewPlanView
  crewRoom: CrewRoomHost
  closures: Closures
  /** The audit log's latest events and the service status (docs/setup/operations.md). */
  activity: ActivityLogView
  services: ServiceStatusView
}

// Presentation only: everything arrives through props, nothing is fetched here.
//
// The sections are built once and laid out twice: stacked inside the bottom sheet on a phone, and
// beside the rail in the console on a laptop. Each one declares which mode it belongs to, so live
// mode shows live data alone: the rescues, orders, crew plan and closures all read the demo
// registry, and showing them next to real fires said things that were not true.
export function Dashboard({
  triage,
  replay,
  replayBounds,
  mode,
  onModeChange,
  live,
  liveOperations,
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
  scriptedCall,
  crewPlan,
  crewRoom,
  closures,
  activity,
  services,
}: DashboardProps) {
  const { t } = useI18n()
  const wide = useWideScreen()
  // How much of a laptop screen the console takes, and whether the coordinator asked for the map
  // alone. Below 900 px none of it applies: the phone keeps the bottom sheet at full width.
  const layout = useConsoleLayout()
  const sidebar = wide && !layout.hidden ? layout.width : 0
  // Only a width someone chose is written here; otherwise the stylesheet's own breakpoints decide.
  const appStyle = wide && !layout.hidden && layout.chosen ? ({ '--sidebar': `${sidebar}px` } as CSSProperties) : undefined
  // A legend three hundred pixels wide over a narrow map is a legend covering the map.
  const mapRoom = !wide || layout.viewport - sidebar >= 620
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

  // One press starts the run-through: the first resident in the registry is the one who is called,
  // and their zone's order is approved on the way if the coordinator has not done it yet.
  const first = neighbors[0] ?? null
  const firstOrder = first === null ? undefined : orders.orders.find((order) => order.zone === first.zone)
  const startDemo = async () => {
    if (first === null) return
    if (firstOrder && !firstOrder.approved) {
      await orders.approve(first.zone, {
        action: firstOrder.proposed_action,
        destination_id: firstOrder.proposed_destination_id,
      })
    }
    await campaign.callOne(first.id)
  }

  // The replay's scrubber or the live status, then what the numbers below are: always in view.
  const header =
    mode === 'replay' ? (
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
        <StatusCounts counts={counts} />
        {voice.phone_calls && (
          <StartDemo
            name={first?.name ?? null}
            needsApproval={firstOrder ? !firstOrder.approved : false}
            busy={campaign.ringing !== null || orders.saving !== null}
            blockedBySimulation={autopilot.enabled}
            onStart={() => void startDemo()}
          />
        )}
        <DataNote mode={mode} />
      </>
    ) : (
      <>
        <LiveStatus {...live} />
        <DataNote mode={mode} />
      </>
    )

  const call =
    mode === 'replay' && scriptedCall.call && scriptedCall.transcript ? (
      <ScriptedCallCard
        call={scriptedCall.call}
        transcript={scriptedCall.transcript}
        residentName={neighbors.find((neighbor) => neighbor.id === scriptedCall.call?.neighbor_id)?.name ?? null}
        shown={scriptedCall.shown}
        typing={scriptedCall.typing}
      />
    ) : null

  const replaySections: ConsoleSection[] = [
    {
      id: 'wayOut',
      icon: 'route',
      title: t('section.wayOut'),
      // Once a resident is open the panel names them and says what their route avoids: a line
      // telling you to tap one would be describing what you have already done.
      blurb: selected === null ? t('section.blurb.wayOut') : '',
      selected: selected !== null,
      content:
        selected === null ? (
          <ResidentPicker neighbors={neighbors} onSelect={selection.select} />
        ) : (
          <>
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
              muted={conversation.muted}
              onMutedChange={conversation.setMuted}
              onTalk={() => conversation.start(selected.id)}
              onHangUp={conversation.hangUp}
              phoneCalls={voice.phone_calls}
              ringing={campaign.ringing === selected.id}
              rang={campaign.rang?.neighborId === selected.id ? campaign.rang.placed : null}
              onPhone={() => void campaign.callOne(selected.id)}
            />
            <details className="backup">
              <summary>{t('section.typedBackup')}</summary>
              <TextTriagePanel key={selected.id} neighbor={selected} triage={textTriage} />
            </details>
          </>
        ),
    },
    {
      id: 'rescues',
      icon: 'lifebuoy',
      title: t('section.rescues'),
      blurb: t('section.blurb.rescues'),
      count: rescues.length,
      urgent: rescues.length > 0,
      content: (
        <>
          <AskAgentPanel
            available={voice.coordinator}
            state={coordinatorCall.state}
            muted={coordinatorCall.muted}
            onMutedChange={coordinatorCall.setMuted}
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
        </>
      ),
    },
    {
      id: 'crewPlan',
      icon: 'fire-truck',
      title: t('section.crewPlan'),
      blurb: t('section.blurb.crewPlan'),
      count: crewPlan.plan?.assignments.length,
      content: (
        <>
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
        </>
      ),
    },
    {
      id: 'closures',
      icon: 'road-closed',
      title: t('section.closures'),
      blurb: t('section.blurb.closures'),
      count: closures.closures.length,
      content: (
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
      ),
    },
    {
      id: 'orders',
      icon: 'flag',
      title: t('section.orders'),
      blurb: t('section.blurb.orders'),
      count: orders.orders.length,
      content: (
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
      ),
    },
    {
      id: 'fire',
      icon: 'flame',
      title: t('section.fire'),
      blurb: t('section.blurb.fire'),
      count: forecast.zonesAtRisk.length,
      content: (
        <>
          <LeadTimeCard view={leadTime} />
          {forecast.status === 'ready' && (
            <SpreadLegend issuedAt={forecast.issuedAt} closedRoads={closedRoads(forecast.zonesAtRisk).length} />
          )}
          <ZonesAtRisk status={forecast.status} zones={forecast.zonesAtRisk} hasForecast={forecast.issuedAt !== null} />
        </>
      ),
    },
    {
      id: 'alerts',
      icon: 'bell',
      title: t('section.alerts'),
      blurb: t('section.blurb.alerts'),
      count: alerts.length,
      content: (
        <CrewAlerts
          alerts={alerts}
          onShowRoute={(neighborId) => {
            onModeChange('replay')
            selection.showRescue(neighborId)
          }}
        />
      ),
    },
  ]

  const liveSections: ConsoleSection[] = [
    {
      id: 'liveOps',
      icon: 'flame',
      title: t('liveOps.section'),
      blurb: t('section.blurb.liveOps'),
      count: liveOperations.data?.places.length,
      content: (
        <LiveOperationsPanel
          fires={live.spread?.fires ?? []}
          view={liveOperations}
          onSelect={liveOperations.select}
          onRetry={liveOperations.retry}
        />
      ),
    },
  ]

  // Operations: the same in both modes, because both are audited.
  const operationsSections: ConsoleSection[] = [
    {
      id: 'activity',
      icon: 'replay',
      title: t('section.activity'),
      blurb: t('section.blurb.activity'),
      content: (
        <ActivityLog
          events={activity.events}
          loaded={activity.loaded}
          failed={activity.failed}
          downloadUrl={activity.downloadUrl}
        />
      ),
    },
    {
      id: 'services',
      icon: 'satellite',
      title: t('section.services'),
      blurb: t('section.blurb.services'),
      content: <ServiceStatus providers={services.providers} loaded={services.loaded} failed={services.failed} />,
    },
  ]

  const sections = [...(mode === 'replay' ? replaySections : liveSections), ...operationsSections]

  // The reset belongs to the demo: in live mode there is nothing of ours to put back.
  const resetButton =
    mode === 'replay' ? (
      <button type="button" className="reset icon-button" onClick={reset}>
        <Icon name="reset" size={16} />
        {t('app.reset')}
      </button>
    ) : null

  const wake = selection.neighborId ?? liveOperations.fireId

  return (
    <div className="app" data-console={consoleState(layout, wide)} style={appStyle}>
      <div className="map-area">
        <TriageMap
          mode={mode}
          replayBounds={replayBounds}
          neighbors={neighbors}
          hotspots={replay.hotspots}
          time={replay.time}
          live={live.data}
          liveSpread={live.spread}
          dgt={live.dgt}
          liveOperations={liveOperations.data}
          onSelectLiveFire={liveOperations.select}
          closureFocus={liveOperations.focus}
          onFocusClosure={liveOperations.focusClosure}
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
          resizeKey={sidebar}
        />
        <MapLegend mode={mode} room={mapRoom} />
        {wide && (
          <button type="button" className="map-only" onClick={layout.toggleHidden}>
            {layout.hidden ? t('console.showPanel') : t('console.mapOnly')}
          </button>
        )}
      </div>

      <header className="topbar">
        <h1 className="brand">
          <a className="brand-link" href="/about" aria-label={t('app.about')}>
            <Icon name="logo" size={26} />
            <span className="brand-name">HackFire</span>
          </a>
        </h1>
        <span className={online ? 'conn ok' : 'conn down'} role="status">
          <span className="conn-dot" aria-hidden="true" />
          <span className="conn-label">{online ? t('app.connected') : t('app.offline')}</span>
        </span>
        <ModeToggle mode={mode} onChange={onModeChange} />
        <LanguagePicker />
      </header>

      {wide && !layout.hidden && (
        <ConsoleDivider width={layout.width} min={layout.min} max={layout.max} onWidthChange={layout.setWidth} />
      )}

      {wide ? (
        <Console
          sections={sections}
          header={header}
          pinned={call}
          wake={wake}
          wakeSection={selection.neighborId !== null ? 'wayOut' : 'liveOps'}
          footer={resetButton}
        />
      ) : (
        <BottomSheet wake={wake} header={header}>
          {call}
          {sections.map((section) => (
            <section key={section.id} className={section.selected ? 'group group-selected' : 'group'}>
              <h2 className="icon-button">
                <Icon name={section.icon} size={18} />
                {section.title}
              </h2>
              {section.blurb !== '' && <p className="section-blurb">{section.blurb}</p>}
              {section.content}
            </section>
          ))}
          {resetButton}
        </BottomSheet>
      )}
    </div>
  )
}
