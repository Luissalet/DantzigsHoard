# Dantzig · capacidades actuales

Motor de planificación con editor, resolución lexicográfica en dos etapas, calendarios de indisponibilidad y tema oscuro común. Configurador finito con completado, reparación mínima y lista de materiales. Estado exacto de aprobación e integración de1938/1941/1942/1980 en el Ágora del espacio dantzig; una prueba positiva no equivale a un voto de revisión.

MCP: `dantzig_example` y `dantzig_validate` declaran lectura pura para su descubrimiento en modo Plan. No crean datos. Guardar, resolver y exportar siguen siendo operaciones persistentes; no se marcan como lectura.

Siete herramientas nativas de planificación: dantzig_validate, dantzig_export, dantzig_example, dantzig_save_problem, dantzig_solve, dantzig_records, dantzig_record. Comparten servicio con HTTP. Descubrimiento/validación no inician HTTP ni abren datos. Sin Sparks ni GPU para calcular.

Interfaz: editor de recursos/pedidos y cierres por recurso, Gantt más tabla, comparación de objetivos, historial propio, importación/exportaciónJSON y borrador persistente. Estados optimal/feasible/infeasible/unknown. Objetivos y alcance detallados en README. Los ciclos de precedencia se rechazan explícitamente; no interpretar unknown como imposible.

Verificación del conjunto con calendarios y anotaciones:118pruebas positivas en16,37s. MCPstdio real, contraste independiente de objetivos y24casos exhaustivos de calendarios, más regresiones de tiempos grandes. La revisión1938r2 contrastó300casos adicionales del motor anterior. Brave: comparar, guardar, reabrir, invalidar al editar, imposibilidad, importación y borrador incompleto; calendario, renombrado Unicode y vista390px. Icono basado en el dragón común, sustituyendo el rechazado por Luis. Copilot1941 aprobado.

Registro nativo comprobado: Hub puerto5241, conector Faustus53af00d1 y servidorMCPc00af948,16herramientas conectadas desde la instalación permanente. Un turno real del modelo global deepseek-v4.1-flash leyó y validó el ejemplo mediante dos llamadas MCP, con entrada y resultado coincidentes;37,34s y3rondas, sin herramientas persistentes. Es un caso de integración, no una evaluación de competencia general. Evidencia DANTZIG-MODELO-HERRAMIENTAS-QA.json en Research.

Coordinación: dantzig1938 y1939, programa ecosystem1937. Investigación: E:/Development/IA/Research/Hangar-2026-11-02.

## Configurador (tarea1939)

Herramientas: `dantzig_config_examples`, `dantzig_config_example`, `dantzig_config_save_catalog`, `dantzig_config_catalogs`, `dantzig_config_propagate`, `dantzig_config_complete`, `dantzig_config_repair`, `dantzig_config_explain`, `dantzig_config_verify`. Aceptan `catalog_id` (guardado o de ejemplo, p. ej. `drive-kit`) o `catalog` en línea y `selections` `{hueco: opción | null}`.

Para un encargo de configurador: formular el catálogo como JSON (huecos, opciones con atributos, reglas requires/excludes/compare/sum), guardarlo, usar propagate mientras se elige, complete para cerrar, repair cuando el cliente pide algo imposible y explain para justificarlo. Con catálogos pequeños, verify demuestra el resultado por enumeración. Página para Luis: `/configurator`.

## Integración de familia1941

Copiloto común con biblioteca canónica; /api/copilot/info y launcher200, panel abierto enBrave sin invocar modelo. Contexto propio del borrador definido en window.hoardCopilot. No se afirma lectura viva de ese objeto desde el evaluador de navegador. Manifiesto arrancable y puerto adaptable, validado con el parser real delHub. MCPstdio probado con16herramientas desde el cliente nativo McpManager de Faustus en un entorno aislado. Esto no acredita por sí mismo una conexión operativa registrada en el panel.

Exportación1942: preparación JSON persistente por API y dantzig_export, descargaHTTP con nombre controlado. API/MCP y selector de importación probados; descarga en disco desde el navegador sin certificar. Consultar README para límites de la verificación. El total de herramientas del candidato es16 (7planificación/exportación y9configurador).

## Calendarios candidatos1980

Campo opcional del problema: `unavailability: {recurso: [{start, end}]}`. Periodos sin disponibilidad semiabiertos, enteros, sin interrupción del trabajo; recursos desconocidos y ventanas inválidas se rechazan explícitamente. Las herramientas validate/solve y la API aceptan el mismo campo. El editor y el contexto del copiloto conservan el calendario, incluido un borrador incompleto. Ejemplo: un trabajo de12unidades y cierre10–20 se planifica20–32.

117pruebas positivas en esta rama, incluidas25de calendarios y24contrastes exhaustivos. MCPstdio/HTTP y Brave probados, móvil390px. No afirmar capacidad integrada: tarea1980 pendiente de revisión propia y de integrar su base1938/1942. No se añade conversión de horas ni recurrencia semanal automática.

## Skills for the agents that connect

This app carries procedures from the skill library of the family's workspace for the agents that connect to it: `constraint-scheduling`, `spec-driven-development`, `verification-loop`. They are named in what an agent reads on connecting, read with `skills_list` and `skill_read`, searched and assigned with `skills_library` and `skills_assign`, and offered as prompts. The person chooses them on the skills page (`/api/agent/skills/page`) or in the hub's Skills tab; the `skills` block of `faustus-plugin.json` holds what the app asks for by default.
