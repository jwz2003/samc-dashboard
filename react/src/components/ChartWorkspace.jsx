import { useEffect, useRef, useState } from 'react'
import { createChart, CandlestickSeries, HistogramSeries, AreaSeries, CrosshairMode } from 'lightweight-charts'
import { ArrowLeft, Maximize2, Minimize2 } from 'lucide-react'
import { useStore } from '../store.js'
import { buildCandles, buildArea, resample, tradingDays } from '../hooks/useSAMCData.js'
import DetailView from './DetailView.jsx'

const round2 = x => Math.round(x * 100) / 100

/* ===== 中央工作区 =====
 * 主视图：K线（Candlestick）+ 成交量（Histogram overlay）+ 属性变化频率（Area 底部）
 * 详情视图：平滑切换到 DetailView（阶段 4）
 * Crosshair 左上角 OHLC 悬浮框 + ResizeObserver 自适应 + 模拟 Tick 流
 */
export default function ChartWorkspace() {
  const view = useStore(s => s.view)
  return view === 'detail' ? <DetailView /> : <MainChart />
}

function MainChart() {
  const containerRef = useRef(null)
  const chartRef = useRef(null)
  const candleRef = useRef(null)
  const volRef = useRef(null)
  const areaRef = useRef(null)
  const [ohlc, setOhlc] = useState(null)      // Crosshair 悬浮 OHLC
  const [expanded, setExpanded] = useState(false)

  const quotes = useStore(s => s.quotes)
  const subjects = useStore(s => s.subjects)
  const activeId = useStore(s => s.activeId)
  const setActive = useStore(s => s.setActive)
  const timeframe = useStore(s => s.timeframe)
  const pushLog = useStore(s => s.pushLog)
  const setView = useStore(s => s.setView)

  const active = subjects.find(s => s.id === activeId) || subjects[0]
  const quote = active ? quotes[active.id] : null

  // ---- 图表初始化（一次） ----
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const chart = createChart(el, {
      layout: { background: { type: 'solid', color: '#131722' }, textColor: '#787b86', fontSize: 11, fontFamily: '"SF Mono", ui-monospace, Menlo, monospace' },
      grid: { vertLines: { color: '#1e222d' }, horzLines: { color: '#1e222d' } },
      rightPriceScale: { borderColor: '#2a2e39' },
      timeScale: { borderColor: '#2a2e39', timeVisible: false },
      crosshair: { mode: CrosshairMode.Normal, vertLine: { color: '#758696', width: 1, style: 3 }, horzLine: { color: '#758696', width: 1, style: 3 } },
      handleScroll: true,
      handleScale: true,
    })
    chartRef.current = chart

    // K线主序列
    const candle = chart.addSeries(CandlestickSeries, {
      upColor: '#089981', downColor: '#f23645', borderUpColor: '#089981', borderDownColor: '#f23645',
      wickUpColor: '#089981', wickDownColor: '#f23645',
    })
    candleRef.current = candle

    // 成交量（overlay 在 K 线下方）
    const vol = chart.addSeries(HistogramSeries, {
      priceScaleId: 'vol', priceFormat: { type: 'volume' },
      color: '#2962ff', priceLineVisible: false, lastValueVisible: false,
    })
    volRef.current = vol
    chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } })

    // 属性变化频率面积图（底部独立刻度）
    const area = chart.addSeries(AreaSeries, {
      priceScaleId: 'attr', lineColor: '#d4a853', topColor: 'rgba(212,168,83,0.25)', bottomColor: 'rgba(212,168,83,0.02)',
      lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
    })
    areaRef.current = area
    chart.priceScale('attr').applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } })

    // Crosshair 联动 → 左上角 OHLC 悬浮框
    chart.subscribeCrosshairMove(param => {
      const d = param.seriesData.get(candle)
      setOhlc(d && param.time ? { time: param.time, ...d } : null)
    })

    // ResizeObserver：窗口缩放自动适配
    const ro = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect
      chart.applyOptions({ width, height })
    })
    ro.observe(el)

    pushLog('INFO', '图表引擎就绪：Candlestick + Volume + Attribute Frequency')

    return () => { ro.disconnect(); chart.remove() }
  }, [pushLog])

  // ---- 数据驱动：active / timeframe 变化时刷新 ----
  useEffect(() => {
    const candle = candleRef.current, vol = volRef.current, area = areaRef.current, chart = chartRef.current
    if (!candle || !quote) return

    const closes = resample(quote.closes || [], timeframe)
    const days = tradingDays(closes.length)
    const candles = buildCandles(closes).map((k, i) => ({ ...k, time: days[i] }))

    candle.setData(candles)

    // 成交量 = [推断] 由 |Δclose| 归一化模拟
    const maxD = Math.max(...candles.map((k, i) => i === 0 ? 1 : Math.abs(k.close - candles[i - 1].close)), 1)
    vol.setData(candles.map((k, i) => ({
      time: k.time,
      value: i === 0 ? 1 : Math.max(0.2, Math.abs(k.close - candles[i - 1].close) / maxD),
      color: k.close >= k.open ? 'rgba(8,153,129,0.45)' : 'rgba(242,54,69,0.45)',
    })))

    const areaData = buildArea(closes).map((a, i) => ({ ...a, time: days[i] }))
    area.setData(areaData)

    chart.timeScale().fitContent()
    setOhlc(null)
  }, [quote, timeframe])

  // ---- 模拟 WebSocket Tick 流（每 2s 微调最后收盘价）----
  useEffect(() => {
    if (!quote || timeframe !== '1d') return
    const id = setInterval(() => {
      const candle = candleRef.current
      if (!candle) return
      const data = candle.data()
      if (!data.length) return
      const last = data[data.length - 1]
      const drift = last.close * (Math.random() - 0.5) * 0.0008
      const up = drift >= 0
      candle.update({
        time: last.time, open: last.open, close: round2(last.close + drift),
        high: Math.max(last.high, last.close + drift), low: Math.min(last.low, last.close + drift),
      })
    }, 2000)
    return () => clearInterval(id)
  }, [quote, timeframe])

  const chg = active?.chg ?? 0
  const risk = active?.risk ?? 0

  return (
    <div className="flex-1 flex flex-col" style={{ minWidth: 0, background: 'var(--tv-bg)', position: 'relative' }}>
      {/* 图表工具条 */}
      <div className="flex items-center shrink-0" style={{ height: 34, padding: '0 10px', gap: 10, borderBottom: '1px solid var(--tv-border)' }}>
        <span className="mono" style={{ fontWeight: 700, fontSize: 13 }}>
          {active?.short} <span style={{ color: 'var(--tv-dim)', fontWeight: 400 }}>{active?.name}</span>
        </span>
        <span className="mono" style={{ fontSize: 13, color: chg >= 0 ? 'var(--tv-up)' : 'var(--tv-down)', fontWeight: 700 }}>
          {quote ? quote.price.toLocaleString() : '—'} {quote?.cur}
        </span>
        <span className="mono" style={{ fontSize: 12, color: chg >= 0 ? 'var(--tv-up)' : 'var(--tv-down)' }}>
          {chg >= 0 ? '+' : ''}{chg.toFixed(2)}%
        </span>
        <span style={{ color: 'var(--tv-faint)', fontSize: 11 }}>RSI {quote?.rsi14?.toFixed?.(1) ?? '—'}</span>
        <span style={{ color: 'var(--tv-faint)', fontSize: 11 }}>风险 {risk}%</span>
        <div className="flex-1" />
        <span style={{ color: 'var(--tv-faint)', fontSize: 10 }}>K线由日线合成 [推断] · Tick 为模拟流</span>
        <button className="tv-hover" style={{ padding: 4, borderRadius: 4, cursor: 'pointer', border: 'none', background: 'transparent', color: 'var(--tv-dim)', display: 'flex' }}
          onClick={() => setExpanded(!expanded)}>
          {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        </button>
      </div>

      {/* 图表容器 */}
      <div className="relative flex-1" style={{ minHeight: 0 }}>
        <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />

        {/* Crosshair 左上角 OHLC 悬浮框 */}
        {ohlc && (
          <div className="mono" style={{
            position: 'absolute', top: 6, left: 8, zIndex: 5,
            background: 'rgba(19,23,34,0.92)', border: '1px solid var(--tv-border)', borderRadius: 4, padding: '5px 8px', fontSize: 11, lineHeight: 1.6, pointerEvents: 'none',
          }}>
            <div style={{ color: 'var(--tv-dim)' }}>{ohlc.time}</div>
            <div>O <span style={{ color: 'var(--tv-text)' }}>{ohlc.open.toFixed(2)}</span></div>
            <div>H <span style={{ color: 'var(--tv-up)' }}>{ohlc.high.toFixed(2)}</span></div>
            <div>L <span style={{ color: 'var(--tv-down)' }}>{ohlc.low.toFixed(2)}</span></div>
            <div>C <span style={{ color: ohlc.close >= ohlc.open ? 'var(--tv-up)' : 'var(--tv-down)' }}>{ohlc.close.toFixed(2)}</span></div>
          </div>
        )}

        {/* 无选中时提示 */}
        {!activeId && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--tv-dim)', zIndex: 2, pointerEvents: 'none' }}>
            从右侧 Watchlist 选择 Subject 开始分析
          </div>
        )}
      </div>

      {/* 底部快捷栏 */}
      <div className="flex items-center shrink-0" style={{ height: 32, padding: '0 10px', gap: 12, borderTop: '1px solid var(--tv-border)', color: 'var(--tv-dim)', fontSize: 11 }}>
        <span>标的：{subjects.length}</span>
        <span>Active：{subjects.filter(s => s.status === 'Active').length}</span>
        <span style={{ color: 'var(--tv-down)' }}>Suspended：{subjects.filter(s => s.status === 'Suspended').length}</span>
        <div className="flex-1" />
        <button
          onClick={() => { if (activeId) setView('detail') }}
          className="tv-hover"
          style={{ padding: '3px 10px', borderRadius: 4, cursor: 'pointer', border: '1px solid var(--tv-border)', background: 'var(--tv-card)', color: 'var(--tv-blue)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 5 }}
        >
          <ArrowLeft size={12} style={{ transform: 'rotate(180deg)' }} /> 详细分析
        </button>
        <button onClick={() => { if (activeId) setView('detail') }} className="tv-hover" style={{ padding: 3, borderRadius: 4, cursor: 'pointer', border: 'none', background: 'transparent', color: 'var(--tv-dim)', display: 'flex' }}>
          <Maximize2 size={13} />
        </button>
        <span className="tv-hover" style={{ cursor: 'pointer' }} onClick={() => setActive(null)}>取消选择</span>
      </div>
    </div>
  )
}
