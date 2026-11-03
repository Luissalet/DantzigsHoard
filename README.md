# Dantzig's Hoard

Planifica trabajos sobre recursos alternativos con tiempos enteros, disponibilidad, precedencias, fechas deseadas, fechas límite obligatorias y separación por cambio de familia. Conserva problemas y resultados en SQLite, con el mismo servicio desde HTTP y siete herramientas MCP de planificación.

Estado: motor/API/MCP inicial integrado con aprobación de1938r1. El configurador1939r3 está aprobado e integrado en Main (7c46280). El candidato1938r3 incorpora editor de pedidos, recursos, cronogramas, comparación, importación/exportación e historial, con el tema oscuro común y el icono de familia corregido. La revisión1938r2 aprobó el funcionamiento y pidió corregir el tema visual; la nueva entrega necesita revisión e integración. Copilot común1941 aprobado, pendiente de integrar junto al planificador. Registro Hub pendiente. Arranque explícito, sin consultas a modelos.

## Uso

Python3.11 o posterior. Crear un entorno propio e instalar `pip install -e .`. Ejecutar `python -m dantzig` y abrir http://127.0.0.1:5241/. `--port` cambia el puerto. `DANTZIG_DATA` selecciona una carpeta de datos independiente. Por defecto usa `data/` del repositorio, ignorada por Git. MCP: `python -m dantzig.mcp_server`. Descubrir herramientas no arranca HTTP ni abre datos.

API: `POST /api/validate`, `GET /api/example`, `POST /api/problems`, `POST /api/solve`, `GET /api/records`, `GET /api/records/{id}`. La última ruta permite exportar entradas y resultados completos. Un problema guardado es inmutable; guardar una variación crea otro ID. Cada cálculo conserva su propia entrada.

El cuerpo de solve es `{ "problem": <problema de /api/example>, "seconds": 10 }`. El esquema completo está en `/openapi.json`. No hay conversión automática de unidades: todas las duraciones/fechas deben usar la misma unidad declarada y el mismo origen temporal.

## Semántica

- `durations` indica recursos compatibles y duración positiva en cada uno. Cada trabajo se asigna exactamente a uno, sin interrupciones.
- `release` es el instante mínimo de inicio; `after` referencia trabajos que deben terminar antes.
- `due` es una preferencia: el retraso positivo se multiplica por `weight`. `deadline` es obligatoria.
- `family_change` es la separación mínima entre trabajos consecutivos de familias distintas en el mismo recurso. No representa una operación de preparación que ocupe a un operario ni un calendario de mantenimiento.
- `horizon` opcional restringe la finalización. Si se omite, se deriva una cota serial suficiente para modelos válidos sin ciclos. Una conclusión de imposibilidad se refiere al modelo y a su horizonte.
- Objetivo: retraso ponderado primero y finalización después, o el orden inverso. Se resuelven dos etapas: se fija el primer objetivo sólo si su óptimo está demostrado y se optimiza después el segundo. Ambas comparten el presupuesto temporal; agotar la segunda conserva el plan de la primera como factible.
- `optimal` acredita óptimo del modelo; `feasible` conserva un plan comprobado sin prueba de óptimo; `infeasible` acredita incompatibilidad del modelo; `unknown` no acredita imposibilidad. `objective_bounds.primary/secondary` contienen las cotas por objetivo en ese orden. El antiguo `objective_bound` permanece como null para compatibilidad; ya no se utiliza la combinación escalada. Los ciclos de precedencia se rechazan con un mensaje propio.

Cada solución se comprueba fuera del solver: presencia de todos los trabajos, recurso/duración, disponibilidad, precedencias, fechas obligatorias, horizonte, exclusión y separación de familias. No se han modelado calendarios, operarios compartidos, interrupciones, rutas ni inventario.

## Verificación

Instalar `pytest httpx` y ejecutar `python -m pytest -q`. Candidato compuesto:92 pruebas (23 planificación/exportación y69 configurador). Planificación incluye12 problemas inventados comparados con enumeración independiente en ambos órdenes lexicográficos, regresión de horizonte grande y caso investigado de6pedidos, imposibilidad, precedencias, entrada inválida, persistencia/API y cliente MCP stdio real. La revisión independiente1938r2 añadió300 casos de planificación sin discrepancias. Los casos no representan una fábrica real.

El motor usa OR-Tools9.15 en proceso, biblioteca Apache2.0 de Google; no ejecuta una CLI externa. Procedencia: https://developers.google.com/optimization/scheduling/job_shop . Las dependencias y sus licencias conservan su identidad; este repositorio define sus modelos, servicio, datos y contrato de herramientas.

## Configurador

Segundo módulo (tarea1939 del espacio `dantzig`): catálogos de componentes con compatibilidades cruzadas. Página `/configurator` (servida por el propio módulo desde `dantzig/configurator/static`), API `/api/configurator/*`, nueve herramientas MCP `dantzig_config_*`. Mismo motor CP-SAT en proceso y misma base SQLite (registros `catalog` y `config_run`).

- Catálogo: huecos (`slots`) obligatorios u opcionales, opciones con precio, cantidad, existencias y atributos; reglas `requires`, `excludes`, `compare` (atributo frente a atributo de otro hueco o constante, con factor y desplazamiento) y `sum` (suma de un atributo frente a una constante o al atributo de otro hueco). Ejemplo incluido: `drive-kit`, kit de accionamiento inventado.
- `propagate`: para cada hueco, qué opciones siguen siendo posibles con el resto de elecciones, cuáles quedan obligadas y si las elecciones encajan juntas.
- `complete`: rellena lo que falta con objetivo lexicográfico (`price`, `count` o cualquier atributo numérico, `min`/`max`) y devuelve lista de materiales.
- `repair`: cambia el menor número de elecciones (varias a la vez si hace falta) y después optimiza; lista los cambios y los conflictos de partida.
- `explain`: todos los conjuntos mínimos de elecciones incompatibles con las reglas mínimas (o la falta de existencias) que los causan; `exhaustive` indica si puede haber más.
- `verify`: contrasta `complete` y `repair` con enumeración exhaustiva independiente (hasta 250.000 combinaciones).

Estados: `optimal`, `feasible` (válido sin prueba de óptimo), `infeasible` (demostrado imposible), `inconclusive` (sin respuesta en el tiempo dado). `seconds` es el presupuesto total de la operación (sin tope fijo): cada paso usa lo que queda; en `complete`/`repair` cada etapa lexicográfica recibe una parte del resto y solo fija un óptimo demostrado, de modo que si una etapa posterior se queda sin tiempo se devuelve la mejor configuración ya encontrada como `feasible`. Precios y números del catálogo se guardan exactos: enteros, decimales exactos o fracciones `"p/q"`. La compatibilidad es lógica: no sustituye un cálculo físico ni de resistencia.

Pruebas: `tests/test_configurator.py`, 69 casos; 40 catálogos aleatorios contrastados con enumeración en comprobación, completado, reparación y explicación; conflictos mínimos comprobados exhaustivamente; caso que exige cambiar dos elecciones a la vez; API y MCP stdio real. Revisión1939r3 aprobada después de contrastar otros20 catálogos y540 combinaciones; en Brave, reparación de dos elecciones incompatibles y lista de materiales de475EUR, con enumeración de6075 combinaciones.

## Interfaz de planificación

La página inicial permite editar recursos y pedidos sin escribir JSON, calcular ambos objetivos, consultar cronograma y tabla equivalente, guardar problemas inmutables y abrir ejecuciones con su entrada original. Importa documentos de problema o de una ejecución; exporta problemas y resultados JSON. Los borradores locales incompletos se conservan al recargar. Modificar el problema invalida el resultado mostrado; una respuesta tardía no sustituye un borrador posterior. El historial de planificación filtra sus propios tipos de documento.

Brave QA de la segunda entrega: comparación4/19 frente5/16, guardado y recuperación Unicode, resultado invalidado al editar, imposibilidad por límite obligatorio0 y conservación de nombre vacío al recargar. La prueba detectó y corrigió el borrado de borradores incompletos. Inspección a390px sin desbordamiento global, tabla con desplazamiento propio. La comprobación automática de estilo funcionó degradada por falta de parsers; no acredita contraste ni auditoría completa.

## Integración de familia (candidato1941)

Tema oscuro canónico, paleta jade y nuevo icono basado en las referencias reales Coase/Vitruvius, conservando la silueta del dragón común. El primer icono generado fue rechazado por Luis y sustituido; no es una alternativa vigente. Procedencia y prompt completos en E:/Development/IA/Research/Hangar-2026-11-02/ICONO-DANTZIG-V2.json. Paleta común en revisión separada hoardlink1944. Vista real de390px comprobada con este tema.

Biblioteca HoardLink canónica incorporada mediante sync_vendored.py,112ficheros comprobados byte a byte, licencia y VENDORED.txt conservados. El copiloto comparte panel, conversaciones y servicio de Faustus; el botón usa el icono canónico. El contexto del planificador aporta el borrador real y los resultados mostrados, y una actualización del asistente refresca el historial sin sustituir el editor.

El manifiesto incluye arranque explícito desdeHub, comprobación de salud y adaptación de puerto mediante --port. Leído con el parser real del Hub: launchable=true. Aún no registrado en el Hub: se hará tras revisión. agent_contract=false indica acceso por MCPstdio; no se anuncian rutasHTTP de agente que no existen. /api/copilot/info responde200 y el panel abre enBrave, sin enviar un turno al modelo. No se acredita inferencia con herramientas desde ese panel hasta registrar la conexión.

## Exportación nativa (candidato1942)

POST /api/exports conserva una instantánea JSON y devuelve un enlace GET /api/exports/{id} con Content-Disposition attachment. La UI ofrece ese enlace visible; ya no utiliza direcciones Blob. dantzig_export realiza la misma preparación por MCP sin iniciar servidor. Los documentos pueden recuperarse mediante dantzig_record; el historial de planificación conserva sus tipos problem/run y no mezcla exportaciones o catálogos. Las pruebas HTTP verifican bytes semánticos, Unicode, enteros grandes, cabecera y recuperación tras reabrir.

Selector de archivos de Brave: fixture propia importada y validada correctamente. La captura del evento download no pudo certificar el guardado en disco. El acceso al gestor interno de descargas fue rechazado por la política del navegador y no se reintentó por otra superficie; no confundir la preparación y respuesta HTTP con un archivo verificado en la carpeta de descargas.
