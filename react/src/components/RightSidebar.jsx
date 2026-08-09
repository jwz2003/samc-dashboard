import { ChevronRight, ChevronLeft, Activity, ScanSearch } from 'lucide-react'
import { useStore } from '../store.js'

/* ===== 右侧面板 300px（可折叠）=====
 * Watchlist：Subject 节点列表（ID / 状态彩色标签 / 风险指数进度条）
 * 详情预览：当前选中 Subject 的指标摘要
 */
export default function RightSidebar() {
  const subjects = useStore(s => s.subjects)
  const activeId = useStore(s => s.activeId)
  const setActive = useStore(s => s.setActive)
  const setView = useStore(s => s.setView)
  const rightOpen = useStore(s => s.rightOpen)
  const toggleRight = useStore(s => s.toggleRight)
  const quotes = useStore(s => s.quotes)

  const active = subjects.find(s => s.id === activeId)
  const q = active ? quotes[active.id] : null

  return (
    <>
      {/* 折叠状态下的窄条触发区 */}
      {!rightOpen && (
        <button onClick={toggleRight} className="tv-hover" style={{ width: 22, border: 'none', borderLeft: '1px solid var(--tv-border)', background: 'var(--tv-card)', color: 'var(--tv-dim)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <ChevronLeft size={14} />
        </button>
      )}

      <div className="collapse-anim flex flex-col shrink-0" style={{ width: rightOpen ? 300 : 0, overflow: 'hidden', background: 'var(--tv-card)', borderLeft: '1px solid var(--tv-border)' }}>
        {/* 头部 */}
        <div className="flex items-center shrink-0" style={{ height: 40, padding: '0 10px', borderBottom: '1px solid var(--tv-border)', gap: 8 }}>
          <Activity size={14} style={{ color: 'var(--tv-blue)' }} />
          <span style={{ fontWeight: 700, fontSize: 12 }}>Watchlist</span>
          <span style={{ color: 'var(--tv-faint)', fontSize: 10 }}>{subjects.length} nodes</span>
          <div className="flex-1" />
          <button onClick={toggleRight} className="tv-hover" style={{ padding: 4, borderRadius: 4, cursor: 'pointer', border: 'none', background: 'transparent', color: 'var(--tv-dim)', display: 'flex' }}>
            <ChevronRight size={14} />
          </button>
        </div>

        {/* 节点列表 */}
        <div style={{ overflowY: 'auto', flex: 1, padding: 6 }}>
          {subjects.map(s => {
            const selected = s.id === activeId
            return (
              <div
                key={s.id}
                onClick={() => { setActive(s.id); setView('detail') }}
                className="tv-hover"
                style={{
                  padding: '8px 10px', marginBottom: 4, borderRadius: 4, cursor: 'pointer',
                  border: selected ? '1px solid rgba(41,98,255,0.6)' : '1px solid transparent',
                  background: selected ? 'var(--tv-sel)' : 'transparent',
                }}
              >
                <div className="flex" style={{ alignItems: 'center', gap: 6, marginBottom: 5 }}>
                  <span className="mono" style={{ fontWeight: 700, fontSize: 12 }}>{s.short}</span>
                  <span style={{ color: 'var(--tv-dim)', fontSize: 10, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.name}</span>
                  <span style={{
                    fontSize: 9, padding: '1px 6px', borderRadius: 3, fontWeight: 700, letterSpacing: 0.4,
                    background: s.status === 'Active' ? 'rgba(8,153,129,0.18)' : 'rgba(242,54,69,0.18)',
                    color: s.status === 'Active' ? 'var(--tv-up)' : 'var(--tv-down)',
                  }}>
                    {s.status.toUpperCase()}
                  </span>
                </div>
                <div className="flex" style={{ alignItems: 'center', gap: 8 }}>
                  <span className="mono" style={{ fontSize: 11, color: (s.chg ?? 0) >= 0 ? 'var(--tv-up)' : 'var(--tv-down)', width: 58 }}>
                    {(s.chg ?? 0) >= 0 ? '+' : ''}{(s.chg ?? 0).toFixed(2)}%
                  </span>
                  {/* 风险指数进度条 */}
                  <div style={{ flex: 1, height: 5, borderRadius: 3, background: '#2a2e39', overflow: 'hidden' }}>
                    <div style={{
                      width: `${s.risk}%`, height: '100%', borderRadius: 3,
                      background: s.risk >= 70 ? 'var(--tv-down)' : s.risk >= 40 ? 'var(--tv-warn)' : 'var(--tv-up)',
                      transition: 'width 0.3s ease',
                    }} />
                  </div>
                  <span className="mono" style={{ fontSize: 10, color: 'var(--tv-dim)', width: 34, textAlign: 'right' }}>{s.risk}%</span>
                </div>
              </div>
            )
          })}
        </div>

        {/* 详情预览 */}
        <div className="shrink-0" style={{ borderTop: '1px solid var(--tv-border)', padding: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--tv-dim)', fontSize: 10, marginBottom: 8, letterSpacing: 0.5 }}>
            <ScanSearch size={11} /> 详情预览 {active ? `· ${active.short}` : ''}
          </div>
          {active && q ? (
            <div style={{ fontSize: 11 }}>
              {[['现价', `${q.price.toLocaleString()} ${q.cur}`], ['RSI14', q.rsi14?.toFixed?.(1)], ['MA20', q.ma20?.toLocaleString?.()], ['MA50', q.ma50?.toLocaleString?.()], ['52周区间', `${q.lo52?.toLocaleString?.()} ~ ${q.hi52?.toLocaleString?.()}`]].map(([k, v]) => (
                <div key={k} className="flex" style={{ justifyContent: 'space-between', padding: '2.5px 0' }}>
                  <span style={{ color: 'var(--tv-dim)' }}>{k}</span>
                  <span className="mono" style={{ color: 'var(--tv-text)' }}>{v ?? '—'}</span>
                </div>
              ))}
              <button
                onClick={() => setView('detail')}
                style={{ width: '100%', marginTop: 8, padding: '5px 0', borderRadius: 4, cursor: 'pointer', border: '1px solid var(--tv-border)', background: 'var(--tv-bg)', color: 'var(--tv-blue)', fontWeight: 600, fontSize: 11 }}
              >
                详细分析 →
              </button>
            </div>
          ) : (
            <div style={{ color: 'var(--tv-faint)', fontSize: 11 }}>点击上方节点查看详情</div>
          )}
        </div>
      </div>
    </>
  )
}
