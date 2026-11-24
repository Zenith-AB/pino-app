# Guion · Defensa EP3 Pino (10 minutos)

**Expositores:** Nacho (Ignacio) y Diego · **Archivo:** `Pino_cambio_de_enfoque_v2.pptx` (18 diapositivas + anexo)

## Reparto y tiempos

| Bloque | Quién | Diapositivas | Tiempo |
|---|---|---|---|
| Problema, datos, preparación y optimización | **Nacho** | 1 – 8 | 4:20 |
| Ensambles, generalización, selección, español, K-Means y producto | **Diego** | 9 – 14 | 3:15 |
| Demo, sesgos, conclusiones y recomendaciones | **Nacho** | 15 – 18 | 2:30 |

> Ritmo: ~130 palabras por minuto. Lo que está en **negrita** es lo que no se puede omitir (son los números que pide la rúbrica).
> Antes de empezar: dejar la app abierta en el navegador (`streamlit run app/streamlit_app.py`) en la pestaña **Predecir una palabra**, idioma **Español**.

---

## NACHO · Diapositivas 1 a 8

### 1 · Portada (0:20)
"Buenos días. Somos Nacho y Diego, del equipo Pino. Pino es una app de alfabetización para niños. Hoy les mostramos un modelo de Machine Learning que responde una pregunta muy concreta: **¿a qué edad aprende un niño cada palabra?**, en español y en inglés."

### 2 · ¿Qué cambió? (0:30)
"Partimos con otro enfoque: predecir qué aprendiz abandonaría la app. El problema es que Pino todavía no tiene usuarios, así que ese modelo se entrenaba con **datos simulados**. Lo cambiamos: ahora la unidad es la **palabra**, usamos **normas psicolingüísticas reales** de unas 32.000 palabras y la salida es un **nivel por edad** que alimenta directamente el contenido de la app."

### 3 · ¿Por qué cambiamos? (0:25)
"Por cuatro razones: datos reales en vez de simulados; ataca el núcleo del producto, porque cada lección se arma con palabras; escala al inglés; y es ético por diseño, porque trabajamos con palabras, no con datos de niños."

### 4 · Problema de negocio y KPIs (0:40)
"Hoy las educadoras nivelan a mano, palabra por palabra: es lento, inconsistente y no escala. Lo planteamos como una **regresión supervisada**: estimar la edad de adquisición en años a partir de propiedades que se calculan solas, como frecuencia, largo, sílabas o concreción. Esa edad se traduce en **4 niveles** de la app.
Definimos los KPIs antes de modelar. Cumplimos **MAE de 1,50 años**, **R² de 0,58**, **94 % de palabras en el nivel correcto o a uno de distancia** y solo **0,05 % de errores graves**. El Spearman queda en 0,74, apenas bajo la meta de 0,75, y lo reportamos tal cual."

### 5 · Los datos (0:25)
"Todas las fuentes son públicas y citables: Kuperman para la edad de adquisición en inglés (30.000 palabras), Brysbaert para la concreción, el diccionario CMU para los fonemas y, en español, Alonso con 1.239 palabras, SUBTLEX para la frecuencia y MultiPic para las imágenes."

### 6 · EDA (0:35)
"Lo principal del análisis exploratorio: **la frecuencia es la señal más fuerte** (correlación –0,59) y su relación con la edad **no es lineal**. Lo concreto, lo que se puede dibujar, se aprende antes. Las palabras largas, más tarde. Y algo clave para el español: el mismo concepto en los dos idiomas correlaciona 0,68. Eso nos dice que **el conocimiento del inglés se puede transferir**."

### 7 · Preparación de los datos (0:40)
"Seguimos CRISP-DM. En la preparación hicimos cinco cosas:
uno, **calidad**: sacamos 2.278 palabras que menos de la mitad de los evaluadores conocía, porque su edad no es confiable;
dos, las **mismas 9 variables** para los dos idiomas;
tres, los **nulos** de concreción y grupo consonántico se imputan con la mediana más un indicador de ausencia;
cuatro, **split 80/20 estratificado por nivel**, y el test no se toca hasta el final;
y cinco, todo va en un **Pipeline** que se ajusta dentro de cada fold, así **no hay fuga de información**."

### 8 · Optimización de hiperparámetros (0:45)
"Optimizamos con validación cruzada de 5 folds, minimizando el MAE. Usamos **GridSearch** en Ridge y **RandomizedSearch** en árbol, Random Forest y Gradient Boosting.
La justificación está en el efecto: en el **árbol**, limitar profundidad y tamaño de hoja bajó el MAE de validación en **0,59 años** y la brecha con train cayó de 2,06 a 0,08: dejó de memorizar. En **Random Forest** la brecha bajó de 0,95 a 0,16. **Ridge no mejora**: su mejor alpha quedó en el borde de la grilla, o sea que su problema es de sesgo, no de varianza. Conclusión: optimizar importa más en los modelos de alta varianza.
Le paso a Diego para los ensambles."

---

## DIEGO · Diapositivas 9 a 14

### 9 · Ensambles: cuánto aportan (0:40)
"Gracias. Los ensambles sí aportan, y lo podemos medir. Un árbol sin podar tiene **2,12 años** de error; si promediamos 100 de esos árboles con **Bagging**, baja a **1,56**. Esa es la prueba directa de que el ensamble reduce la varianza.
Random Forest y Gradient Boosting optimizados llegan a **~1,49 años**, 0,10 mejor que Ridge y casi 0,9 mejor que la línea base.
En cambio, **Voting y Stacking casi no suman**: Random Forest y Gradient Boosting se equivocan en las mismas palabras, sus errores correlacionan 0,99. El error que queda no es del algoritmo, es ruido de la norma y del significado de la palabra."

### 10 · Generalización y selección (0:45)
"Para evaluar la generalización usamos **validación cruzada repetida 5×3**, o sea 15 estimaciones por modelo. La desviación entre folds es de solo 0,02 años: el resultado es estable, y todas las brechas train–validación están bajo 0,30.
Para elegir: el Stacking gana por **0,001 años**, unas nueve horas. El t-test corregido de Nadeau-Bengio dice que es significativo, pero con 23.000 palabras cualquier diferencia lo es. Por eso fijamos una regla antes de mirar: si un modelo está a menos de 0,02 años del mejor, gana el más simple. **Elegimos Gradient Boosting**: mismo error, **33 veces más rápido** de entrenar y una sola pieza que mantener."

### 11 · Evaluación en palabras nunca vistas (0:35)
"En el test, que el modelo nunca vio, el MAE es **1,50 años**, con intervalo de confianza 1,47 a 1,53, casi igual al 1,48 de la validación cruzada: **el modelo generaliza**.
El sesgo que tiene es regresión a la media: las palabras más tempranas salen uno a tres años más tarde. Pero es un sesgo seguro: casi nunca una palabra de adulto cae en un nivel infantil, solo el 0,05 %."

### 12 · ¿Funciona en español? (0:30)
"En español tenemos solo 1.239 palabras. Probamos tres estrategias. El modelo inglés aplicado tal cual llega a ρ = 0,53. Un modelo solo con datos españoles, 0,55. Y la mejor: un modelo propio **más el conocimiento del inglés**, usando la edad de la traducción y la predicción del modelo inglés: **ρ = 0,71**. Es un stacking entre idiomas."

### 13 · No supervisado: K-Means (0:25)
"Como técnica no supervisada usamos K-Means para agrupar palabras por cómo se ven y suenan, sin usar la edad. Salen cuatro **familias de lecciones**: cortas con rimas, bisílabas frecuentes, con grupos consonánticos y largas abstractas. La silueta es baja, las palabras son un continuo, así que elegimos k = 4 por interpretabilidad pedagógica."

### 14 · Resultado para la app (0:20)
"El producto final: **1.312 palabras en español y 10.333 en inglés** niveladas, con sílabas, fonemas y 473 pares imagen–palabra, listos para importar. Con filtro editorial para sacar groserías y violencia. Nacho les muestra cómo se usa el modelo en vivo."

---

## NACHO · Diapositivas 15 a 18

### 15 · Demo en vivo (1:00)
*(Cambiar al navegador con la app. Si algo falla, quedarse en la diapositiva: el pantallazo muestra lo mismo.)*
"Esta es la interfaz en Streamlit. Escribo **pelota** y presiono Enter: la app calcula sus variables con las mismas reglas del entrenamiento y predice **3,7 años**, nivel 1, primeras palabras. La norma real es 2,9.
Ahora muevo la **frecuencia** hacia abajo… y la edad sube: es la curva no lineal que vimos en el EDA. *(mostrar el gráfico ¿Qué pasaría si…?)*
Con la barra de la izquierda elijo la **edad del niño**: a los 5 años la probabilidad de que ya conozca la palabra es alta.
Y ahora un caso difícil: **palta**. *(clic en el botón «palta»)* El modelo dice **8,4 años**. Eso nos lleva a los sesgos."

### 16 · Sesgos, limitaciones y ética (0:30)
"En Chile *palta* es de las primeras palabras, pero el modelo no conoce vocabulario chileno: las normas son de adultos de Estados Unidos y España, y la frecuencia viene de subtítulos de películas. Por eso en la primera ejecución aparecieron *beer* o *gun* como palabras fáciles, y agregamos un filtro editorial. Lo ético: no hay datos personales de niños, y **el modelo propone, la educadora valida**."

### 17 · Conclusiones (0:35)
"Cuatro conclusiones. Uno: **se puede nivelar automáticamente**, 94 % en el nivel correcto ±1. Dos: **los ensambles sí aportan**, de 2,12 a 1,49 años, pero los heterogéneos no justifican su costo. Tres: elegimos **lo más simple que rinde**, Gradient Boosting. Cuatro: **el conocimiento cruza idiomas**, y esa es la vía para crecer.
La decisión para el negocio: adoptar el modelo y el dataset como punto de partida; las educadoras **validan en vez de nivelar desde cero**."

### 18 · Recomendaciones y cierre (0:25)
"Los próximos pasos: integrar el modelo a la app como endpoint, y la demo ya es el prototipo; sumar datos de niños reales con Wordbank y CHILDES; más español y vocabulario chileno; y cerrar el ciclo re-entrenando con los aciertos reales de los niños. Muchas gracias, quedamos atentos a sus preguntas."

---

## Preguntas probables (las pueden hacer a cualquiera de los dos)

| Pregunta | Respuesta corta |
|---|---|
| ¿Por qué MAE y no RMSE? | Está en años y se explica fácil a una educadora ("se equivoca 1,5 años en promedio"). Igual reportamos RMSE (1,90) y R². |
| ¿Por qué no eligieron el Stacking si tiene menor error? | Gana por 0,001 años: no es relevante. La regla fijada antes dice que, a menos de 0,02 años, gana el más simple. GB entrena 33× más rápido y tiene menor brecha (0,06 vs 0,08). |
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
