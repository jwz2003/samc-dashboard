import { ChevronDown, Settings, Radio, Wifi, WifiOff } from 'lucide-react'
import { useStore } from '../store.js'

const TIMEFRAMES = ['1m', '5m', '1h', '1d']

export default function TopBar() {
  const subjects = useStore(s => s.subjects)
  const activeId = useStore(s => s.activeId)
  const setActive = useStore(s => s.setActive)
  const timeframe = useStore(s => s.timeframe)
  const setTimeframe = useStore(s => s.setTimeframe)
  const connState = useStore(s => s.connState)

  const active = subjects.find(s => s.id === activeId)

  return (
    <div
      className="flex items-center shrink-0"
      style={{ height: 48, background: 'var(--tv-card)', borderBottom: '1px solid var(--tv-border)', padding: '0 10px', gap: 12 }}
    >
      {/* 品牌 */}
      <div className="flex items-center" style={{ gap: 8, fontWeight: 600, fontSize: 14, letterSpacing: 0.3 }}>
        <span style={{ color: 'var(--tv-blue)' }}>◆</span>
        <span>SAMC Explorer</span>
      </div>

      {/* 标的选择器 */}
      <div
        className="flex items-center tv-hover"
        style={{ gap: 8, border: '1px solid var(--tv-border)', borderRadius: 4, padding: '4px 10px', cursor: 'pointer', height: 30, minWidth: 180 }}
        onClick={() => { /* 可展开列表，此处点击已有 Watchlist 联动 */ }}
      >
        <span style={{ color: 'var(--tv-dim)', fontSize: 11 }}>SUBJECT</span>
        <span className="mono" style={{ fontWeight: 600 }}>{active ? `${active.short} · ${active.name}` : '—'}</span>
        <span className="mono" style={{ color: (active?.chg ?? 0) >= 0 ? 'var(--tv-up)' : 'var(--tv-down)', fontWeight: 700 }}>
          {(active?.chg ?? 0) >= 0 ? '+' : ''}{(active?.chg ?? 0).toFixed(2)}%
        </span>
        <ChevronDown size={14} style={{ color: 'var(--tv-dim)' }} />
      </div>

      {/* 时间周期 */}
      <div className="flex" style={{ gap: 2, border: '1px solid var(--tv-border)', borderRadius: 4, padding: 2 }}>
        {TIMEFRAMES.map(t => (
          <button
            key={t}
            onClick={() => setTimeframe(t)}
            style={{
              padding: '3px 10px', borderRadius: 3, cursor: 'pointer', border: 'none', fontSize: 12,
              background: timeframe === t ? 'var(--tv-sel)' : 'transparent',
              color: timeframe === t ? '#fff' : 'var(--tv-dim)',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="flex-1" />

      {/* 连接状态 */}
      <div className="flex items-center" style={{ gap: 6, color: 'var(--tv-dim)', fontSize: 11 }}>
        {connState === 'live' ? (
          <>
            <Radio size={13} style={{ color: 'var(--tv-up)' }} />
            <span style={{ color: 'var(--tv-up)' }}>实时数据源</span>
          </>
        ) : connState === 'simulated' ? (
          <>
            <WifiOff size={13} style={{ color: 'var(--tv-warn)' }} />
            <span style={{ color: 'var(--tv-warn)' }}>模拟数据</span>
          </>
        ) : (
          <>
            <Wifi size={13} style={{ color: 'var(--tv-gold)' }} />
            <span style={{ color: 'var(--tv-gold)' }}>连接中…</span>
          </>
        )}
      </div>

      {/* 设置 */}
      <button className="tv-hover" style={{ padding: 6, borderRadius: 4, cursor: 'pointer', border: 'none', background: 'transparent', color: 'var(--tv-dim)', display: 'flex' }}>
        <Settings size={16} />
      </button>
    </div>
  )
}
