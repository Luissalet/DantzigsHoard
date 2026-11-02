# Dantzig · capacidades actuales

Primera entrega1938 en worktree, pendiente de revisión e integración. No tratar el manifiesto como instalación terminada.

Cinco herramientas nativas: `dantzig_example`, `dantzig_save_problem`, `dantzig_solve`, `dantzig_records`, `dantzig_record`. Usan el mismo servicio que HTTP, sin iniciar un servidor como efecto de descubrimiento. Datos locales mediante DANTZIG_DATA. Los cálculos no necesitan Sparks ni GPU.

Resolver: recursos alternativos exclusivos, duración entera, disponibilidad, precedencias, fechas deseadas/obligatorias, prioridades y separación mínima por familia. Informar el estado devuelto: sólo optimal demuestra óptimo, unknown no demuestra imposibilidad. Leer README para el alcance exacto de los cambios de familia y objetivo.

Verificación actual:21 pruebas positivas con MCP stdio real y API;12 contrastes independientes exhaustivos; ejecución POST desde Brave sobre datos QA. Interfaz normal de planificación, copilot común, icono, catálogo Hub y despliegue quedan pendientes. La página inicial redirige a la documentación interactiva técnica. No afirmar que hay Gantt o editor de pedidos.

Coordinación: espacio dantzig, tarea1938; programa ecosystem1937. Investigación persistente: E:/Development/IA/Research/Hangar-2026-11-02.

## Configurador (tarea1939)

Herramientas: `dantzig_config_examples`, `dantzig_config_example`, `dantzig_config_save_catalog`, `dantzig_config_catalogs`, `dantzig_config_propagate`, `dantzig_config_complete`, `dantzig_config_repair`, `dantzig_config_explain`, `dantzig_config_verify`. Aceptan `catalog_id` (guardado o de ejemplo, p. ej. `drive-kit`) o `catalog` en línea y `selections` `{hueco: opción | null}`.

Para un encargo de configurador: formular el catálogo como JSON (huecos, opciones con atributos, reglas requires/excludes/compare/sum), guardarlo, usar propagate mientras se elige, complete para cerrar, repair cuando el cliente pide algo imposible y explain para justificarlo. Con catálogos pequeños, verify demuestra el resultado por enumeración. Página para Luis: `/configurator`.
