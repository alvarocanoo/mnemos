# Escribí el suite de evals antes de escribir el sistema de memoria

> Diseñar `mnemos-bench-v1` primero acabó siendo la decisión de diseño más barata del proyecto.

La primera vez que me senté a empezar `mnemos`, tenía un schema de Postgres medio escrito en una ventana, un mockup del dashboard en Next.js en otra, y un plan vago de "ya añadiré los evals luego". Pasé casi toda una tarde decidiendo qué modelo de embeddings poner por defecto antes de pillarme: estaba a punto de gastar tres semanas construyendo un sistema cuya calidad iba a juzgar **a ojo** con un ejemplo de juguete de cinco memorias.

Cerré todas las pestañas menos el archivo JSONL en blanco.

Este post va de por qué arranqué por el suite de evals, cómo es `mnemos-bench-v1` y las decisiones concretas que habría tomado mal si hubiera dejado el eval para después.

## Qué es `mnemos` en un párrafo

`mnemos` es un sistema de memoria para agentes: un servicio HTTP que guarda trozos de texto cortos ("memorias") y deja que un agente las recupere después. Lo interesante está en el retrieval híbrido (BM25 + embeddings densos + fusión RRF), la detección de contradicciones entre memorias, el decay temporal para que los facts viejos pierdan peso, y la eviction ponderada por importancia para que la base de datos no crezca infinita. Todo corre en local con `docker compose up`. Código en [github.com/alvarocanoo/mnemos](https://github.com/alvarocanoo/mnemos).

El post no va del sistema. Va del eval suite que escribí primero, sobre un `*.jsonl` en blanco, antes de que ninguna otra pieza existiera.

## Por qué eval-first, concretamente

Hay una versión moralista de "test-first" que suena a póster de bootcamp. No me refiero a eso. Me refiero a tres cosas específicas que he notado probando ambos caminos en proyectos más pequeños:

**1. El eval te fuerza a fijar el contrato.** En el momento en que escribes un solo caso de test del tipo "el agente pregunta esto, el sistema de memoria devuelve estas memorias", tienes que comprometerte a cómo es una memoria (¿un string?, ¿estructurada?), qué es una query (¿texto?, ¿embedding?), qué cuenta como respuesta "correcta" (¿un gold id?, ¿overlap del top-k?) y qué devuelve el sistema (¿una lista de ids?, ¿hits con scores?). Esas cuatro decisiones las vas a tomar igual, implícitamente. Escribirlas como caso de test las saca a la superficie *antes* de tener mil líneas de código que asumen la forma equivocada.

**2. El eval hace visible el scope creep.** Cuando tienes un objetivo numérico ("recall@10 ≥ 0.80 sobre 75 casos") es difícil mentirte sobre si una feature nueva de verdad ayuda. Sin objetivo, toda feature parece buena idea — porque cualquier cosa aislada parece buena idea.

**3. El eval es el primer artefacto que un reviewer lee.** Si alguien clona tu repo y ejecuta `make eval`, su primera interacción con tu trabajo es un número contra un dataset. Nada más que hayas escrito se lee hasta que decide que esa interacción fue honesta.

## Cómo es `mnemos-bench-v1` por dentro

El benchmark son 75 casos en cinco tipos de tarea. Un archivo por tipo, todos concatenados en un `mnemos_bench_v1.jsonl`. Cada línea es un objeto JSON.

El tipo más simple es `single_hop_recall`:

```json
{
  "id": "shr_001",
  "task_type": "single_hop_recall",
  "version": "seed_v0",
  "memories": [
    {"content": "The Q3 marketing budget is 450,000 EUR for digital channels.", "importance": 3},
    {"content": "The product team meets every Tuesday at 10am CET.", "importance": 2},
    {"content": "Our primary CRM is Pipedrive and the dashboard owner is Marta.", "importance": 2},
    {"content": "Office address: Calle Mayor 12, Madrid 28013.", "importance": 1},
    {"content": "All employee laptops must be encrypted with FileVault or BitLocker.", "importance": 3}
  ],
  "query": "How much money do we have for Q3 marketing?",
  "gold": {"memory_indices": [0]}
}
```

Se ingestan unas pocas memorias, se manda la query, y la métrica comprueba si la memoria correcta apareció en el top-k. `recall@k = |gold ∩ top_k| / |gold|`. No hay magia, pero la estructura fuerza cinco decisiones específicas que no puedes evitar:

- Las memorias llevan `importance` (1, 2, 3). ¿Por qué? Porque si esperas a añadirlo después, todos los módulos downstream ya asumen memorias uniformes y el refactor duele. La eviction y el decay temporal ambos lo necesitan desde el día uno.
- El gold son `memory_indices` (enteros que indexan el `memories[]` del propio caso), no UUIDs. El runner ingesta, recibe los UUIDs reales y traduce. Esto hace el dataset portable entre runs — sin UUIDs hardcodeados.
- Los casos se aíslan por `user_id = f"bench_{case.id}"`. La llamada de retrieval filtra por `user_id`, así que las memorias de un caso no se filtran al top-k de otro. Eso dejó el runner sin estado: sin resets per-caso de la base de datos, sin flakiness.

Compara con `abstention`:

```json
{
  "id": "abs_001",
  "task_type": "abstention",
  "memories": [
    {"content": "Our primary CRM is Pipedrive.", "importance": 2},
    {"content": "GDPR DPO is Carla Morena.", "importance": 3},
    {"content": "Office wifi password rotates quarterly.", "importance": 1}
  ],
  "query": "What is our email marketing platform?",
  "gold": {"memory_indices": [], "expected_empty": true}
}
```

El schema es *exactamente la misma forma* — mismo `memories[]`, mismo `gold.memory_indices` — y `gold.memory_indices = []` es la verdad: no se debe devolver nada. La métrica es "¿el sistema devolvió lista vacía?". El truco es que el sistema tiene que *querer* abstenerse, porque por defecto una búsqueda vectorial siempre va a devolver *algo*. Añadí un parámetro opcional `score_threshold` al endpoint de search específicamente para que el agente pueda pedir "dame hits, pero solo si pasan este listón". Rellenar ese hueco fue visible *gracias al caso de abstention*; sin él habría enviado un sistema que devuelve con confianza el match más cercano y ruidoso a preguntas que no sabe contestar.

Los casos `temporal_update` fuerzan el mismo tipo de presión de diseño. El pool de memorias tiene tanto una memoria `current` como una `superseded` para el mismo fact, más distractores. La query pide ese fact. La métrica es si la memoria *current* rankea por encima de la *superseded* en el top-5. Eso requirió que el runner pudiera inyectar `created_at` al ingestar, lo cual se convirtió en un campo opcional explícito en `MemoryWrite`. En producción este campo se queda en `None` y gana el default de la base de datos; en eval permite simular memorias envejecidas.

`contradiction` tiene su propia forma — pares `memory_a` / `memory_b` con un verdict gold en `{contradicts, supersedes, independent, paraphrase}` — porque prueba un subsistema completamente distinto.

`multi_session_reasoning` reutiliza la forma de `single_hop_recall` pero `gold.memory_indices` tiene 1–2 entradas y la query está construida para que no se pueda responder desde una sola memoria.

Ese es todo el schema. ~75 líneas de JSON describen lo que el sistema tiene que hacer.

## La restricción de reproducibilidad

Una de las pocas líneas rojas que me puse al inicio: el eval tiene que correr desde un clon limpio con un solo comando. No "instala estas tools, configura este env, puebla la base de datos". No un notebook. Un comando.

La razón es egoísta. El artefacto al que quiero apuntar a un hiring manager *no* es un screenshot de un leaderboard. Es la experiencia de:

```powershell
git clone https://github.com/alvarocanoo/mnemos.git
cd mnemos
make sync
make up
make eval-compare
Get-Content leaderboard.md
```

Esa secuencia termina con una tabla markdown apendida a `leaderboard.md`. Si cualquier paso requiere cerebro, el artefacto está roto.

Para que eso funcione, cada fila del eval registra el git SHA del commit en el que corrió, el id del modelo de embeddings (pinned en env), el id del modelo del LLM judge cuando aplica, el nombre del dataset y el número de casos. Una fila del leaderboard que no registra qué la produjo es una fila en la que no confío.

## Lo que no sobrevivió al diseño eval-first

Sección honesta. Diseñar el eval primero recortó dos ideas que me hacían ilusión.

La primera: una **base de datos de grafos para entidades**. Tenía planeado pasar cada memoria por un extractor de entidades, escribir las entidades en Neo4j y usar el grafo para retrieval. El eval me forzó a preguntar: ¿para qué caso de test es esto? `single_hop` no lo necesita. `multi_session_reasoning` va más de enlace semántico que de overlap de entidades. Incluso `contradiction` se beneficia más de un LLM judge que de un traversal del grafo. Así que me cargué el grafo. Las entidades viven en una tabla de Postgres — joineadas cuando hace falta, sin base de datos de grafos que defender en entrevista.

La segunda: un **algoritmo de fusión a medida**. RRF (Reciprocal Rank Fusion) es famoso y gratis en Qdrant; tenía un draft de un esquema de pesos "aprendido" que pensaba que iba a ser más interesante. El eval me dijo cómo iba a probar que era mejor: filas lado a lado en el leaderboard, una de RRF, otra del esquema aprendido. Me di cuenta de que no iba a poder enviar el esquema aprendido en v0.5 *y* defenderlo en entrevista *y* sacar números útiles de 75 casos. Así que envié RRF y dejé el esquema aprendido como candidato para v2 documentado en `ARCHITECTURE.md`. Decir que no a la idea brillante fue un regalo directo de tener el eval ahí para rechazarla.

## Lo que voy a reportar cuando lleguen los números

Esta es la parte que no he hecho todavía, y decirlo es parte del diseño. El README apunta a una sección "Results — pending the first real run" con la *estructura* del leaderboard y celdas explícitas con `?`. El sistema corre, los tests pasan (71 de ellos), pero todavía no he ejecutado el bench completo en hardware real. Dos posts de la serie planeada dependen de esos números: el post #2 sobre si RRF de verdad le gana a un weighting más simple en estos 75 casos, y el post #4 sobre qué valor del lambda del decay rinde mejor en `temporal_update`.

Cuando escriba esos posts, el titular de cada uno va a ser **el gap entre dos configuraciones** — RRF vs solo-dense; LLM judge vs NLI baseline; decay off vs on — en lugar de "mi sistema sacó un X%". Esos gaps son lo que el eval framework está construido para medir, y son lo que creo que de verdad generaliza más allá de los 75 casos.

## Si quieres probarlo

El repo está en [github.com/alvarocanoo/mnemos](https://github.com/alvarocanoo/mnemos). El dataset está en `packages/eval/mnemos_eval/datasets/mnemos_bench_v1.jsonl` y las formas del `gold` por tarea están documentadas en `packages/eval/mnemos_eval/datasets/schema.md`. El código del runner es lo bastante pequeño para leer de una sentada — menos de 200 líneas por tipo de tarea, sobre todo llamadas `httpx` al servicio más una función de métrica.

Si estás evaluando esto para un puesto de AI Engineer: la parte que más me interesa defender es **el formato del dataset y las decisiones que forzó**. El sistema es un medio para hacer esas decisiones visibles. El siguiente post va a comparar una configuración baseline contra la completa sobre `mnemos-bench-v1` y reportar el gap de forma honesta, con el JSON per-case volcado al lado para que los fallos sean inspeccionables. Si el gap es pequeño, ese es el post. Si el gap es grande, ese también es el post.

---

*Construido como tercer proyecto de mi portfolio de AI engineer 2026. Fuente bilingüe: [Inglés](01-eval-first-en.md) · [Español](01-eval-first-es.md).*
