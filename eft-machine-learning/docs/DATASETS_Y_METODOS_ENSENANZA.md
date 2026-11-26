# Datasets de palabras y métodos para enseñar a leer a niños pequeños (español e inglés)

Catálogo de recursos para construir el contenido de Pino. Para cada uno se indica qué aporta,
si ya está integrado en `data/raw/` y cómo se accede.

---

## 1. Datasets integrados en este proyecto

| Dataset | Idioma | Tamaño | Qué aporta | Acceso | Archivo |
|---|---|---|---|---|---|
| **Kuperman, Stadthagen-González y Brysbaert (2012)**: *Age-of-acquisition ratings for 30,000 English words* | EN | 30.121 palabras con AoA (archivo de 51.715 con frecuencia, letras, fonemas, sílabas y categoría) | Edad de adquisición en años: **variable objetivo** | Archivo original de crr.ugent.be (copia de Internet Archive) | `en_kuperman2012_aoa_51715.xlsx` |
| **Brysbaert, Warriner y Kuperman (2014)**: *Concreteness ratings for 40 thousand English lemmas* | EN | 39.954 | Concreción 1–5: las palabras "dibujables" se aprenden antes | Material suplementario, *Behavior Research Methods* | `en_brysbaert2014_concreteness.xlsx` |
| **CMU Pronouncing Dictionary** | EN | 134.000 | Pronunciación en fonemas ARPAbet: grupos consonánticos, base para la fonética inglesa | GitHub `cmusphinx/cmudict` (licencia BSD) | `en_cmudict.dict` |
| **Alonso, Fernández y Díez (2015)**: *Subjective AoA norms for 7,039 Spanish words* | ES | 1.239 vinculadas a conceptos (de 7.039 en total) | AoA en español, escala 1–11 | NoRaRe / Concepticon (GitHub `concepticon/norare-data`, CC-BY) | `es_alonso2015_aoa_norare.tsv` |
| **Alonso et al. (2016)**: AoA de verbos | ES | 387 vinculadas | AoA de verbos (otra escala) | NoRaRe | `es_alonso2016_aoa_verbos_norare.tsv` |
| **SUBTLEX-ESP**, Cuetos et al. (2011) | ES | 94.000 formas | Frecuencia de uso (subtítulos) | Archivo original de crr.ugent.be (copia de Internet Archive) | `es_subtlex_esp_cuetos2011.xlsx` |
| **Guasch et al. (2016)**: normas afectivas y semánticas | ES | 336 vinculadas | Concreción, imaginabilidad y familiaridad en español | NoRaRe | `es_guasch2016_ratings_norare.tsv` |
| **MultiPic**, Duñabeitia et al. (2022) | 30 idiomas | 750 dibujos | Nombre más frecuente de cada dibujo en español (España y Río de la Plata) e inglés, con % de acuerdo y familiaridad. Base de los **ejercicios imagen–palabra** | CC-BY, NoRaRe (las imágenes se descargan en bcbl.eu/multipic) | `multipic_dunabeitia2022.csv` |

## 2. Datasets recomendados para la siguiente etapa

Ordenados por valor para Pino:

| Dataset | Idioma | Por qué importa | Acceso |
|---|---|---|---|
| **Wordbank** (Frank et al., 2017): inventarios MacArthur-Bates CDI | ES (México, España), EN y 40 más | Datos **de niños reales**: qué palabras dicen o comprenden según su edad, de 8 a 30 meses. Es la mejor fuente para el **Nivel 1 – Primeras palabras**, y en español la más cercana a Latinoamérica es la de México | Gratis; paquete R `wordbankr` o Redivis (requiere cuenta gratuita) |
| **CHILDES / childes-db** | ES, EN y más | Transcripciones de **habla dirigida a niños**. Sirve para calcular la frecuencia "infantil" real y corregir el sesgo de SUBTLEX, que es habla adulta | Paquete Python `childespy` |
| **"Cuenta Palabras"**, diccionario de frecuencia léxica infantil del español rioplatense | ES (Argentina y Uruguay) | Frecuencia en textos para y de niños latinoamericanos | Revista *Lingüística* (UNComa) |
| **LEXIN**, Corral, Ferrero y Goikoetxea (2009) | ES (España) | Léxico de los libros de lectura de jardín infantil y 1.º básico | Programa de los autores (pedir acceso) |
| **EsPal**, Duchon et al. (2013) | ES | Frecuencia, vecindarios, sílabas y propiedades fonológicas de cualquier palabra | Web bcbl.eu/databases/espal |
| **Alonso et al. (2015), lista completa** | ES | 7.039 palabras (aquí solo usamos 1.239). Multiplicaría por 5 los datos de entrenamiento en español | Material suplementario Springer (DOI 10.3758/s13428-014-0454-2) |
| **Glasgow Norms**, Scott et al. (2019) | EN | 5.553 palabras con AoA, concreción, imaginabilidad y familiaridad | Suplemento abierto del artículo |
| **Listas Dolch (220 + 95) y Fry (1.000)** | EN | *Sight words*: palabras de alta frecuencia que en inglés se enseñan "de memoria" porque no son decodificables (*the, said, was*) | Dominio público |
| **Normas de AoA infantil de la USAL**: palabras producidas por niños de 11 a 49 meses | ES | Producción real de niños españoles | iblues-inico.usal.es |

## 3. Métodos de enseñanza de la lectura y cómo los apoya el dataset

### Marco general: *Science of Reading*
* **Simple View of Reading** (Gough y Tunmer, 1986): comprensión lectora = **decodificación × comprensión del lenguaje**. Pino entrena ambas: la decodificación con fonemas, sílabas y trazado, y el vocabulario oral con imagen, audio y AoA.
* **Cuerda de Scarborough**: reconocimiento de palabras (conciencia fonológica, decodificación, palabras de vista) más comprensión (vocabulario, conocimiento del mundo).
* **Conciencia fonológica antes que letras:** rimas → sílabas → fonemas. Es la base de los niveles 1 y 2.

### Español: ortografía transparente
| Método | Idea | Campos del dataset que lo apoyan |
|---|---|---|
| **Fonético / sintético** | Enseñar la correspondencia letra–sonido y combinar (*m + a = ma*) | `fonemas`, `opacidad` (≈ 0 en español) |
| **Silábico** | Partir de sílabas directas CV (*ma, pa, sa*) y avanzar a inversas (*al*), trabadas (*tra, pla*) y mixtas | `silabas`, `complejidad_silabica` (CV = 1,0 … CCVC = 3,0) |
| **Palabra generadora / global** | Palabras significativas y concretas (*mamá, oso, sol*) con imagen; después se descomponen | `concrecion`, `con_imagen_multipic`, `nivel_pino` |
| **Ecléctico** (el usado en Chile, MINEDUC) | Combina los anteriores | Todo el dataset: nivel por edad + estructura silábica |

**Secuencia que sugiere el dataset:** vocales → consonantes continuas (m, s, l, p) en sílabas CV de palabras de nivel 1–2 con muchos vecinos → sílabas inversas y trabadas (familia "Largas y multisilábicas").

### Inglés: ortografía opaca
| Método | Idea | Campos |
|---|---|---|
| **Systematic Synthetic Phonics** (Jolly Phonics, *Letters and Sounds*; obligatorio en el Reino Unido) | 44 fonemas, grafemas en un orden fijo (s, a, t, p, i, n…), decodificar palabras CVC (*cat*, *sit*) | `fonemas` (CMU), `opacidad`, `n_silabas` |
| **Word families / onset–rime** | Rimas: *-at (cat, hat, bat)*, *-og (dog, log)* | `vecinos_ort` (vecindario de Coltheart); familia "Cortas con familia (rimas)" |
| **Sight words** (Dolch/Fry) | Palabras irregulares y muy frecuentes que se memorizan | `opacidad` alta + `zipf` alto |
| **Decodable readers** | Textos que usan solo los grafemas ya enseñados | Filtro por nivel + fonemas |

### Transversales (ya presentes en la app)
* **Repetición espaciada** (SuperMemo SM-2, implementado en `algoritmo_adaptativo.py`): cada palabra vuelve a aparecer en intervalos crecientes. La AoA estimada sirve como **dificultad inicial** del ítem.
* **Doble codificación** (Paivio): imagen + palabra + audio → `pares_imagen_es_en.csv`.
* **Bilingüismo:** se puede aprovechar la **transferencia entre idiomas** con cognados (*elefante / elephant*) y enseñar primero los conceptos que el niño ya domina en su lengua materna. Los pares MultiPic con nivel en ambos idiomas permiten detectarlos.

## 4. Cómo citar
Si los datasets se usan en publicaciones o en la app, hay que citar a sus autores (ver *Fuentes* en `README.md`). El uso comercial requiere revisar la licencia de cada recurso.
