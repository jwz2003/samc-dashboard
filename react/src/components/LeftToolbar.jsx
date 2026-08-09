import {
  Crosshair, LineChart, CandlestickChart, AreaChart, Ruler, Magnet, PenLine, Type,
  FolderOpen, BarChart3, ShieldAlert, Trash2, MoveUpRight,
} from 'lucide-react'
import { useStore } from '../store.js'

const TOOLS = [
  { icon: Crosshair, tip: '十字光标', active: true },
  { icon: CandlestickChart, tip: 'K线' },
  { icon: AreaChart, tip: '面积图' },
  { icon: LineChart, tip: '线段' },
  { icon: Ruler, tip: '量尺' },
  { icon: PenLine, tip: '画笔' },
  { icon: Type, tip: '文字' },
  { icon: Magnet, tip: '磁吸' },
  { icon: BarChart3, tip: '指标' },
  { icon: ShieldAlert, tip: '风险分析' },
  { icon: FolderOpen, tip: '数据源' },
  { icon: Trash2, tip: '清除' },
]

export default function LeftToolbar() {
  const setView = useStore(s => s.setView)
  return (
    <div
      className="flex flex-col items-center shrink-0"
      style={{ width: 45, background: 'var(--tv-card)', borderRight: '1px solid var(--tv-border)', padding: '6px 0', gap: 2, overflowY: 'auto' }}
    >
      {TOOLS.map(({ icon: Icon, tip, active }, i) => (
        <button
          key={tip}
          title={tip}
          onClick={() => { if (tip === '风险分析') setView('detail') }}
          className="tv-hover"
          style={{
            width: 32, height: 32, borderRadius: 4, cursor: 'pointer', border: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: active ? 'var(--tv-sel)' : 'transparent',
            color: active ? '#fff' : 'var(--tv-dim)',
          }}
        >
          <Icon size={16} />
        </button>
      ))}
      <div className="flex-1" />
      <button
        title="返回主视图"
        onClick={() => setView('main')}
        className="tv-hover"
        style={{ width: 32, height: 32, borderRadius: 4, cursor: 'pointer', border: 'none', background: 'transparent', color: 'var(--tv-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      >
        <MoveUpRight size={16} />
      </button>
    </div>
  )
}
