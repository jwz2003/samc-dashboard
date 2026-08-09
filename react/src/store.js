import { create } from 'zustand'

/* ===== SAMC 数据语义映射 =====
 * Subject = 存储产业链标的（股票/指数）
 * 状态   = Active（正常）/ Suspended（异常：跌幅过大或 RSI 极端）
 * 风险指数 = 综合评分 0-100%，[推断] 公式见 computeRisk
 */

// [推断] 风险指数 = 40% 当日波动 + 35% RSI 偏离度 + 25% 52周位置
export function computeRisk(q) {
  if (!q) return 0
  const chg = Math.min(Math.abs(q.chg ?? 0) / 8, 1)
  const rsiDev = Math.min(Math.abs((q.rsi14 ?? 50) - 50) / 50, 1)
  const range = (q.hi52 ?? 0) - (q.lo52 ?? 0)
  const pos = range > 0 ? 1 - Math.min(Math.max(((q.price ?? 0) - q.lo52) / range, 0), 1) : 0.5
  return Math.round((0.4 * chg + 0.35 * rsiDev + 0.25 * pos) * 100)
}

export function computeStatus(q) {
  if (!q) return 'Suspended'
  const chg = q.chg ?? 0
  const rsi = q.rsi14 ?? 50
  if (chg <= -5 || rsi <= 25 || rsi >= 80) return 'Suspended'
  return 'Active'
}

// 审计日志条目工厂
let logSeq = 0
export function mkLog(level, msg, subject = null) {
  return {
    id: ++logSeq,
    ts: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    level, // INFO | WARN | ERROR
    msg,
    subject,
  }
}

export const useStore = create((set, get) => ({
  quotes: {},        // 全量行情 { code: quote }
  subjects: [],      // 派生列表 [{id,name,short,group,price,chg,status,risk}]
  activeId: null,    // 当前选中 Subject
  activeDetail: null,// 单股详情（fetch data/{code}.js）
  view: 'main',      // main | detail
  timeframe: '1d',   // 1m | 5m | 1h | 1d
  rightOpen: true,   // 右侧面板折叠
  bottomOpen: true,  // 底部面板折叠
  bottomHeight: 220, // 底部面板高度（可拖拽）
  logs: [],          // 审计日志（新在前）
  loading: true,     // 骨架屏
  connState: 'connecting', // connecting | live | simulated

  setQuotes(quotes) {
    const subjects = Object.entries(quotes)
      .map(([id, q]) => ({
        id,
        name: q.name ?? id,
        short: q.short ?? id,
        group: q.group ?? '未分组',
        price: q.price,
        chg: q.chg,
        cur: q.cur,
        status: computeStatus(q),
        risk: computeRisk(q),
      }))
      .sort((a, b) => b.risk - a.risk)
    set({ quotes, subjects, loading: false })
  },

  setActiveDetail(detail) { set({ activeDetail: detail }) },

  setActive(id) { set({ activeId: id }) },
  setView(v) { set({ view: v }) },
  setTimeframe(t) { set({ timeframe: t }) },
  toggleRight() { set(s => ({ rightOpen: !s.rightOpen })) },
  toggleBottom() { set(s => ({ bottomOpen: !s.bottomOpen })) },
  setBottomHeight(h) { set({ bottomHeight: h }) },
  setConnState(s) { set({ connState: s }) },

  pushLog(level, msg, subject) {
    const entry = mkLog(level, msg, subject)
    set(s => ({ logs: [entry, ...s.logs].slice(0, 300) }))
    return entry
  },
}))
