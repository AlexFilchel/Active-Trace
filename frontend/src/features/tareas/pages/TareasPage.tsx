import { useTareas } from '../hooks/useTareas'
import { useCreateTarea } from '../hooks/useCreateTarea'
import { useUpdateTarea } from '../hooks/useUpdateTarea'
import { KanbanTareas } from '../components/KanbanTareas'
import { FormTarea } from '../components/FormTarea'
import type { TareaEstado } from '../types'

export function TareasPage() {
  const { data: tareas = [], isLoading } = useTareas()
  const create = useCreateTarea()
  const update = useUpdateTarea()

  function handleMover(id: string, estado: TareaEstado) {
    update.mutate({ id, data: { estado } })
  }

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando tareas…</p>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-800">Tareas internas</h1>

      <section>
        <FormTarea
          onSubmit={(data) => create.mutate(data)}
          isLoading={create.isPending}
        />
      </section>

      <section>
        <KanbanTareas tareas={tareas} onMover={handleMover} />
      </section>
    </div>
  )
}
