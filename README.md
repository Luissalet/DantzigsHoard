# Dantzig's Hoard

Planificador de taller y configurador de catálogos con restricciones, en local.

![Dantzig's Hoard](app-icon.png)

## Qué es

Dantzig's Hoard resuelve decisiones con restricciones sobre un motor CP-SAT (OR-Tools) que corre dentro del propio proceso. Tiene dos módulos que comparten servicio, base SQLite y herramientas MCP: un **planificador** de trabajos sobre recursos alternativos y un **configurador** de catálogos de componentes con compatibilidades cruzadas.

Cada solución se comprueba fuera del solver, y los problemas guardados son inmutables: guardar una variación crea otro ID, y cada cálculo conserva su propia entrada. El cálculo no consulta ningún modelo de lenguaje.

## Qué hace

**Planificador**
- Asigna cada trabajo a exactamente un recurso compatible, sin interrupciones, con tiempos enteros, disponibilidad, precedencias, fechas de liberación, fechas deseadas con retraso ponderado, fechas límite obligatorias y separación mínima entre trabajos consecutivos de familias distintas.
- Calendarios por recurso: periodos sin disponibilidad (cierres y mantenimiento) como intervalos semiabiertos; los solapados o contiguos se unen para el cálculo y la entrada original se conserva.
- Dos objetivos lexicográficos, retraso ponderado y finalización, en cualquiera de los dos órdenes; la primera etapa se fija solo si su óptimo está demostrado. Ambas comparten el presupuesto de tiempo.
- Estados honestos: `optimal`, `feasible` (plan comprobado sin prueba de óptimo), `infeasible` (el modelo es incompatible) y `unknown` (sin conclusión). `objective_bounds.primary/secondary` dan las cotas por objetivo.
- Rechaza ciclos de precedencia con un mensaje propio. Sin horizonte explícito, deriva uno suficiente para modelos válidos.
- Interfaz: editor de pedidos y recursos sin escribir JSON, cronograma con tabla equivalente (periodos sin disponibilidad rayados), comparación de objetivos, importación y exportación JSON de problemas y ejecuciones, historial y borradores locales que sobreviven a recargar.
- Exportaciones nativas: `POST /api/exports` conserva una instantánea y devuelve un enlace de descarga.

**Configurador** (`/configurator`)
- Catálogos con huecos (`slots`) obligatorios u opcionales y opciones con precio, cantidad, existencias y atributos; reglas `requires`, `excludes`, `compare` (atributo frente a atributo de otro hueco o a una constante, con factor y desplazamiento) y `sum`.
- `propagate`: qué opciones siguen siendo posibles en cada hueco, cuáles quedan obligadas y si las elecciones encajan.
- `complete`: rellena lo que falta con objetivo lexicográfico (`price`, `count` o cualquier atributo numérico, `min`/`max`) y devuelve la lista de materiales con precios exactos (enteros, decimales o fracciones `"p/q"`).
- `repair`: cambia el menor número de elecciones, varias a la vez si hace falta, y después optimiza; lista los cambios y los conflictos de partida.
- `explain`: conjuntos mínimos de elecciones incompatibles y la regla (o la falta de existencias) que los causa.
- `verify`: contrasta `complete` y `repair` con enumeración exhaustiva independiente (hasta 250.000 combinaciones).
- Estados `optimal`, `feasible`, `infeasible` e `inconclusive`. `seconds` es el presupuesto total de la operación; si una etapa posterior se queda sin tiempo se devuelve la mejor configuración ya encontrada como `feasible`. Incluye un ejemplo (`drive-kit`).

## Cómo ejecutarlo

Requiere Python 3.11 o superior.

```powershell
python -m venv .venv
.venv\Scripts\pip install -e .
.venv\Scripts\python -m dantzig          # http://127.0.0.1:5241/
```

`--port` cambia el puerto. `DANTZIG_DATA` selecciona otra carpeta de datos; por defecto se usa `data/`, ignorada por Git.

API del planificador: `GET /api/health`, `GET /api/example`, `POST /api/validate`, `POST /api/problems`, `POST /api/solve` (cuerpo `{"problem": ..., "seconds": 10}`), `GET /api/records`, `GET /api/records/{id}`, `POST /api/exports`, `GET /api/exports/{id}`. El configurador cuelga de `/api/configurator/*`. El esquema completo está en `/openapi.json`.

## Semántica del planificador

- `durations` indica recursos compatibles y duración positiva en cada uno.
- `release` es el instante mínimo de inicio; `after` referencia trabajos que deben terminar antes.
- `due` es una preferencia (el retraso positivo se multiplica por `weight`); `deadline` es obligatoria.
- `family_change` es tiempo transcurrido, no una preparación que ocupe a un operario; puede transcurrir durante un cierre.
- `unavailability: {"Torno": [{"start": 10, "end": 20}]}`: un pedido puede terminar a las 10 o empezar a las 20, pero no atravesar el cierre. Con horizonte explícito el calendario se recorta a él.
- No hay conversión de unidades: duraciones y fechas deben usar la misma unidad y el mismo origen temporal.
- No se modelan operarios compartidos, interrupciones, rutas ni inventario. La compatibilidad del configurador es lógica y no sustituye un cálculo físico ni de resistencia.

## Conexión con Faustus y Hoard Hub

`faustus-plugin.json` registra la app como plugin: el Hub la arranca bajo demanda con una comprobación de salud y adaptación de puerto mediante `--port`, y el panel común entrega a Faustus el borrador real del planificador y los resultados mostrados. El acceso de agentes es por MCP stdio (`python -m dantzig.mcp_server`, 16 herramientas); descubrir herramientas no arranca HTTP ni abre datos.

| Grupo | Herramientas |
| --- | --- |
| Planificación, lectura | `dantzig_example`, `dantzig_validate` (indicación de solo lectura, usables en modo Plan) |
| Planificación, cálculo y datos | `dantzig_solve`, `dantzig_save_problem`, `dantzig_export`, `dantzig_records`, `dantzig_record` |
| Configurador, catálogos | `dantzig_config_examples`, `dantzig_config_example`, `dantzig_config_save_catalog`, `dantzig_config_catalogs` |
| Configurador, cálculo | `dantzig_config_propagate`, `dantzig_config_complete`, `dantzig_config_repair`, `dantzig_config_explain`, `dantzig_config_verify` |

La app lleva además procedimientos de la biblioteca de skills de la familia para los agentes que se conectan (`constraint-scheduling`, `spec-driven-development`, `verification-loop`): aparecen en lo que el agente lee al conectarse, se leen con `skills_list` y `skill_read`, se buscan y asignan con `skills_library` y `skills_assign`, y se ofrecen como prompts. Se eligen en `/api/agent/skills/page` o en la pestaña Skills del Hub.

## Estructura del proyecto

| Ruta | Contenido |
| --- | --- |
| `dantzig/solver.py`, `models.py`, `service.py` | Modelo CP-SAT, esquemas y servicio del planificador |
| `dantzig/app.py`, `static/` | API HTTP e interfaz del planificador |
| `dantzig/configurator/` | Configurador: catálogo, reglas, solver, verificación, API, herramientas MCP e interfaz |
| `dantzig/mcp_server.py` | Servidor MCP |
| `dantzig/hoard_link/` | Código compartido de la familia Hoard |
| `tests/` | Pruebas del planificador, calendarios, configurador y MCP |
| `data/` | Base SQLite de problemas, catálogos y ejecuciones |

Pruebas: `pip install pytest httpx` y `python -m pytest -q`.

## Créditos

El motor es [OR-Tools](https://developers.google.com/optimization/scheduling/job_shop) (Apache 2.0, Google), ejecutado en proceso y no como CLI externa. Los ejemplos son datos inventados y no representan una fábrica real.
