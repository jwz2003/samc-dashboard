import { useEffect } from 'react'
import { useStore } from './store.js'
import { useSAMCData } from './hooks/useSAMCData.js'
import TopBar from './components/TopBar.jsx'
import LeftToolbar from './components/LeftToolbar.jsx'
import ChartWorkspace from './components/ChartWorkspace.jsx'
import RightSidebar from './components/RightSidebar.jsx'
import BottomPanel from './components/BottomPanel.jsx'

export default function App() {
  const { loadQuotes } = useSAMCData()
  const loading = useStore(s => s.loading)

  useEffect(() => {
    loadQuotes().catch(() => { /* 回退逻辑已由 hook 内处理 */ })
  }, [loadQuotes])

  if (loading) {
    return (
      <div className="flex flex-col" style={{ height: '100vh', background: 'var(--tv-bg)' }}>
        <div style={{ height: 48, background: 'var(--tv-card)', borderBottom: '1px solid var(--tv-border)', display: 'flex', alignItems: 'center', padding: '0 12px', gap: 8 }}>
          <div className="skeleton-bar" style={{ width: 140, height: 14 }} />
          <div className="skeleton-bar" style={{ width: 200, height: 26, borderRadius: 4 }} />
          <div className="skeleton-bar" style={{ width: 120, height: 26, borderRadius: 4 }} />
        </div>
        <div className="flex flex-1" style={{ minHeight: 0 }}>
          <div style={{ width: 45, background: 'var(--tv-card)', borderRight: '1px solid var(--tv-border)' }} />
          <div className="flex-1 flex items-center justify-center" style={{ background: 'var(--tv-bg)' }}>
            <div style={{ textAlign: 'center', color: 'var(--tv-dim)' }}>
              <div className="skeleton-ring" style={{ width: 42, height: 42, margin: '0 auto 12px' }} />
              <div>正在连接数据源 · 加载 Subject 行情…</div>
            </div>
          </div>
          <div style={{ width: 300, background: 'var(--tv-card)', borderLeft: '1px solid var(--tv-border)', padding: 10 }}>
            {[0, 1, 2, 3, 4, 5].map(i => (
              <div key={i} className="skeleton-bar" style={{ height: 44, marginBottom: 8, borderRadius: 4 }} />
            ))}
          </div>
        </div>
        <style>{`
          @keyframes sk-pulse { 0%,100% { opacity: .35 } 50% { opacity: .7 } }
          .skeleton-bar { background: var(--tv-card-hover); animation: sk-pulse 1.2s ease-in-out infinite; }
          .skeleton-ring { border: 3px solid var(--tv-card-hover); border-top-color: var(--tv-blue); border-radius: 50%; animation: sk-spin 1s linear infinite; }
          @keyframes sk-spin { to { transform: rotate(360deg) } }
        `}</style>
      </div>
    )
  }

  return (
    <div className="flex flex-col" style={{ height: '100vh', background: 'var(--tv-bg)' }}>
      {/* Top Bar 48px */}
      <TopBar />
      <div className="flex flex-1" style={{ minHeight: 0 }}>
        {/* Left Toolbar 45px */}
        <LeftToolbar />
        {/* Center Workspace：主图表区 / 深度详情页 */}
        <ChartWorkspace />
        {/* Right Sidebar 300px 可折叠 */}
        <RightSidebar />
      </div>
      {/* Bottom Panel 可调高度 */}
      <BottomPanel />
    </div>
  )
}
