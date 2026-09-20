import { useState, type ReactNode } from 'react'
import { Icon, type IconName } from './Icon'
import { useI18n } from './i18n'

// The laptop layout: a rail that names everything the dashboard can do, and one section open beside
// it at a size you can read. The map keeps the rest of the screen, so nothing ever covers the fire.
// Phones get BottomSheet instead. Pure presentation: sections arrive built from Dashboard.

export interface ConsoleSection {
  id: string
  icon: IconName
  /** The heading, and the name in the rail. */
  title: string
  /** One line in plain words: what this section is for; empty once the content says it itself. */
  blurb: string
  /** A live figure beside the name: rescues waiting, alerts sent, roads closed. */
  count?: number
  /** The figure is people waiting for a crew, so it is read in fire red. */
  urgent?: boolean
  /** A blue inset outline, as the selected resident's group has on a phone. */
  selected?: boolean
  content: ReactNode
}

interface ConsoleProps {
  sections: ConsoleSection[]
  /** Always in view above both columns: the scrubber or the live status, the strip and the note. */
  header: ReactNode
  /** The scripted call, pinned under the header so it is never scrolled away during the demo. */
  pinned?: ReactNode
  /** When this changes to a non-null value, `wakeSection` opens by itself. */
  wake: string | null
  wakeSection: string | null
  /** The reset button, at the foot of the rail. */
  footer?: ReactNode
}

export function Console({ sections, header, pinned, wake, wakeSection, footer }: ConsoleProps) {
  const { t } = useI18n()
  const [openId, setOpenId] = useState(sections[0]?.id ?? '')

  // A newly selected resident (or fire) opens its section, the way it opens the sheet on a phone.
  // State adjusted during render, not in an effect.
  const [lastWake, setLastWake] = useState(wake)
  if (wake !== lastWake) {
    setLastWake(wake)
    if (wake !== null && wakeSection !== null) setOpenId(wakeSection)
  }

  // Switching mode changes the sections: an id that is gone falls back to the first one.
  const open = sections.find((section) => section.id === openId) ?? sections[0]

  return (
    <section className="sheet console" aria-label={t('sheet.label')}>
      <div className="sheet-header">
        {header}
        {pinned}
      </div>
      <div className="sheet-body console-split">
        <nav className="rail" aria-label={t('console.rail')}>
          <ul>
            {sections.map((section) => (
              <li key={section.id}>
                <button
                  type="button"
                  className={section.id === open?.id ? 'rail-item current' : 'rail-item'}
                  aria-current={section.id === open?.id ? 'true' : undefined}
                  onClick={() => setOpenId(section.id)}
                >
                  <Icon name={section.icon} size={18} />
                  <span className="rail-name">{section.title}</span>
                  {section.count !== undefined && section.count > 0 && (
                    <span className={section.urgent ? 'rail-count urgent' : 'rail-count'}>{section.count}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
          {footer}
        </nav>
        {/* Every section stays mounted: a call or a video keeps running while another is read. */}
        <div className="stage">
          {sections.map((section) => (
            <div
              key={section.id}
              className={section.selected ? 'group group-selected' : 'group'}
              hidden={section.id !== open?.id}
            >
              <h2 className="icon-button">
                <Icon name={section.icon} size={20} />
                {section.title}
              </h2>
              {section.blurb !== '' && <p className="section-blurb">{section.blurb}</p>}
              {section.content}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
