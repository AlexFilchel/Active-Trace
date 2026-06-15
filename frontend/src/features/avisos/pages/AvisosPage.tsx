import { useAvisos } from '../hooks/useAvisos'
import { useCreateAviso } from '../hooks/useCreateAviso'
import { useDeleteAviso } from '../hooks/useDeleteAviso'
import { TablaAvisos } from '../components/TablaAvisos'
import { FormAviso } from '../components/FormAviso'

export function AvisosPage() {
  const { data: avisos = [], isLoading } = useAvisos()
  const create = useCreateAviso()
  const remove = useDeleteAviso()

  if (isLoading) {
    return <p className="text-sm text-gray-500">Cargando avisos…</p>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-800">Avisos</h1>

      <section>
        <h2 className="text-base font-medium text-gray-700 mb-3">Publicar nuevo aviso</h2>
        <FormAviso
          onSubmit={(data) => create.mutate(data)}
          isLoading={create.isPending}
        />
      </section>

      <section>
        <h2 className="text-base font-medium text-gray-700 mb-3">
          Avisos publicados ({avisos.length})
        </h2>
        <TablaAvisos
          avisos={avisos}
          onDelete={(id) => remove.mutate(id)}
          isDeleting={remove.isPending}
        />
      </section>
    </div>
  )
}
