# Reporte de estado — Vi-Sdet-Selector

**Fecha:** 2026-07-27
**Rama analizada:** `claude/project-status-report-auceh5` (sincronizada con `main`)
**Último commit:** `1d58d3f` — *Fix docker paths, clean up ML leftovers, rewrite README* (2026-07-19)

> **Actualización (2026-07-27):** los 10 hallazgos de abajo ya están
> corregidos. Ver la sección [Resolución](#resolución) al final. El cuerpo del
> reporte se deja como quedó en el diagnóstico original.

---

## Resumen

Proyecto pequeño y coherente (~516 líneas de código propio). El pivote de un
clasificador scikit-learn a un motor de reglas determinista está completo y
bien documentado: no quedan restos del enfoque anterior más allá de los
placeholders `model/` y `data/`, que explican su propia existencia.

Lo que hay funciona. Lo que falta es sobre todo infraestructura: no hay CI, no
hay lockfile, el TypeScript no compila bajo `tsc`, y las dependencias llevan
entre uno y dos años sin actualizarse.

---

## Verificado en esta sesión

| Comprobación | Resultado |
|---|---|
| `pytest tests/` | **6 passed, 1 skipped** en 0.10s |
| `GET /health` | 200 `{"status":"ok"}` |
| `POST /predict` | 200, salida correcta en las 4 ramas de prioridad |
| `POST /predict/explain` sin `ANTHROPIC_API_KEY` | 503 con mensaje claro |
| `POST /predict` con body inválido | 422 (validación Pydantic) |
| SDK → API (round trip real, sin browser) | Las 4 estrategias resuelven bien |
| Imagen `mcr.microsoft.com/playwright:v1.47.2-focal` | El tag existe en el registry |
| `npx tsc --noEmit` | **falla** (ver hallazgo 2) |

**No verificable en este entorno** (limitación del sandbox, no del proyecto):

- El E2E de `saucedemo.spec.ts` no corre: el proxy de salida bloquea
  `saucedemo.com` (`ERR_TUNNEL_CONNECTION_FAILED`). La lógica del SDK sí se
  validó llamando al API directamente.
- El test de DeepEval se salta correctamente por falta de `ANTHROPIC_API_KEY`
  y `OPENAI_API_KEY`.

---

## Hallazgos

### 1. Falsos positivos en la detección de clases dinámicas — *impacta la recomendación*

`server/rules.py:24`

```python
re.compile(r"^[a-zA-Z]+-[a-f0-9]{5,}$", re.IGNORECASE),  # generic hash suffix
```

El sufijo se valida contra `[a-f0-9]`, así que cualquier palabra formada solo
con las letras `a`–`f` cuenta como hash. Comprobado:

```
btn-added      dynamic=True    ← falso positivo
user-facade    dynamic=True    ← falso positivo
nav-decade     dynamic=True    ← falso positivo
submit-button  dynamic=False   ← correcto
```

No es cosmético: un elemento con `id="btn-added"` deja de calificar como id
estático y la recomendación baja de `css` (confianza 0.75) a `xpath` (0.40).

Arreglo probable: exigir al menos un dígito en el sufijo, o subir el mínimo de
longitud (`{6,}` / `{8,}`) para que un hash real siga matcheando pero una
palabra en inglés no.

### 2. El SDK de TypeScript no compila

```
$ npx tsc --noEmit
predict.ts(32,17): error TS2580: Cannot find name 'process'.
```

Falta `@types/node` en `devDependencies`. En runtime no se nota porque
Playwright transpila sin hacer typecheck, así que el `"strict": true` del
`tsconfig.json` hoy no lo está verificando nadie. Tampoco hay script
`typecheck` en `package.json`.

### 3. No hay CI

No existe `.github/`. Es el primer punto del roadmap del README y sigue
pendiente. Los 6 tests deterministas corren en 0.10s sin API keys — es la
mejora con mejor relación esfuerzo/beneficio del repo.

### 4. No hay lockfile commiteado

`playwright-sdk/package-lock.json` no está versionado, y `Dockerfile.playwright`
hace `npm install` (no `npm ci`). Las builds no son reproducibles: dos personas
que clonen el repo pueden terminar con árboles de dependencias distintos.

### 5. Modelo de Claude desactualizado

`server/reasoning.py:41` fija `claude-3-5-haiku-20241022`, dos generaciones
atrás. El equivalente actual es `claude-haiku-4-5-20251001`.

### 6. `deepeval==1.1.9` está roto: no se puede ni importar

Este es el hallazgo más serio después del 1. Verificado en un venv limpio:

```
$ pip install deepeval==1.1.9      # instala sin error
$ python -c "import deepeval"
  File ".../deepeval/models/gpt_model.py", line 7, in <module>
    from langchain.schema import HumanMessage
ModuleNotFoundError: No module named 'langchain.schema'
```

La causa: `deepeval` 1.1.9 declara `langchain`, `langchain-core` y
`langchain-openai` **sin ninguna cota de versión**, así que pip resuelve a
`langchain` 1.3.14, donde `langchain.schema` ya no existe. No es que el pin sea
viejo: es que el pin ya no es instalable de forma utilizable.

Hoy no se nota porque `pytestmark` salta el test sin API keys y los imports de
deepeval están dentro de la función de test. En cuanto se configuren
`ANTHROPIC_API_KEY` y `OPENAI_API_KEY`, el test no falla por métricas — muere
con `ModuleNotFoundError` en su primera línea.

Dos salidas, ambas comprobadas:

- **Parche mínimo:** agregar `langchain==0.2.16`, `langchain-core<0.3` y
  `langchain-openai<0.2` a `requirements.txt`. Con eso los imports funcionan.
- **Subir a `deepeval` 4.1.4** — y acá la buena noticia: **el código del test no
  hay que tocarlo**. Verifiqué contra 4.1.4 que siguen existiendo `assert_test`,
  `LLMTestCase(input=, actual_output=, retrieval_context=)`,
  `FaithfulnessMetric(threshold=)` y `AnswerRelevancyMetric(threshold=)`. La
  API que usa el test sobrevivió los tres majors intactos.

### 7. El `retrieval_context` no coincide con lo que ve el generador

`tests/test_deepeval_reasoning.py:64` pasa solo `prediction.reasoning` como
`retrieval_context`, pero `_build_prompt` le da al modelo **cinco** hechos:

```
retrieval_context (lo que juzga DeepEval):
  ['element has stable test id', 'dynamic class detected', 'xpath likely brittle']

contexto real del generador:
  Recommended strategy: data-testid      ← no está en retrieval_context
  Alternative strategy: aria-label       ← no está en retrieval_context
  + los tres signals de arriba
```

La explicación necesariamente va a decir "usá data-testid" y "aria-label como
alternativa", y ninguna de las dos afirmaciones está respaldada por el contexto
declarado. Faithfulness termina midiendo contra un contexto más angosto que el
real, lo que le mete ruido al score.

Peor: como `"xpath likely brittle"` sí está en el contexto, si el modelo
alucinara y recomendara XPath, la métrica no tendría con qué contradecirlo. El
test no puede detectar precisamente la alucinación que más importa — que
recomiende la estrategia equivocada.

Arreglo: incluir la recomendación y la alternativa en `retrieval_context`, y
agregar un assert plano de que la explicación menciona
`prediction.recommended_strategy`.

### 8. Otras dependencias atrasadas

| Paquete | Fijado | Actual |
|---|---|---|
| `anthropic` | 0.34.2 | 0.120.0 |
| `fastapi` | 0.111.0 | 0.140.2 |

### 9. La imagen de la API arrastra la capa opcional

`Dockerfile/Dockerfile.api:8` instala todo `requirements.txt`, lo que mete
`deepeval` y `pytest` en la imagen que sirve `/predict`. La capa de IA es
opcional por diseño; separar `requirements-dev.txt` (o extras) achicaría
bastante la imagen.

### 10. Detalles menores

- `docker-compose.yml:1` — la clave `version: "3.9"` está obsoleta; Compose v2
  emite un warning al leerla.
- `playwright-sdk/package.json` declara `"type": "module"` mientras
  `tsconfig.json` usa `"module": "commonjs"`. Playwright lo tolera, pero es
  inconsistente.
- En el fallback a xpath, `alternative` siempre es `"css"` aunque no haya id ni
  clase estable donde anclar; `getLocator` termina devolviendo `element.tag`,
  un selector que matchea todos los elementos de ese tag.

---

## Cobertura de tests

Los 6 tests cubren la ruta feliz de cada rama de prioridad del motor de reglas
más dos casos de borde (id dinámico no confiable, confianza según xpath
frágil). Buen nivel para el tamaño del engine.

Sin cubrir:

- Los endpoints HTTP. Los tests llaman a `predict_strategy()` directamente;
  `app.py` (serialización, el 503, el 422) no se ejercita.
- El SDK de TypeScript. `predict.ts` solo se ejecuta a través del E2E, que
  depende de un sitio externo.

---

## Prioridades sugeridas

1. **CI en GitHub Actions** — `pytest tests/test_rules.py` en cada push.
   Cierra el punto 1 del roadmap y da red de seguridad para todo lo demás.
2. **Arreglar el regex del hallazgo 1** — es el único bug que cambia una
   recomendación, y ya hay tests donde encajarlo.
3. **Destrabar DeepEval (hallazgo 6)** — subir a `deepeval` 4.1.4. El código del
   test no se toca; ya verifiqué que su API sigue igual. Sin esto, la parte
   "AI Quality" del proyecto no corre aunque se configuren las keys.
4. **Alinear el `retrieval_context` (hallazgo 7)** — sin esto el test corre pero
   no mide lo que debería.
5. **`@types/node` + script `typecheck`** — vuelve real el `strict: true`.
6. **Commitear el lockfile** y pasar el Dockerfile a `npm ci`.
7. **Actualizar el modelo de Claude y el resto de las dependencias.**

---

## Resolución

Todo lo de arriba quedó corregido y verificado corriendo, no solo cambiado.

| # | Hallazgo | Qué se hizo |
|---|---|---|
| 1 | Falsos positivos en clases dinámicas | El sufijo del patrón genérico ahora exige al menos un dígito (`server/rules.py`). 8 tests nuevos, incluido un guard de regresión para `id="btn-added"` |
| 2 | El SDK no compila | `@types/node` + `"types": ["node"]`, y script `npm run typecheck`. Pasa limpio |
| 3 | Sin CI | `.github/workflows/ci.yml`: pytest + typecheck del SDK en cada push y PR |
| 4 | Sin lockfile | `package-lock.json` commiteado; `Dockerfile.playwright` pasa a `npm ci` |
| 5 | Modelo desactualizado | `claude-haiku-4-5-20251001` |
| 6 | `deepeval` roto | Subido a 4.1.4. Verificado: la suite colecta y corre bajo 4.x sin tocar el código del test |
| 7 | `retrieval_context` incompleto | Ahora incluye la estrategia recomendada y la alternativa, más un assert plano de que la explicación nombra la estrategia |
| 8 | Deps atrasadas | `fastapi` 0.140.2, `uvicorn` 0.51.0, `pydantic` 2.13.4, `anthropic` 0.120.0, `pytest` 9.1.1 |
| 9 | Imagen de API inflada | `requirements.txt` (runtime) separado de `requirements-dev.txt` (pytest, httpx, deepeval). La imagen ya no arrastra langchain |
| 10 | Detalles menores | Sacada la clave `version` obsoleta de compose; `tsconfig` alineado con `"type": "module"`; el fallback a xpath ya no ofrece `css` cuando no hay dónde anclarlo; `getLocator` usa clases estáticas antes de caer al tag |

**Cobertura:** de 6 tests a 28 (+1 skipped). Se sumó `tests/test_api.py`, que
cubre el nivel HTTP que antes no se tocaba: las cuatro ramas de prioridad, el
422 de validación y el 503 de `/predict/explain` sin key.

```
$ python -m pytest tests/ -q
28 passed, 1 skipped in 0.49s

$ npm run typecheck        # (playwright-sdk/)
$ tsc --noEmit             # sin errores
```

**Lo que sigue sin verificarse acá:** el E2E de Playwright (el proxy del sandbox
bloquea `saucedemo.com`) y las métricas de DeepEval en sí, que necesitan
`ANTHROPIC_API_KEY` y `OPENAI_API_KEY`. Lo que sí se verificó del lado DeepEval
es que la suite ahora importa, colecta y corre bajo 4.1.4 — que era el bloqueo.
