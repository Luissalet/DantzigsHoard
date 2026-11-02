# Dantzig · capacidades actuales

Primera entrega1938 en worktree, pendiente de revisión e integración. No tratar el manifiesto como instalación terminada.

Cinco herramientas nativas: `dantzig_example`, `dantzig_save_problem`, `dantzig_solve`, `dantzig_records`, `dantzig_record`. Usan el mismo servicio que HTTP, sin iniciar un servidor como efecto de descubrimiento. Datos locales mediante DANTZIG_DATA. Los cálculos no necesitan Sparks ni GPU.

Resolver: recursos alternativos exclusivos, duración entera, disponibilidad, precedencias, fechas deseadas/obligatorias, prioridades y separación mínima por familia. Informar el estado devuelto: sólo optimal demuestra óptimo, unknown no demuestra imposibilidad. Leer README para el alcance exacto de los cambios de familia y objetivo.

Verificación actual:21 pruebas positivas con MCP stdio real y API;12 contrastes independientes exhaustivos; ejecución POST desde Brave sobre datos QA. Interfaz normal de planificación, copilot común, icono, catálogo Hub y despliegue quedan pendientes. La página inicial redirige a la documentación interactiva técnica. No afirmar que hay Gantt o editor de pedidos.

Coordinación: espacio dantzig, tarea1938; programa ecosystem1937. Investigación persistente: E:/Development/IA/Research/Hangar-2026-11-02.
