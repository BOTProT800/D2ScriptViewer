<!-- Prompt para ejecutar el primer hito del plan. Pégalo en una sesión nueva de Claude Code abierta en D2ScriptViewer, o escribe: "Lee y ejecuta PROMPT_EJECUCION.md". -->

# Ejecutar PLAN_MAESTRO.md: primer hito (fases 0 a 4)

Vamos a ejecutar `PLAN_MAESTRO.md` hasta cerrar el primer hito: fases 0, 1, 2, 3 y 4.

Antes de escribir nada, lee completos `CLAUDE.md` y `PLAN_MAESTRO.md`. Fíjate sobre todo en
las secciones 3, 4, 5, 7, 8 y 10 y en el apéndice A. Esos dos archivos mandan: si algo de este
mensaje choca con ellos, para y pregúntame.

## Decisiones confirmadas

- Python ≥ 3.10, solo biblioteca estándar, interfaz con tkinter/ttk. Tengo Python 3.12.5 con Tk 8.6.
- Copia del original: `scripts.original.obsp`, junto al archivo que se guarda.
- Copias rotativas de la versión anterior: activadas, las últimas 5, en `.d2sv_backups\`.
- Licencia MIT, autor BOTProT800.

Lo primero: márcalas como decididas en la sección 12 del plan y en el estado de `CLAUDE.md`.

## Alcance

- Haz las fases 0 → 4 en orden. No pases a la siguiente sin cumplir todos los criterios
  "Hecho cuando" de la actual.
- Las fases 5 a 9 quedan fuera. En concreto, no intentes descubrir la función de hash ni editar
  scripts compilados (tipo 0): en este hito los scripts son de solo lectura.

## Cómo trabajar

- **Archivo real.** Para desarrollo y tests usa
  `C:\Users\vicen\Documents\Extractions\Darksiders\scripts.obsp` y define `D2SV_OBSP` con esa ruta.
  No escribas nunca en la carpeta del juego. Los archivos de trabajo van a `build\` (ignorado
  por git) o a carpetas temporales.
- **Tests de oro primero.** Empieza el núcleo por los tests que reproducen lo ya verificado en el
  apéndice A. No sigas mientras alguno falle:
  - la reconstrucción da el SHA-256 `B46DD3DA…`;
  - los 4 172 BOD salen idénticos al decodificar y recodificar;
  - las 3 690 cabeceras de script son coherentes.
- **Tests sintéticos para la CI**, sin datos del juego y construidos con el propio codificador.
  Deben cubrir los 11 tags y todos los modos y flags.
- **Núcleo y GUI separados.** El núcleo es `formats/`, `document`, `edits` y `saving`. La GUI no
  lee ni escribe bytes por su cuenta.
- **La GUI no se puede congelar.** La decodificación pesada, la búsqueda y el índice de
  referencias van en hilos que se comunican con ella mediante `queue`, y el árbol carga sus
  hijos de forma perezosa.
- Entre fases sigue sin esperar confirmación, salvo en los puntos de control.
- **Al cerrar cada fase:**
  1. Ejecuta todos los tests (`python -m unittest discover -s tests -v`). Desde la fase 1,
     ejecuta también `python -m d2scriptviewer verify` sobre el archivo real.
  2. Comprueba uno por uno los criterios "Hecho cuando".
  3. Añade una nota fechada al principio de `PLAN_MAESTRO.md` con lo hecho, las cifras medidas y
     cualquier desviación. Actualiza también `CLAUDE.md`: el estado y, cuando ya existan, los
     comandos reales en lugar de los previstos.
  4. Actualiza `CHANGELOG.md` en `[Unreleased]`.
  5. Haz un commit local de la fase, sin push.
  6. Dame un resumen breve: qué funciona, resultados de los tests, desviaciones y siguiente paso.

## Puntos de control: para y espérame

1. **Al terminar la fase 2.** Dime cómo abrir el visor y qué revisar. No empieces la fase 3 hasta
   que dé el visto bueno o pida cambios.
2. **Prueba en el juego (fase 4).** La hago yo con la propia herramienta. Tú, con el visor, elige
   dos ediciones candidatas: una que no cambie el tamaño del blob y otra que sí (por ejemplo, una
   cadena `05` más larga). Explícame qué editar, qué efecto esperar y cómo restaurar. Después
   espera mi resultado y regístralo en `research/PRUEBAS_EN_JUEGO.md`.
3. **Si algo contradice el apéndice A** o una decisión del plan, o tendrías que suponer qué
   significa un campo, pregúntame antes de seguir.

El hito queda cerrado cuando se cumplen todos los criterios de la sección 10 del plan.
