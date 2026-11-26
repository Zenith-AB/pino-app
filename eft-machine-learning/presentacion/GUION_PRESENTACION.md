# Guion · Defensa EFT Pino (10 minutos)

**Expositores:** Nacho (Ignacio) y Diego · **Archivo:** `Pino_EFT.pptx` (21 diapositivas + anexo)

> La nota es **individual** y habrá **preguntas cruzadas**: los dos deben poder explicar todas las diapositivas, no solo las propias.

## Reparto y tiempos

| Bloque | Quién | Diapositivas | Tiempo aprox. |
|---|---|---|---|
| Problema, datos, preparación y optimización | **Nacho** | 1 – 10 | 4:35 |
| Ensambles, generalización, selección, español, K-Means y producto | **Diego** | 11 – 17 | 3:15 |
| Demo, sesgos, conclusiones y recomendaciones | **Nacho** | 18 – 21 | 2:10 |

> Total: 10:00, sin holgura. Ensayar con cronómetro; si falta tiempo, acortar las diapositivas 4, 9 y 17.
> **Negrita** = lo que no se puede omitir.
> Antes de empezar: dejar la app abierta (`streamlit run app/streamlit_app.py`) en **Predecir una palabra**, idioma **Español**.

---

## NACHO · Diapositivas 1 a 10

### 1 · Portada (0:15)
"Buenos días. Somos Nacho y Diego, del equipo Pino. Pino es una app de alfabetización. Hoy respondemos con Machine Learning una pregunta concreta: **¿a qué edad aprende un niño cada palabra?**, en español y en inglés."

### 2 · Problema y objetivos (0:35)
"Cada lección de Pino se arma con palabras, y el orden decide si el niño se frustra, se aburre o aprende. Hoy las educadoras nivelan a mano: lento, inconsistente y no escala. Tenemos cinco objetivos: **estimar, transferir, nivelar, agrupar y cuidar**. Respecto de la primera versión, cambiamos el abandono con datos **simulados** por la dificultad de las palabras con datos **reales**."

### 3 · KPIs (0:30)
"Es una **regresión supervisada**. Definimos los KPIs antes de modelar. Cumplimos **MAE 1,50 años**, **R² 0,58**, **94 % en el nivel correcto ±1** y **0,05 % de errores graves**. Dos no se cumplen y lo decimos: Spearman 0,74 contra 0,75, y la transferencia directa al español, 0,53 contra 0,60."

### 4 · Datos (0:20)
"Fuentes públicas y citables: Kuperman (edad en inglés), Brysbaert (concreción), CMU (fonemas) y, en español, Alonso, SUBTLEX y MultiPic."

### 5 · CRISP-DM y herramientas (0:30)
"Seguimos **CRISP-DM** de forma iterativa: cambiamos el enfoque al mirar los datos y agregamos un filtro al ver el despliegue. Trabajamos con **Git y GitHub** para revisar cambios en equipo, **Jupyter** para reproducir, versiones fijas para que los modelos sean compatibles y **Streamlit** para recibir retroalimentación de educadoras."

### 6 · Calidad y anomalías (0:35)
"Revisamos nulos, duplicados, atípicos y errores lógicos. Excluimos **2.278 palabras** poco conocidas. Los atípicos son palabras reales, y lo comprobamos: **quitarlos empeora el error**, de 1,486 a 1,513. Por eso se quedan."

### 7 · EDA (0:30)
"**La frecuencia es la señal más fuerte** (–0,59) y **no es lineal**. Lo concreto se aprende antes, lo largo más tarde. Y el mismo concepto correlaciona **0,68** entre idiomas: se puede transferir."

### 8 · Preparación (0:25)
"En Python usamos diccionarios, conjuntos y contadores para calcular las **mismas 9 variables** en ambos idiomas, con un contrato que valida los datos. Nulos con mediana más indicador, **split 80/20 estratificado** y todo dentro de un **Pipeline**: sin fuga de información."

### 9 · Modelos supervisados (0:25)
"Partimos con Ridge y árbol como modelos base y sumamos ensambles. Cada uno tiene un motivo: Ridge es interpretable; bagging baja varianza; boosting baja sesgo. Descartamos SVR, k-NN y redes por costo o falta de señal."

### 10 · Optimización (0:30)
"GridSearch en Ridge y RandomizedSearch en el resto. El **árbol mejora 0,59 años** y deja de memorizar; Random Forest reduce su brecha de 0,95 a 0,16. En español usamos **validación anidada**: Gradient Boosting pasa de 1,26 a 1,16. Le paso a Diego."

---

## DIEGO · Diapositivas 11 a 17

### 11 · Ensambles (0:35)
"Gracias. Los ensambles sí aportan, y lo podemos medir. Un árbol sin podar tiene **2,12 años** de error; si promediamos 100 de esos árboles con **Bagging**, baja a **1,56**. Esa es la prueba directa de que el ensamble reduce la varianza.
Random Forest y Gradient Boosting optimizados llegan a **~1,49 años**, 0,10 mejor que Ridge y casi 0,9 mejor que la línea base.
En cambio, **Voting y Stacking casi no suman**: Random Forest y Gradient Boosting se equivocan en las mismas palabras, sus errores correlacionan 0,99. El error que queda no es del algoritmo, es ruido de la norma y del significado de la palabra."

### 12 · Generalización y selección (0:35)
"Para evaluar la generalización usamos **validación cruzada repetida 5×3**, o sea 15 estimaciones por modelo. La desviación entre folds es de solo 0,02 años: el resultado es estable, y todas las brechas train–validación están bajo 0,30.
Para elegir: el Stacking gana por **0,001 años**, unas nueve horas. El t-test corregido de Nadeau-Bengio dice que es significativo, pero con 23.000 palabras cualquier diferencia lo es. Por eso fijamos una regla antes de mirar: si un modelo está a menos de 0,02 años del mejor, gana el más simple. **Elegimos Gradient Boosting**: mismo error, **24 veces más rápido**, **1,2 MB contra 104 MB** y una sola pieza que mantener."

### 13 · Test (0:25)
"En el test, que el modelo nunca vio, el MAE es **1,50 años**, con intervalo de confianza 1,47 a 1,53, casi igual al 1,48 de la validación cruzada: **el modelo generaliza**.
El sesgo que tiene es regresión a la media: las palabras más tempranas salen uno a tres años más tarde. Pero es un sesgo seguro: casi nunca una palabra de adulto cae en un nivel infantil, solo el 0,05 %. Y somos honestos: **sin modelo ya se logra 82 % a ±1**, y con cortes fijos casi no asignamos el nivel 1. Calibrando los cortes, el nivel 1 sube de 2 % a 38 %."

### 14 · Español (0:30)
"En español hay solo 1.239 palabras. El modelo inglés tal cual llega a ρ = 0,53; uno propio, a 0,55; y el propio **más el conocimiento del inglés**, a **ρ = 0,71**. Es un stacking entre idiomas."

### 15 · K-Means (0:20)
"Como no supervisado, K-Means agrupa por cómo se ve y suena la palabra, sin usar la edad. Salen cuatro **familias de lecciones**."

### 16 · Por qué k = 4 (0:30)
"Las métricas internas no señalan un k claro: las palabras son un continuo. Elegimos 4 porque es **estable** (ARI 0,91), útil para planificar y K-Means supera a Ward y a la mezcla gaussiana. El valor para el negocio es un **orden de lecciones**: rimas, bisílabas, grupos consonánticos y largas."

### 17 · Producto (0:20)
"El resultado: **1.312 palabras en español y 10.333 en inglés** niveladas, con sílabas, fonemas, imágenes y filtro editorial. Nacho muestra el modelo en vivo."

---

## NACHO · Diapositivas 18 a 21

### 18 · Demo en vivo (0:45)
*(Cambiar al navegador con la app. Si algo falla, quedarse en la diapositiva: el pantallazo muestra lo mismo.)*
"Esta es la interfaz en Streamlit. Escribo **pelota**, traducción **ball**, y presiono **Autocompletar**: la app calcula sus variables con las mismas reglas del entrenamiento y predice **3,7 años**, nivel 1, primeras palabras. La norma real es 2,9.
Ahora muevo la **frecuencia** hacia abajo… y la edad sube: es la curva no lineal que vimos en el EDA. *(mostrar el gráfico ¿Qué pasaría si…?)*
Con la barra de la izquierda elijo la **edad del niño**: a los 5 años la probabilidad de que ya conozca la palabra es alta.
Y ahora un caso difícil: **palta**. *(clic en el botón «palta»)* El modelo dice **8,5 años**. Eso nos lleva a los sesgos."

### 19 · Sesgos, privacidad y ética (0:35)
"Las normas son de adultos de Estados Unidos y España. Lo medimos: de 10 palabras chilenas **ninguna está en la norma** y el modelo les suma **casi un año**; es una muestra chica, indicativa. Hoy no hay datos personales; si la app los recoge, aplican las **leyes 19.628 y 21.719**, consentimiento de apoderados y seudónimos. **El modelo propone, la educadora valida**."

### 20 · Conclusiones (0:30)
"Cuatro conclusiones. Uno: **se puede apoyar la nivelación**: 94 % en el nivel correcto ±1, contra 82 % sin modelo. Dos: **los ensambles sí aportan**, de 2,12 a 1,49 años, pero los heterogéneos no justifican su costo. Tres: elegimos **lo más simple que rinde**, Gradient Boosting. Cuatro: **el conocimiento cruza idiomas**, y esa es la vía para crecer.
La decisión para el negocio: adoptar el modelo y el dataset como punto de partida; las educadoras **validan en vez de nivelar desde cero**."

### 21 · Recomendaciones y cierre (0:20)
"Los próximos pasos: integrar el modelo a la app como endpoint, y la demo ya es el prototipo; sumar datos de niños reales con Wordbank y CHILDES; más español y vocabulario chileno; y cerrar el ciclo re-entrenando con los aciertos reales de los niños. Muchas gracias, quedamos atentos a sus preguntas."

---

## Preguntas probables (las pueden hacer a cualquiera de los dos)

| Pregunta | Respuesta corta |
|---|---|
| ¿Por qué MAE y no RMSE? | Está en años y se explica fácil a una educadora ("se equivoca 1,5 años en promedio"). Igual reportamos RMSE (1,90) y R². |
| ¿Por qué no eligieron el Stacking si tiene menor error? | Gana por 0,001 años: no es relevante. La regla fijada antes dice que, a menos de 0,02 años, gana el más simple. GB entrena 24× más rápido, es 87× más liviano y tiene menor brecha (0,06 vs 0,08). |
| ¿Cómo saben que no hay sobreajuste? | Brecha train–validación de 0,06 años, CV repetida estable (d.e. 0,02) y test (1,50) casi igual a CV (1,48). La learning curve converge. |
| ¿Cómo evitaron la fuga de información? | Imputación, escalado y one-hot dentro de un Pipeline que se ajusta en cada fold; el test se separó al inicio y solo se usó al final. |
| ¿Por qué RandomizedSearch y no GridSearch en todo? | Con muchos hiperparámetros la grilla explota; la búsqueda aleatoria cubre mejor el espacio con el mismo presupuesto. En Ridge, con un solo parámetro, sí usamos grilla. |
| ¿Por qué Ridge no mejora al optimizar? | El mejor alpha queda en el borde inferior: no necesita regularización. Su error es de sesgo (no capta la curva de la frecuencia), no de varianza. |
| ¿Qué es la diferencia entre Bagging y Boosting? | Bagging entrena modelos en paralelo sobre muestras bootstrap y promedia: baja la varianza. Boosting los entrena en secuencia corrigiendo los errores del anterior: baja el sesgo. |
| ¿Por qué Voting/Stacking no ayudan? | Combinar sirve si los modelos fallan distinto. RF y GB tienen errores correlacionados ≈ 0,99. |
| ¿Por qué el Spearman no llega a la meta? | 0,74 vs 0,75. El error restante viene del ruido de la norma (son juicios subjetivos de adultos) y del significado de la palabra; más datos del mismo tipo no ayudan (learning curve plana). Hacen falta variables nuevas. |
| ¿Por qué K-Means con silueta baja? | Las palabras forman un continuo. Elegimos k = 4 por interpretabilidad pedagógica, y las familias tienen edades medias distintas (6,1 a 8,5) sin haber usado la edad para agrupar. |
| ¿Cómo pasan la escala 1–11 del español a años? | Enlace equipercentil: se igualan los percentiles de la norma española y de la traducción inglesa en los conceptos que tienen ambas. |
| ¿Qué significa la probabilidad por edad de la app? | Es una guía: compara la edad del niño con la predicción suponiendo un error normal del tamaño del RMSE del modelo. No es una probabilidad calibrada. |
| ¿Qué riesgos éticos hay? | Sesgo cultural (normas de EE. UU. y España), contenido inapropiado por la frecuencia de películas (por eso el filtro) y licencias académicas. No hay datos de menores. Siempre valida una educadora. |
| ¿Por qué no eliminaron los atípicos? | Son palabras reales (largas, raras o con muchos vecinos). Al quitarlas del train el MAE de validación sube de 1,486 a 1,513. |
| ¿Qué es la validación anidada? | Un CV interno elige hiperparámetros y uno externo mide el error con datos que la búsqueda no vio; evita un resultado optimista. |
| ¿Qué aporta K-Means si la silueta es baja? | Organiza lecciones por dificultad de lectura, algo que la edad sola no da. Es estable (ARI 0,91) pero no son grupos naturales, y lo declaramos. |
| ¿Qué herramientas colaborativas usaron y por qué? | Git/GitHub para historial y revisión, Jupyter para reproducir, versiones fijas para compatibilidad y Streamlit para feedback de educadoras. |
| ¿Qué estructuras de datos de Python usaron? | Diccionario de pronunciaciones, conjuntos para vocales, Counter para vecinos ortográficos en tiempo lineal y DataFrames vectorizados. |
| ¿Cómo aplicaron CRISP-DM? | Las seis fases, con retorno: cambio de enfoque al revisar datos y filtro editorial al revisar el despliegue. |
| ¿Cómo monitorearían el modelo? | % de niveles corregidos por educadoras (re-entrenar sobre 20 %) y error en palabras nuevas. |
| ¿Cuánto mejora el modelo frente a no usarlo? | Nivel exacto 67,4 % contra 61,7 % y ±1 94,3 % contra 81,6 %. En palabras infantiles, de 0 % a 35 % de acierto exacto. |
| ¿Qué es la calibración de cortes? | Elegir los umbrales para que la proporción por nivel sea la real, usando predicciones out-of-fold del train. Recupera el nivel 1 (38 %) a cambio de 2 puntos de nivel exacto. |
