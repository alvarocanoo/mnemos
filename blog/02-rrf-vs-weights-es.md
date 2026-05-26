# Por qué elegí RRF antes de tener números que lo respaldaran

> El primer post de esta serie prometía una segunda entrega comparando RRF contra una fusión ponderada *sobre `mnemos-bench-v1`*, con números reales. Este no es ese post. El bench todavía no se ha ejecutado — Docker está dando guerra en mi máquina de desarrollo. Lo que sí puedo contar hoy con honestidad es por qué elegí RRF frente a una fusión ponderada *bajo incertidumbre*, antes de tener un solo número que lo justificara. El post de números-contra-números llega cuando corra el bench.

Si quieres el upstream: el sistema está en [github.com/alvarocanoo/mnemos](https://github.com/alvarocanoo/mnemos), y el post anterior es *"Escribí el suite de evals antes de escribir el sistema de memoria"*.

## La decisión que no podía aplazar

El retrieval híbrido te da dos listas ranqueadas — una de BM25 (léxica), otra de embeddings densos (semántica) — y te obliga a fusionarlas en una sola. Esa fusión es una decisión de diseño que tomas *una vez*, que se mete en la capa de storage, y que tienes que defender en cada conversación posterior sobre calidad de retrieval.

Cuando estaba dibujando el camino híbrido de `mnemos`, el bench no existía aún. (Ahora sí existe — 75 casos hand-authored en cinco tipos de tarea — pero todavía no tiene números para estas dos configuraciones en paralelo.) No tenía datos por tipo de tarea diciéndome si dense o sparse dominarían. No tenía calibración de la distribución de scores de ninguno de los dos retrievers sobre mi dominio. Tenía media configuración de colección Qdrant escrita y una deadline.

Esa es la situación donde la mayoría del consejo "deberías medir" es inútil. Vas a medir, eventualmente. La pregunta es qué default defendible se publica hoy para que las mediciones futuras tengan algo contra lo que empujar.

## Las dos opciones reales

Lo reduje a dos:

**Opción A — Media ponderada de scores normalizados.** Corres los dos retrievers, normalizas cada uno a `[0, 1]` (min-max o z-score), combinas como `w_dense · s_dense + w_sparse · s_sparse`, ordenas. Los dos pesos son hiperparámetros tuneables.

**Opción B — Reciprocal Rank Fusion (RRF).** Corres los dos retrievers, ignoras los scores por completo, usas el *rank* del documento en cada lista. El score fusionado de un documento `d` es `Σ_i 1 / (k + rank_i(d))` sumando sobre retrievers. `k = 60` por defecto, el mismo valor del paper original de 2009 y el que Qdrant expone por defecto. Ordenas por score fusionado.

Las dos son simples de implementar. Las dos son razonables. Se comportan distinto en dos puntos concretos:

- **La opción A es sensible a las distribuciones de score.** La similitud coseno densa vive más o menos en `[0, 1]`, los scores de BM25 pueden ser arbitrariamente grandes según las stats del corpus. Normalizar a un rango común esconde esto, pero la elección de normalización se convierte en sí misma en un hiperparámetro — y uno *oculto*, porque la mayoría de los equipos normalizan una vez y se olvidan.
- **La opción B es sensible solo al *orden*.** No le importa si el primer hit de BM25 tuvo score 18.4 o score 4.2. Solo le importa que fuera el primero. Eso hace a RRF robusto frente a recalibraciones de retrievers: si cambias el modelo de embeddings o el indexador de BM25, la fusión no hay que re-tunearla.

## Por qué tunear pesos a mano es una trampa para un junior publicando esto

Voy a ser directo porque el sesgo que estoy combatiendo es uno que comparto. La media ponderada parece más sofisticada. Tiene knobs. Los knobs dan sensación de control. Cuando un reclutador o entrevistador pregunta "¿cómo elegiste la fusión?", decir *"tunee w_dense y w_sparse sobre un held-out set"* suena a alguien que entendió el problema.

La trampa es que para fijar esos pesos honestamente, necesitas tres cosas que yo no tenía en el día uno:

1. Un held-out set cuya distribución case con el tráfico de producción. (Mis 75 casos son hand-authored, no son tráfico de producción. Los pesos que aprendería serían pesos para *mi* gusto en queries, no para los de un usuario futuro desconocido.)
2. Una métrica de scoring sobre la que el optimizador converja de manera estable. Con N pequeño, incluso nDCG@10 tiene varianza alta entre runs.
3. Una historia defendible de *por qué exactamente esos pesos* — no "hice gridsearch" sino "esta es la geometría de mi espacio de retrieval que predice esos pesos".

Sin (1), (2), (3), los pesos tuneados son un overfit a lo primero que probé que parecía mejor. Publicar eso y llamarlo "tuneado" es peor que publicar RRF y llamarlo el default.

RRF tiene cero hiperparámetros de dominio que tunear. `k = 60` es el valor que el paper original encontró insensible a la elección de corpus y de retriever, validado repetidas veces desde entonces. Elegirlo no es una decisión por la que deba una justificación de dominio. Es el *default citable*.

## La afirmación defendible, en una frase

> "Elegí RRF como fusión por defecto porque no requiere calibración de los scores de los retrievers, lleva 15 años de track record siendo robusto en tareas de IR, y es la implementación que Qdrant trae nativa — lo cual significa que no estoy manteniendo código de fusión custom que diverja del upstream con el tiempo."

Esa frase aguanta tanto si los números del bench salen halagadores como si salen poco halagadores, porque no afirma que RRF sea el mejor sobre mis datos. Afirma que es el default defendible *bajo incertidumbre*. El yo-futuro le exigirá al yo-pasado que sostenga eso.

## La implementación, en código real

El retrieval híbrido de `mnemos` vive en dos archivos. La capa Qdrant en [packages/core/mnemos/storage/qdrant.py](https://github.com/alvarocanoo/mnemos/blob/main/packages/core/mnemos/storage/qdrant.py) hace una sola llamada `query_points` con un `Prefetch` por retriever y un `FusionQuery(fusion=Fusion.RRF)` para fusionar:

```python
def hybrid_search(
    settings: Settings,
    dense_query: list[float],
    sparse_query: SparseVec,
    user_id: str,
    limit: int,
    prefetch_limit: int = 50,
) -> list[tuple[UUID, float]]:
    client = get_client()
    response = client.query_points(
        collection_name=settings.qdrant_collection,
        prefetch=[
            qm.Prefetch(
                query=dense_query,
                using="dense",
                limit=prefetch_limit,
                filter=_user_filter(user_id),
            ),
            qm.Prefetch(
                query=qm.SparseVector(
                    indices=sparse_query.indices,
                    values=sparse_query.values,
                ),
                using="sparse",
                limit=prefetch_limit,
                filter=_user_filter(user_id),
            ),
        ],
        query=qm.FusionQuery(fusion=qm.Fusion.RRF),
        limit=limit,
        with_payload=False,
    )
    return [(UUID(str(point.id)), float(point.score)) for point in response.points]
```

Ese es todo el código de fusión. Cero pesos. Cero normalización de scores. Una llamada, dos prefetches, RRF.

`prefetch_limit = 50` es el único knob que merece defensa. La doc de Qdrant recomienda prefetch > limit para que la fusión tenga material suficiente para mezclar de forma significativa. Cincuenta es un default `v0.5`; tunearlo vive en el bucle de eval, no en un comentario.

La capa de retrieval en [packages/core/mnemos/retrieval/hybrid.py](https://github.com/alvarocanoo/mnemos/blob/main/packages/core/mnemos/retrieval/hybrid.py) envuelve la llamada Qdrant, hace join con la metadata de Postgres, y multiplica el score fusionado por un peso de decay temporal antes de devolver el top-`k`. Esa multiplicación por decay es el *único* sitio donde `mnemos` modifica un score de Qdrant, y es honesto al respecto — mismo factor para cada memoria en el pool de candidatos, así que el orden solo cambia cuando los pesos de decay difieren entre edades.

## Lo que dirá el leaderboard (y lo que no)

Cuando el bench corra, cuatro filas aparecerán en `leaderboard.md` en la tabla de retrieval:

| config | retriever | fusion | recall@10 |
|---|---|---|---|
| `naive_dense_only` | dense | — | ? |
| `bm25_only` | sparse | — | ? |
| `mnemos_hybrid_no_decay` | dense + sparse | RRF | ? |
| `mnemos_full` | dense + sparse | RRF + decay | ? |

Tres lecturas posibles de esas filas, todas útiles:

- **Híbrido >> cualquiera por separado.** RRF está haciendo trabajo real. El post-#2 con números se escribe solo.
- **Híbrido ≈ dense solo.** BM25 está aportando poco sobre estos 75 casos. Tocaría examinar si el dataset es demasiado semántico, o si BM25 está siendo aplastado por el top-k denso.
- **Híbrido < dense solo.** RRF está degradando el retrieval. Sería sorprendente pero no sin precedente en benchmarks pequeños; el post se metería a fondo en el porqué, probablemente con dumps por caso.

Nota lo que *no* estoy escribiendo: una fila llamada `mnemos_hybrid_weighted`. No implementé fusión por media ponderada porque hacerlo honestamente exigiría comprometerme a un protocolo de tuneo — split held-out, optimizador, grid de pesos — y el dataset es demasiado pequeño para hacer eso sin overfitear. Si los resultados del bench empujan hacia "RRF era el camino equivocado", el siguiente movimiento es crecer el dataset primero, después tunear.

## Lo que no puedo afirmar hoy con honestidad

Para mantenerme dentro de la regla de este post — sin números, sin afirmaciones que necesiten números — las cosas que *no* estoy diciendo ahora:

- No estoy diciendo que RRF gane a la media ponderada sobre `mnemos-bench-v1`. El bench no se ha corrido para ninguno de los dos lados.
- No estoy diciendo que RRF gane a la media ponderada en general. El paper de 2009 dice que gana a Condorcet y a learning-to-rank sobre datos a escala TREC; mis datos son 75 casos, no TREC.
- No estoy afirmando que `prefetch_limit = 50` sea óptimo. Es el valor de arranque recomendado por Qdrant y no he hecho sweep.
- No estoy afirmando que BGE-M3 + Qdrant BM25 sea el par de retrievers ideal. Son el par defendible más barato dado el constraint de correr en local sin API key.

Esos gaps son la agenda de posts siguientes y de runs del bench, no ocultaciones.

## Siguiente

El próximo post de esta serie comparará la implementación LLM-as-judge de detección de contradicciones contra el baseline NLI sobre los 15 casos de `contradiction` del bench. Mismo molde: escribir el diseño primero, correr el bench, reportar el gap con honestidad. Si el LLM judge no le gana claro al baseline NLI, el post se convierte en "por qué publiqué dos jueces y dejé que el usuario elija". Si le gana, el post se convierte en "el coste de tener razón".

---

*Hecho como parte del tercer proyecto de mi portfolio AI Engineer 2026. Repo: [github.com/alvarocanoo/mnemos](https://github.com/alvarocanoo/mnemos). Versión bilingüe: [English](02-rrf-vs-weights-en.md) · [Español](02-rrf-vs-weights-es.md).*
