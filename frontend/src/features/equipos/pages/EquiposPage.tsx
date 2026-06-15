import { useEquipos } from '../hooks/useEquipos'
import { useCreateEquipo } from '../hooks/useCreateEquipo'
import { useDeleteEquipo } from '../hooks/useDeleteEquipo'
import { useClonarEquipo } from '../hooks/useClonarEquipo'
import { TablaEquipos } from '../components/TablaEquipos'
import { FormEquipo } from '../components/FormEquipo'

export function EquiposPage() {
  const { data: equipos = [], isLoading } = useEquipos()
  const create = useCreateEquipo()
  const remove = useDeleteEquipo()
  const clonar = useClonarEquipo()

  function handleClonar(id: string) {
    const original = equipos.find((e) => e.id === id)
    if (!original) return
    clonar.mutate({ id, payload: { nombre: `${original.nombre} (copia)` } })
  }

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando equipos…</p>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-800">Equipos docentes</h1>

      <section>
        <h2 className="text-base font-medium text-gray-700 mb-3">Nuevo equipo</h2>
        <FormEquipo
          onSubmit={(data) => create.mutate(data)}
          isLoading={create.isPending}
        />
      </section>

      <section>
        <h2 className="text-base font-medium text-gray-700 mb-3">
          Equipos ({equipos.length})
        </h2>
        <TablaEquipos
          equipos={equipos}
          onDelete={(id) => remove.mutate(id)}
          onClonar={handleClonar}
          isDeleting={remove.isPending}
        />
      </section>
    </div>
  )
}
