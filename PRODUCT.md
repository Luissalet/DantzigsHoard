# Dantzig's Hoard

Luis autoriza construir las capacidades del programa Hangar (ecosystem1937). Primera entrega: decisiones de producción bajo restricciones, espacio dantzig, tarea1938.

Usuarios: Luis y modelos conectados a Faustus, preparando herramientas para encargos empresariales. Trabajo: expresar trabajos/recursos/fechas, calcular un plan, entender su estado y conservar el problema con sus resultados.

Plataforma: web local Windows y MCP stdio. Datos locales. Arranque explícito. Sin LLM para calcular. Tiempos enteros, operaciones indivisibles, recursos alternativos de capacidad uno, precedencias y separación por cambio de familia.

Stack elegido para esta entrega a partir de los patrones de la familia: Python, CP-SAT integrado en proceso, FastAPI, SQLite y HTML nativo. Decisión de implementación inferida del encargo; no preferencia explícita de Luis sobre un framework.

Éxito: restricciones verificadas independientemente; estados factible/óptimo/imposible/inconcluso; persistencia/exportación; misma lógica desde API/MCP/UI. Ninguna validación de maquinaria real inferida.
