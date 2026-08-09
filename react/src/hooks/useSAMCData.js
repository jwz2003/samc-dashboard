import { useCallback } from 'react'
import { useStore, computeStatus } from '../store.js'

/* ===== useSAMCData：对接现有数据源 =====
 * 现有数据：~/dashboard/data.js（window.QUOTES 全量）
 *          ~/dashboard/data/{code}.js（window.QUOTE 单股）
 * 通过 Vite public/ 目录作为静态资源 fetch，剥掉 JS 前缀后 JSON.parse。
 */

async function fetchJSVar(url, varName) {
  const res = await fetch(url, { cache: 'no-store' })
  if (!res.ok) throw new Error(`HTTP ${res.status} @ ${url}`)
  const text = await res.text()
  const json = text.slice(text.indexOf('=') + 1).trim().replace(/;?\s*$/, '')
  return JSON.parse(json)
}

// data/ 文件名编码规则（build_dashboard.py 生成）：%→P ^→C .→D =→E
const safeFile = id => id.replace(/%/g, 'P').replace(/\^/g, 'C').replace(/\./g, 'D').replace(/=/g, 'E') + '.js'

// [推断] 由 closes 合成 OHLC K线（仅有收盘价序列）：open=前收，high/low=±0.2% 包络
export function buildCandles(closes) {
  return closes.map((c, i) => {
    const open = i === 0 ? c : closes[i - 1]
    const range = Math.max(Math.abs(c - open) * 0.15, c * 0.002)
    return {
      time: i, // 占位，调用方替换为真实交易日
      open: round2(open),
      high: round2(Math.max(open, c) + range),
      low: round2(Math.min(open, c) - range),
      close: round2(c),
    }
  })
}

// [推断] 属性变化频率序列（面积图数据源）= |Δclose| 滚动均值
export function buildArea(closes) {
  const out = []
  for (let i = 0; i < closes.length; i++) {
    const d = i === 0 ? 0 : Math.abs(closes[i] - closes[i - 1])
    const win = closes.slice(Math.max(0, i - 4), i + 1)
    const avg = win.reduce((a, b) => a + b, 0) / win.length
    out.push({ value: round4(avg === 0 ? 0 : d / avg), time: i })
  }
  return out
}

// 生成最近 N 个交易日（跳过周末）
export function tradingDays(n, end = new Date()) {
  const days = []
  const d = new Date(end)
  while (days.length < n) {
    const wd = d.getDay()
    if (wd !== 0 && wd !== 6) days.unshift(d.toISOString().slice(0, 10))
    d.setDate(d.getDate() - 1)
  }
  return days
}

// [推断] 子周期重采样：1d 日线插值成 1m/5m/1h 序列（模拟，UI 标注）
export function resample(closes, timeframe) {
  if (timeframe === '1d') return closes
  const n = { '1m': 240, '5m': 48, '1h': 24 }[timeframe] ?? 24
  const out = []
  for (let i = 0; i < closes.length; i++) {
    const base = closes[i]
    for (let j = 0; j < n; j++) {
      const t = j / n
      const next = i + 1 < closes.length ? closes[i + 1] : base
      const drift = (next - base) * t
      const noise = (Math.sin(i * 12.9898 + j * 78.233) * 43758.5453 % 1) - 0.5
      out.push(base + drift + noise * base * 0.0008)
    }
  }
  return out
}

const round2 = x => Math.round(x * 100) / 100
const round4 = x => Math.round(x * 10000) / 10000

export function useSAMCData() {
  const pushLog = useStore(s => s.pushLog)
  const setQuotes = useStore(s => s.setQuotes)
  const setActiveDetail = useStore(s => s.setActiveDetail)
  const setConnState = useStore(s => s.setConnState)

  const loadQuotes = useCallback(async () => {
    setConnState('connecting')
    pushLog('INFO', '数据源连接：data.js（window.QUOTES）')
    try {
      const quotes = await fetchJSVar('data.js', 'QUOTES')
      const n = Object.keys(quotes).length
      setQuotes(quotes)
      setConnState('live')
      pushLog('INFO', `全量行情加载完成：${n} 个 Subject`)
      // 异常主体扫描（WARN）
      let warnN = 0
      for (const [id, q] of Object.entries(quotes)) {
        if (computeStatus(q) === 'Suspended') {
          warnN++
          if (warnN <= 3) pushLog('WARN', `Subject ${id} 状态异常（chg=${(q.chg ?? 0).toFixed(2)}% / RSI=${q.rsi14}）`, id)
        }
      }
      if (warnN > 0) pushLog('WARN', `共 ${warnN} 个 Subject 处于 Suspended 状态`)
      else pushLog('INFO', '全部 Subject 状态正常（Active）')
    } catch (e) {
      setConnState('simulated')
      pushLog('ERROR', `数据加载失败：${e.message}；回退模拟数据`, null)
      throw e
    }
  }, [pushLog, setQuotes, setConnState])

  const loadSubject = useCallback(async (id) => {
    pushLog('INFO', `读取 Subject 详情：${id}`, id)
    try {
      const q = await fetchJSVar(`data/${safeFile(id)}`, 'QUOTE')
      setActiveDetail({ id, ...q })
      pushLog('INFO', `Subject ${id} 详情就绪（${q.name}）`, id)
      return { id, ...q }
    } catch (e) {
      // 回退：商品/指数类无独立文件（data/ 仅存个股），使用 data.js 全量快照
      const fallback = useStore.getState().quotes[id]
      if (fallback) {
        setActiveDetail({ id, ...fallback })
        pushLog('INFO', `Subject ${id} 无独立文件，回退全量快照 data.js`, id)
        return { id, ...fallback }
      }
      pushLog('ERROR', `Subject ${id} 详情加载失败：${e.message}`, id)
      return null
    }
  }, [pushLog, setActiveDetail])

  return { loadQuotes, loadSubject }
}
