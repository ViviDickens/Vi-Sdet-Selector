# Reporte de estado — Vi-Sdet-Selector

**Fecha:** 2026-07-27
**Rama analizada:** `claude/project-status-report-auceh5` (sincronizada con `main`)
**Último commit:** `1d58d3f` — *Fix docker paths, clean up ML leftovers, rewrite README* (2026-07-19)

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

### 6. Dependencias Python muy atrasadas

| Paquete | Fijado | Actual |
|---|---|---|
| `anthropic` | 0.34.2 | 0.120.0 |
| `deepeval` | 1.1.9 | 4.1.4 |
| `fastapi` | 0.111.0 | 0.140.2 |

`deepeval` es el más delicado: tres majors de diferencia, así que la API que
usa `tests/test_deepeval_reasoning.py` (`assert_test`, `LLMTestCase`,
`FaithfulnessMetric`) casi seguro cambió. Ese test hoy se salta por falta de
keys, así que la incompatibilidad no se está manifestando — pero aparecerá en
cuanto se configuren.

### 7. La imagen de la API arrastra la capa opcional

`Dockerfile/Dockerfile.api:8` instala todo `requirements.txt`, lo que mete
`deepeval` y `pytest` en la imagen que sirve `/predict`. La capa de IA es
opcional por diseño; separar `requirements-dev.txt` (o extras) achicaría
bastante la imagen.

### 8. Detalles menores

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
3. **`@types/node` + script `typecheck`** — vuelve real el `strict: true`.
4. **Commitear el lockfile** y pasar el Dockerfile a `npm ci`.
5. **Actualizar modelo y dependencias**, empezando por `deepeval` (validar que
   el test siga compilando contra la API 4.x).
