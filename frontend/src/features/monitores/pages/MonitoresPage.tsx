import { useState } from 'react'
import { useMonitorGeneral } from '../hooks/useMonitorGeneral'
import { useMonitorEntregas } from '../hooks/useMonitorEntregas'
import { TablaMonitor } from '../components/TablaMonitor'
import { TablaEntregasMonitor } from '../components/TablaEntregasMonitor'

type Tab = 'general' | 'entregas'

export function MonitoresPage() {
  const [activeTab, setActiveTab] = useState<Tab>('general')

  const { data: monitorItems = [], isLoading: loadingGeneral } = useMonitorGeneral()
  const { data: entregas = [], isLoading: loadingEntregas } = useMonitorEntregas()

  const TABS: { id: Tab; label: string }[] = [
    { id: 'general', label: 'Monitor general' },
    { id: 'entregas', label: 'Entregas sin corregir' },
  ]

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-gray-800">Monitores</h1>

      <div className="flex border-b border-gray-200">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab.id
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'general' && (
        <section>
          {loadingGeneral ? (
            <p className="text-sm text-gray-500">Cargando monitor…</p>
          ) : (
            <TablaMonitor items={monitorItems} />
          )}
        </section>
      )}

      {activeTab === 'entregas' && (
        <section>
          {loadingEntregas ? (
            <p className="text-sm text-gray-500">Cargando entregas…</p>
          ) : (
            <TablaEntregasMonitor entregas={entregas} />
          )}
        </section>
      )}
    </div>
  )
}
