# Dantzig's Hoard

Dantzig permite tomar decisiones de producción bajo restricciones en el programa Hangar.

Usuarios: responsables de producción y asistentes conectados a Faustus, preparando herramientas para encargos empresariales. Trabajo: expresar trabajos/recursos/fechas, calcular un plan, entender su estado y conservar el problema con sus resultados.

Plataforma: web local Windows y MCP stdio. Datos locales. Arranque explícito. Sin LLM para calcular. Tiempos enteros, operaciones indivisibles, recursos alternativos de capacidad uno, precedencias y separación por cambio de familia.

Stack elegido para esta entrega a partir de los patrones de la familia: Python, CP-SAT integrado en proceso, FastAPI, SQLite y HTML nativo. La elección técnica sigue las necesidades de planificación y persistencia del encargo.

Éxito: restricciones verificadas independientemente; estados factible/óptimo/imposible/inconcluso; persistencia/exportación; misma lógica desde API/MCP/UI. Ninguna validación de maquinaria real inferida.
