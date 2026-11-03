# Dantzig · capacidades actuales

MCP: `dantzig_example` y `dantzig_validate` declaran lectura pura para su descubrimiento en modo Plan. No crean datos. Guardar, resolver y exportar siguen siendo operaciones persistentes; no se marcan como lectura.

Motor1938r1 integrado y aprobado. Configurador1939r3 aprobado e integrado en7c46280. Candidato1938r3 añade editor de planificación, resolución lexicográfica en dos etapas y tema oscuro común; corrige los cambios visuales pedidos en1938r2, cuyo funcionamiento está aprobado. Pendiente de nueva revisión/integración.

Siete herramientas nativas de planificación: dantzig_validate, dantzig_export, dantzig_example, dantzig_save_problem, dantzig_solve, dantzig_records, dantzig_record. Comparten servicio con HTTP. Descubrimiento/validación no inician HTTP ni abren datos. Sin Sparks ni GPU para calcular.

Interfaz candidata: editor de recursos/pedidos, Gantt más tabla, comparación de objetivos, historial propio, importación/exportaciónJSON y borrador persistente. Estados optimal/feasible/infeasible/unknown. Objetivos y alcance detallados en README. Los ciclos de precedencia se rechazan explícitamente; no interpretar unknown como imposible.

Verificación del candidato compuesto:92pruebas, MCPstdio real,24contrastes de objetivos y regresión de tiempos grandes; revisión independiente1938r2 con300 casos adicionales. Brave: comparar, guardar, reabrir, invalidar al editar, imposibilidad, importación y recarga de borrador incompleto. Vista oscura390px comprobada. Icono corregido a partir del dragón común, sustituyendo el rechazado por Luis. Copilot común1941 aprobado, pendiente de integrar junto al planificador; registroHub pendiente.

Coordinación: dantzig1938 y1939, programa ecosystem1937. Investigación: E:/Development/IA/Research/Hangar-2026-11-02.

## Configurador (tarea1939)

Herramientas: `dantzig_config_examples`, `dantzig_config_example`, `dantzig_config_save_catalog`, `dantzig_config_catalogs`, `dantzig_config_propagate`, `dantzig_config_complete`, `dantzig_config_repair`, `dantzig_config_explain`, `dantzig_config_verify`. Aceptan `catalog_id` (guardado o de ejemplo, p. ej. `drive-kit`) o `catalog` en línea y `selections` `{hueco: opción | null}`.

Para un encargo de configurador: formular el catálogo como JSON (huecos, opciones con atributos, reglas requires/excludes/compare/sum), guardarlo, usar propagate mientras se elige, complete para cerrar, repair cuando el cliente pide algo imposible y explain para justificarlo. Con catálogos pequeños, verify demuestra el resultado por enumeración. Página para Luis: `/configurator`.

## Candidato de familia1941

Copilotocomún incorporado con biblioteca canónica; /api/copilot/info y launcher200, panel abierto enBrave sin invocar modelo. Contexto propio del borrador definido en window.hoardCopilot. Se ha comprobado la definición en código; el evaluador de navegador no expone ese global para leerlo, por tanto no se afirma lectura viva de ese objeto. Manifiesto arrancable y puerto adaptable, validado con parser real delHub. RegistroHub y conexión operativa del panel con las herramientas pendientes de revisión/integración. MCPstdio sigue siendo el acceso de herramientas probado.

Exportación1942: preparación JSON persistente por API y dantzig_export, descargaHTTP con nombre controlado. API/MCP y selector de importación probados; descarga en disco desde el navegador sin certificar. Consultar README para límites de la verificación. El total de herramientas del candidato es16 (7planificación/exportación y9configurador).
