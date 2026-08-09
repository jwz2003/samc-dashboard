import { useEffect, useRef, useState } from 'react'
import { Terminal, ChevronUp, ChevronDown, Grid3X3, ShieldAlert, Zap } from 'lucide-react'
import { useStore } from '../store.js'

const TABS = [
  { key: 'logs', label: '实时审计日志', icon: Terminal },
  { key: 'attrs', label: '属性编辑', icon: Grid3X3 },
  { key: 'risk', label: '风险分析', icon: ShieldAlert },
]

/* ===== 底部控制台（可调高度 / 可折叠）===== */
export default function BottomPanel() {
  const [tab, setTab] = useState('logs')
  const bottomOpen = useStore(s => s.bottomOpen)
  const toggleBottom = useStore(s => s.toggleBottom)
  const bottomHeight = useStore(s => s.bottomHeight)
  const setBottomHeight = useStore(s => s.setBottomHeight)
  const dragRef = useRef(null)

  // 拖拽调整高度
  useEffect(() => {
    const el = dragRef.current
    if (!el) return
    const onMove = e => {
      const h = window.innerHeight - e.clientY - 48 // 减去 TopBar
      if (h > 120 && h < window.innerHeight * 0.6) setBottomHeight(h)
    }
    const onUp = () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
    el.addEventListener('mousedown', e => {
      e.preventDefault()
      document.addEventListener('mousemove', onMove)
      document.addEventListener('mouseup', onUp)
    })
    return () => { el.removeEventListener('mousedown', onMove) }
  }, [setBottomHeight])

  if (!bottomOpen) {
    return (
      <button onClick={toggleBottom} className="tv-hover" style={{ height: 26, border: 'none', borderTop: '1px solid var(--tv-border)', background: 'var(--tv-card)', color: 'var(--tv-dim)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, fontSize: 11 }}>
        <ChevronUp size={13} /> 打开控制台
      </button>
    )
  }

  return (
    <div className="shrink-0 flex flex-col" style={{ height: bottomHeight, background: 'var(--tv-card)', borderTop: '1px solid var(--tv-border)' }}>
      {/* 拖拽条 */}
      <div ref={dragRef} className="resize-handle" style={{ height: 3, background: 'transparent', flexShrink: 0, cursor: 'ns-resize' }} />

      {/* Tab 栏 */}
      <div className="flex items-center shrink-0" style={{ height: 34, padding: '0 8px', gap: 2, borderBottom: '1px solid var(--tv-border)' }}>
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className="tv-hover"
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px', borderRadius: 4, cursor: 'pointer', border: 'none', fontSize: 12,
              background: tab === key ? 'var(--tv-sel)' : 'transparent',
              color: tab === key ? '#fff' : 'var(--tv-dim)',
            }}
          >
            <Icon size={13} /> {label}
          </button>
        ))}
        <div className="flex-1" />
        <button onClick={toggleBottom} className="tv-hover" style={{ padding: 4, borderRadius: 4, cursor: 'pointer', border: 'none', background: 'transparent', color: 'var(--tv-dim)', display: 'flex' }}>
          <ChevronDown size={14} />
        </button>
      </div>

      {/* Tab 内容 */}
      <div className="flex-1" style={{ minHeight: 0, overflow: 'hidden' }}>
        {tab === 'logs' && <AuditLogs />}
        {tab === 'attrs' && <AttrGrid />}
        {tab === 'risk' && <RiskTab />}
      </div>
    </div>
  )
}

/* ---- 实时审计日志：级别着色 + 模拟流 ---- */
function AuditLogs() {
  const logs = useStore(s => s.logs)
  const pushLog = useStore(s => s.pushLog)
  const listRef = useRef(null)

  // 模拟实时审计事件流
  useEffect(() => {
    const events = [
      ['INFO', 'Tick 数据包接收（模拟流）'],
      ['INFO', 'Crosshair 联动刷新'],
      ['WARN', '波动率监测：RSI 接近阈值'],
      ['INFO', '属性变更轨迹同步'],
      ['ERROR', '心跳超时，重连数据源…'],
      ['INFO', '重连成功，数据对齐完成'],
    ]
    let i = 0
    const id = setInterval(() => {
      const [lv, msg] = events[i % events.length]
      pushLog(lv, msg + ' [sim]')
      i++
    }, 5000)
    return () => clearInterval(id)
  }, [pushLog])

  // 自动滚动到底部（最新在底部 = 终端流式风格）
  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  }, [logs])

  return (
    <div ref={listRef} className="mono" style={{ height: '100%', overflowY: 'auto', padding: '8px 12px', fontSize: 11, lineHeight: 1.7, background: '#101418' }}>
      {logs.map(l => (
        <div key={l.id} style={{ display: 'flex', gap: 8 }}>
          <span style={{ color: 'var(--tv-faint)' }}>{l.ts}</span>
          <span className={`log-${l.level}`} style={{ width: 44, fontWeight: 700, flexShrink: 0 }}>{l.level}</span>
          <span style={{ color: 'var(--tv-text)' }}>
            {l.subject && <span style={{ color: 'var(--tv-blue)' }}>[{l.subject}] </span>}
            {l.msg}
          </span>
        </div>
      ))}
    </div>
  )
}

/* ---- 属性编辑：Subject Attribute Management Contract 状态表 ---- */
function AttrGrid() {
  const activeId = useStore(s => s.activeId)
  const activeDetail = useStore(s => s.activeDetail)
  const quotes = useStore(s => s.quotes)
  const q = activeDetail ?? (activeId ? quotes[activeId] : null)

  const rows = q ? [
    ['price', '现价', q.price, q.price >= q.ma50 ? 'OK' : 'WARN'],
    ['chg', '当日涨跌', q.chg?.toFixed?.(2) + '%', Math.abs(q.chg ?? 0) > 5 ? 'CRIT' : 'OK'],
    ['rsi14', 'RSI 14', q.rsi14?.toFixed?.(1), (q.rsi14 ?? 50) < 30 || (q.rsi14 ?? 50) > 70 ? 'CRIT' : 'OK'],
    ['ma20', 'MA20', q.ma20, q.price >= q.ma20 ? 'OK' : 'WARN'],
    ['ma50', 'MA50', q.ma50, q.price >= q.ma50 ? 'OK' : 'WARN'],
    ['vol', '成交量', q.vol, 'OK'],
    ['ytd', '年初至今', q.ytd?.toFixed?.(2) + '%', 'OK'],
    ['hi52', '52周最高', q.hi52, 'OK'],
    ['lo52', '52周最低', q.lo52, 'OK'],
  ] : []

  const stateColor = s => s === 'OK' ? 'var(--tv-up)' : s === 'WARN' ? 'var(--tv-warn)' : 'var(--tv-down)'

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: 8 }}>
      <div style={{ color: 'var(--tv-dim)', fontSize: 10, marginBottom: 6 }}>
        Subject Attribute Management Contract · {q ? `${activeDetail?.short ?? activeId}（${q.name ?? ''}）` : '未选择 Subject'}
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
        <thead>
          <tr style={{ color: 'var(--tv-dim)', textAlign: 'left' }}>
            {['字段', '说明', '当前值', '契约状态', '校验规则'].map(h => (
              <th key={h} style={{ padding: '5px 10px', borderBottom: '1px solid var(--tv-border)', fontWeight: 600, fontSize: 10, letterSpacing: 0.4 }}>{h.toUpperCase()}</th>
            ))}
          </tr>
        </thead>
        <tbody className="mono">
          {rows.map(([k, label, v, st]) => (
            <tr key={k} style={{ borderBottom: '1px solid rgba(42,46,57,0.5)' }}>
              <td style={{ padding: '5px 10px', color: 'var(--tv-blue)' }}>{k}</td>
              <td style={{ padding: '5px 10px', color: 'var(--tv-dim)' }}>{label}</td>
              <td style={{ padding: '5px 10px', color: 'var(--tv-text)' }}>{typeof v === 'number' ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : v}</td>
              <td style={{ padding: '5px 10px' }}>
                <span style={{ color: stateColor(st), fontWeight: 700, fontSize: 10 }}>{st}</span>
              </td>
              <td style={{ padding: '5px 10px', color: 'var(--tv-faint)', fontSize: 10 }}>{k === 'rsi14' ? 'RSI<30 或 >70' : k === 'chg' ? '|chg|>5%' : k === 'price' ? 'price vs MA50' : '—'}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td colSpan={5} style={{ padding: 12, color: 'var(--tv-faint)' }}>从右侧 Watchlist 选择一个 Subject 查看合约状态</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

/* ---- 风险分析：分布统计 + 高风险 TOP5 ---- */
function RiskTab() {
  const subjects = useStore(s => s.subjects)
  const setActive = useStore(s => s.setActive)
  const setView = useStore(s => s.setView)

  const active = subjects.filter(s => s.status === 'Active').length
  const suspended = subjects.length - active
  const top = [...subjects].sort((a, b) => b.risk - a.risk).slice(0, 5)

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: '10px 14px' }}>
      <div className="flex" style={{ gap: 24, marginBottom: 12 }}>
        <div>
          <div style={{ color: 'var(--tv-dim)', fontSize: 10 }}>ACTIVE</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--tv-up)' }}>{active}</div>
        </div>
        <div>
          <div style={{ color: 'var(--tv-dim)', fontSize: 10 }}>SUSPENDED</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--tv-down)' }}>{suspended}</div>
        </div>
        <div>
          <div style={{ color: 'var(--tv-dim)', fontSize: 10 }}>风险指数 ≥70%</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--tv-warn)' }}>{subjects.filter(s => s.risk >= 70).length}</div>
        </div>
      </div>

      <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6, color: 'var(--tv-text)' }}>高风险 Subject TOP 5</div>
      {top.map((s, i) => (
        <div key={s.id} className="flex tv-hover" style={{ alignItems: 'center', gap: 10, padding: '6px 8px', borderRadius: 4, cursor: 'pointer' }}
          onClick={() => { setActive(s.id); setView('detail') }}>
          <span className="mono" style={{ color: 'var(--tv-faint)', width: 18 }}>{i + 1}</span>
          <span className="mono" style={{ fontWeight: 700, width: 110 }}>{s.short}</span>
          <span style={{ flex: 1, color: 'var(--tv-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.name}</span>
          <div style={{ width: 140, height: 6, borderRadius: 3, background: '#2a2e39', overflow: 'hidden' }}>
            <div style={{ width: `${s.risk}%`, height: '100%', background: s.risk >= 70 ? 'var(--tv-down)' : s.risk >= 40 ? 'var(--tv-warn)' : 'var(--tv-up)' }} />
          </div>
          <span className="mono" style={{ color: 'var(--tv-dim)', width: 40, textAlign: 'right' }}>{s.risk}%</span>
        </div>
      ))}

      <button
        onClick={() => { const h = subjects.find(s => s.risk >= 70) ?? subjects[0]; if (h) { setActive(h.id); setView('detail') } }}
        style={{ marginTop: 10, padding: '5px 14px', borderRadius: 4, cursor: 'pointer', border: '1px solid var(--tv-border)', background: 'var(--tv-bg)', color: 'var(--tv-blue)', fontWeight: 600, fontSize: 11, display: 'inline-flex', alignItems: 'center', gap: 6 }}
      >
        <Zap size={12} /> 详细分析（跳转最高风险 Subject）
      </button>
    </div>
  )
}
