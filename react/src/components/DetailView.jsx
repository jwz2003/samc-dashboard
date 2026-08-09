import { useEffect, useRef, useState } from 'react'
import { createChart, LineSeries, ColorType } from 'lightweight-charts'
import { ArrowLeft, User, CalendarClock, Hash, AlertTriangle } from 'lucide-react'
import { useStore } from '../store.js'
import { useSAMCData, tradingDays } from '../hooks/useSAMCData.js'

/* ===== 深度详情页（细分选项）=====
 * 左：Subject 元数据（Owner / Expiration / Metadata Hash）
 * 中：属性历史变更轨迹（closes + MA20 + MA50 多线图）
 * 右：关联风险节点拓扑图（Canvas）
 */

// [推断] djb2 哈希：由行情 JSON 生成稳定指纹
function djb2(str) {
  let h = 5381
  for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) >>> 0
  return h.toString(16).toUpperCase().padStart(8, '0')
}

function sma(closes, n) {
  const out = []
  for (let i = 0; i < closes.length; i++) {
    if (i < n - 1) { out.push(null); continue }
    const win = closes.slice(i - n + 1, i + 1)
    out.push(Math.round(win.reduce((a, b) => a + b, 0) / n * 100) / 100)
  }
  return out
}

export default function DetailView() {
  const { loadSubject } = useSAMCData()
  const activeId = useStore(s => s.activeId)
  const activeDetail = useStore(s => s.activeDetail)
  const setView = useStore(s => s.setView)
  const subjects = useStore(s => s.subjects)
  const setActive = useStore(s => s.setActive)
  const setTimeframe = useStore(s => s.setTimeframe)
  const quotes = useStore(s => s.quotes)

  const chartElRef = useRef(null)
  const canvasRef = useRef(null)
  const [trailData, setTrailData] = useState(null)

  // 加载单股详情
  useEffect(() => {
    if (activeId) loadSubject(activeId)
  }, [activeId, loadSubject])

  const d = activeDetail
  const closes = d?.closes ?? (activeId ? quotes[activeId]?.closes : null) ?? []

  // 历史变更轨迹图（三线：close / MA20 / MA50）
  useEffect(() => {
    const el = chartElRef.current
    if (!el || !closes.length) return
    const chart = createChart(el, {
      layout: { background: { type: ColorType.Solid, color: '#131722' }, textColor: '#787b86', fontSize: 11 },
      grid: { vertLines: { color: '#1e222d' }, horzLines: { color: '#1e222d' } },
      rightPriceScale: { borderColor: '#2a2e39' },
      timeScale: { borderColor: '#2a2e39' },
    })
    const days = tradingDays(closes.length)

    const line = chart.addSeries(LineSeries, { color: '#2962ff', lineWidth: 2, priceLineVisible: false })
    const ma20 = chart.addSeries(LineSeries, { color: '#d4a853', lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
    const ma50 = chart.addSeries(LineSeries, { color: '#787b86', lineWidth: 1, priceLineVisible: false, lastValueVisible: false })

    line.setData(closes.map((v, i) => ({ time: days[i], value: v })))
    ma20.setData(sma(closes, 20).map((v, i) => v === null ? null : { time: days[i], value: v }).filter(Boolean))
    ma50.setData(sma(closes, 50).map((v, i) => v === null ? null : { time: days[i], value: v }).filter(Boolean))

    chart.timeScale().fitContent()
    const ro = new ResizeObserver(es => {
      const { width, height } = es[0].contentRect
      chart.applyOptions({ width, height })
    })
    ro.observe(el)
    return () => { ro.disconnect(); chart.remove() }
  }, [closes])

  // 风险拓扑图（Canvas）：中心节点 + 同组关联节点
  useEffect(() => {
    const cv = canvasRef.current
    if (!cv) return
    const ctx = cv.getContext('2d')
    const W = cv.width, H = cv.height
    ctx.clearRect(0, 0, W, H)
    ctx.fillStyle = '#131722'; ctx.fillRect(0, 0, W, H)

    const group = d?.group ?? ''
    const peers = subjects.filter(s => s.group === group && s.id !== activeId).slice(0, 6)
    const center = { x: W / 2, y: H / 2 }

    // 连线
    peers.forEach((p, i) => {
      const ang = (i / peers.length) * Math.PI * 2 - Math.PI / 2
      const r = Math.min(W, H) * 0.32
      const pos = { x: center.x + Math.cos(ang) * r, y: center.y + Math.sin(ang) * r }
      ctx.beginPath(); ctx.moveTo(center.x, center.y); ctx.lineTo(pos.x, pos.y)
      ctx.strokeStyle = p.chg >= 0 ? 'rgba(8,153,129,0.35)' : 'rgba(242,54,69,0.35)'
      ctx.lineWidth = 1; ctx.stroke()
    })

    // 中心节点
    const cr = 26 + (d?.risk ?? 0) / 100 * 14
    const cg = ctx.createRadialGradient(center.x - cr / 3, center.y - cr / 3, 4, center.x, center.y, cr)
    cg.addColorStop(0, '#2962ff'); cg.addColorStop(1, '#1a3fb0')
    ctx.beginPath(); ctx.arc(center.x, center.y, cr, 0, Math.PI * 2); ctx.fillStyle = cg; ctx.fill()
    ctx.strokeStyle = 'rgba(255,255,255,0.35)'; ctx.lineWidth = 1.5; ctx.stroke()
    ctx.fillStyle = '#fff'; ctx.font = 'bold 10px "SF Mono", Menlo, monospace'; ctx.textAlign = 'center'
    ctx.fillText(d?.short ?? '—', center.x, center.y + 3)
    ctx.font = '9px sans-serif'; ctx.fillStyle = 'rgba(255,255,255,0.75)'
    ctx.fillText(`risk ${d?.risk ?? 0}%`, center.x, center.y + 18)

    // 关联节点
    peers.forEach((p, i) => {
      const ang = (i / peers.length) * Math.PI * 2 - Math.PI / 2
      const r = Math.min(W, H) * 0.32
      const pos = { x: center.x + Math.cos(ang) * r, y: center.y + Math.sin(ang) * r }
      const pr = 10 + p.risk / 100 * 8
      ctx.beginPath(); ctx.arc(pos.x, pos.y, pr, 0, Math.PI * 2)
      ctx.fillStyle = p.chg >= 0 ? '#089981' : '#f23645'
      ctx.fill()
      ctx.strokeStyle = '#131722'; ctx.lineWidth = 1.5; ctx.stroke()
      ctx.fillStyle = '#fff'; ctx.font = 'bold 9px "SF Mono", Menlo, monospace'
      ctx.fillText(p.short.slice(0, 6), pos.x, pos.y + 3)
      ctx.font = '8px sans-serif'; ctx.fillStyle = 'rgba(255,255,255,0.7)'
      ctx.fillText(`${p.chg >= 0 ? '+' : ''}${p.chg.toFixed(1)}%`, pos.x, pos.y + 15)
    })
  }, [d, subjects, activeId])

  if (!activeId) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ color: 'var(--tv-dim)' }}>
        <AlertTriangle size={20} style={{ marginRight: 8 }} /> 请先在右侧 Watchlist 选择一个 Subject
      </div>
    )
  }

  const meta = [
    { icon: User, label: 'Owner', value: d?.group ?? quotes[activeId]?.group ?? '未披露' },
    { icon: CalendarClock, label: 'Expiration', value: new Date().toISOString().slice(0, 10) + '（数据截止日）' },
    { icon: Hash, label: 'Metadata Hash', value: d ? djb2(JSON.stringify(d)) : '—', mono: true },
  ]

  return (
    <div className="flex-1 flex flex-col" style={{ minWidth: 0, background: 'var(--tv-bg)' }}>
      {/* 顶栏：返回 + 标题 */}
      <div className="flex items-center shrink-0" style={{ height: 40, padding: '0 10px', gap: 10, borderBottom: '1px solid var(--tv-border)' }}>
        <button
          onClick={() => setView('main')}
          className="tv-hover"
          style={{ padding: '5px 12px', borderRadius: 4, cursor: 'pointer', border: '1px solid var(--tv-border)', background: 'var(--tv-card)', color: 'var(--tv-text)', display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <ArrowLeft size={14} /> 返回主视图
        </button>
        <span className="mono" style={{ fontWeight: 700, fontSize: 14 }}>{d?.short ?? activeId} · 细分选项深度详情</span>
        <span style={{ color: 'var(--tv-dim)', fontSize: 11 }}>{d?.name ?? ''}</span>
        <span className="mono" style={{ fontSize: 12, color: (d?.chg ?? 0) >= 0 ? 'var(--tv-up)' : 'var(--tv-down)' }}>
          {(d?.chg ?? 0) >= 0 ? '+' : ''}{(d?.chg ?? 0).toFixed(2)}%
        </span>
        <div className="flex-1" />
        <button onClick={() => { setTimeframe('1d'); setView('main') }} className="tv-hover" style={{ padding: '4px 10px', borderRadius: 4, cursor: 'pointer', border: 'none', background: 'transparent', color: 'var(--tv-dim)', fontSize: 11 }}>
          主图联动：{d?.name ?? ''}
        </button>
      </div>

      <div className="flex flex-1" style={{ minHeight: 0, gap: 0 }}>
        {/* 左：元数据 */}
        <div className="shrink-0 tv-panel" style={{ width: 240, margin: 8, padding: 12, borderRadius: 6, overflowY: 'auto' }}>
          <div style={{ fontWeight: 700, marginBottom: 10, color: 'var(--tv-text)', fontSize: 12 }}>SUBJECT 元数据</div>
          {meta.map(({ icon: Icon, label, value, mono }) => (
            <div key={label} style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--tv-dim)', fontSize: 10, marginBottom: 4, letterSpacing: 0.5 }}>
                <Icon size={11} /> {label.toUpperCase()}
              </div>
              <div className={mono ? 'mono' : ''} style={{ fontSize: 12, wordBreak: 'break-all', color: 'var(--tv-text)' }}>{value}</div>
            </div>
          ))}
          <div style={{ borderTop: '1px solid var(--tv-border)', margin: '6px 0 10px' }} />
          <div style={{ color: 'var(--tv-dim)', fontSize: 10, marginBottom: 6, letterSpacing: 0.5 }}>属性快照</div>
          {[['Price', d?.price], ['RSI14', d?.rsi14], ['MA20', d?.ma20], ['MA50', d?.ma50], ['52W High', d?.hi52], ['52W Low', d?.lo52], ['YTD', d?.ytd ? d.ytd.toFixed(2) + '%' : '—']].map(([k, v]) => (
            <div key={k} className="flex" style={{ justifyContent: 'space-between', padding: '3px 0', fontSize: 11, borderBottom: '1px solid rgba(42,46,57,0.5)' }}>
              <span style={{ color: 'var(--tv-dim)' }}>{k}</span>
              <span className="mono" style={{ color: 'var(--tv-text)' }}>{v ?? '—'}</span>
            </div>
          ))}
        </div>

        {/* 中：历史变更轨迹 */}
        <div className="flex-1 flex flex-col tv-panel" style={{ margin: '8px 0', borderRadius: 6, minWidth: 0 }}>
          <div className="flex items-center shrink-0" style={{ height: 32, padding: '0 10px', gap: 12, borderBottom: '1px solid var(--tv-border)', color: 'var(--tv-dim)', fontSize: 11 }}>
            <span style={{ fontWeight: 700, color: 'var(--tv-text)' }}>属性历史变更轨迹</span>
            <span><span style={{ color: '#2962ff' }}>━</span> Close</span>
            <span><span style={{ color: '#d4a853' }}>━</span> MA20</span>
            <span><span style={{ color: '#787b86' }}>━</span> MA50</span>
            <div className="flex-1" />
            <span style={{ fontSize: 10 }}>MA 序列由 closes 滑动窗口计算 [推断]</span>
          </div>
          <div className="flex-1 relative" style={{ minHeight: 0 }}>
            <div ref={chartElRef} style={{ position: 'absolute', inset: 0 }} />
          </div>
        </div>

        {/* 右：风险拓扑 */}
        <div className="shrink-0 tv-panel" style={{ width: 300, margin: 8, borderRadius: 6, display: 'flex', flexDirection: 'column' }}>
          <div className="flex items-center shrink-0" style={{ height: 32, padding: '0 10px', borderBottom: '1px solid var(--tv-border)', color: 'var(--tv-dim)', fontSize: 11 }}>
            <span style={{ fontWeight: 700, color: 'var(--tv-text)' }}>关联风险节点拓扑</span>
            <div className="flex-1" />
            <span style={{ fontSize: 10 }}>同组 {d?.group ?? ''}</span>
          </div>
          <div className="flex-1" style={{ minHeight: 0 }}>
            <canvas ref={canvasRef} width={600} height={420} style={{ width: '100%', height: '100%', display: 'block' }} />
          </div>
          <div style={{ padding: '8px 10px', borderTop: '1px solid var(--tv-border)', fontSize: 10, color: 'var(--tv-faint)' }}>
            节点半径 ∝ 风险指数；绿/红 = 当日涨/跌；连线表示同组关联
          </div>
        </div>
      </div>
    </div>
  )
}
