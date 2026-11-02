# Dantzig · capacidades actuales

Motor1938r1 integrado y aprobado. Candidato1938r2 añade el editor de planificación y resolución lexicográfica en dos etapas; pendiente de revisión/integración. Configurador1939r2 integrado por su autor, con cambios pedidos por revisión: no tratarlo como entrega aprobada.

Seis herramientas nativas de planificación: dantzig_validate, dantzig_example, dantzig_save_problem, dantzig_solve, dantzig_records, dantzig_record. Comparten servicio con HTTP. Descubrimiento/validación no inician HTTP ni abren datos. Sin Sparks ni GPU para calcular.

Interfaz candidata: editor de recursos/pedidos, Gantt más tabla, comparación de objetivos, historial propio, importación/exportaciónJSON y borrador persistente. Estados optimal/feasible/infeasible/unknown. Objetivos y alcance detallados en README. Los ciclos de precedencia se rechazan explícitamente; no interpretar unknown como imposible.

Verificación del candidato compuesto:77pruebas, MCPstdio real,24contrastes de objetivos y regresión de tiempos grandes. Brave: comparar, guardar, reabrir, invalidar al editar, imposibilidad y recarga de borrador incompleto. Vista390px comprobada. Copilot común, icono y registroHub pendientes.

Coordinación: dantzig1938 y1939, programa ecosystem1937. Investigación: E:/Development/IA/Research/Hangar-2026-11-02.

## Configurador (tarea1939)

Herramientas: `dantzig_config_examples`, `dantzig_config_example`, `dantzig_config_save_catalog`, `dantzig_config_catalogs`, `dantzig_config_propagate`, `dantzig_config_complete`, `dantzig_config_repair`, `dantzig_config_explain`, `dantzig_config_verify`. Aceptan `catalog_id` (guardado o de ejemplo, p. ej. `drive-kit`) o `catalog` en línea y `selections` `{hueco: opción | null}`.

Para un encargo de configurador: formular el catálogo como JSON (huecos, opciones con atributos, reglas requires/excludes/compare/sum), guardarlo, usar propagate mientras se elige, complete para cerrar, repair cuando el cliente pide algo imposible y explain para justificarlo. Con catálogos pequeños, verify demuestra el resultado por enumeración. Página para Luis: `/configurator`.
