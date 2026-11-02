# Dantzig's Hoard

Planifica trabajos sobre recursos alternativos con tiempos enteros, disponibilidad, precedencias, fechas deseadas, fechas límite obligatorias y separación por cambio de familia. Conserva problemas y resultados en SQLite, con el mismo servicio desde HTTP y cinco herramientas MCP.

Estado: primera entrega de motor/API/MCP en revisión, tarea1938 del espacio `dantzig`; programa ecosystem1937. No integrado ni anunciado como aplicación instalada. La entrada web actual es la documentación interactiva `/docs`; la interfaz de pedidos y Gantt está pendiente. El arranque es explícito y no consulta modelos.

## Uso

Python3.11 o posterior. Crear un entorno propio e instalar `pip install -e .`. Ejecutar `python -m dantzig` y abrir http://127.0.0.1:5241/docs. `--port` cambia el puerto. `DANTZIG_DATA` selecciona una carpeta de datos independiente. Por defecto usa `data/` del repositorio, ignorada por Git. MCP: `python -m dantzig.mcp_server`. Descubrir herramientas no arranca HTTP ni abre datos.

API: `GET /api/example`, `POST /api/problems`, `POST /api/solve`, `GET /api/records`, `GET /api/records/{id}`. La última ruta permite exportar entradas y resultados completos. Un problema guardado es inmutable; guardar una variación crea otro ID. Cada cálculo conserva su propia entrada.

El cuerpo de solve es `{ "problem": <problema de /api/example>, "seconds": 10 }`. El esquema completo está en `/openapi.json`. No hay conversión automática de unidades: todas las duraciones/fechas deben usar la misma unidad declarada y el mismo origen temporal.

## Semántica

- `durations` indica recursos compatibles y duración positiva en cada uno. Cada trabajo se asigna exactamente a uno, sin interrupciones.
- `release` es el instante mínimo de inicio; `after` referencia trabajos que deben terminar antes.
- `due` es una preferencia: el retraso positivo se multiplica por `weight`. `deadline` es obligatoria.
- `family_change` es la separación mínima entre trabajos consecutivos de familias distintas en el mismo recurso. No representa una operación de preparación que ocupe a un operario ni un calendario de mantenimiento.
- `horizon` opcional restringe la finalización. Si se omite, se deriva una cota serial suficiente para modelos válidos sin ciclos. Una conclusión de imposibilidad se refiere al modelo y a su horizonte.
- Objetivo: retraso ponderado primero y finalización después, o el orden inverso. La suma escalar interna conserva esa prioridad mediante cotas enteras; no es una suma de pesos arbitrarios.
- `optimal` acredita óptimo del modelo; `feasible` conserva un plan comprobado sin prueba de óptimo; `infeasible` acredita incompatibilidad del modelo; `unknown` no acredita imposibilidad. `objective_bound` es una cota del objetivo escalar interno, no minutos de retraso.

Cada solución se comprueba fuera del solver: presencia de todos los trabajos, recurso/duración, disponibilidad, precedencias, fechas obligatorias, horizonte, exclusión y separación de familias. No se han modelado calendarios, operarios compartidos, interrupciones, rutas ni inventario.

## Verificación

Instalar `pytest httpx` y ejecutar `python -m pytest -q`. Primera entrega:21 pruebas, incluidos12 problemas inventados comparados con enumeración independiente, caso investigado de6pedidos, imposibilidad, precedencias, entrada inválida, persistencia/API y cliente MCP stdio real. Navegador Brave: petición POST real de2pedidos devuelve óptimo, precedencia y retraso0. Los casos no representan una fábrica real.

El motor usa OR-Tools9.15 en proceso, biblioteca Apache2.0 de Google; no ejecuta una CLI externa. Procedencia: https://developers.google.com/optimization/scheduling/job_shop . Las dependencias y sus licencias conservan su identidad; este repositorio define sus modelos, servicio, datos y contrato de herramientas.
