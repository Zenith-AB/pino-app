# -*- coding: utf-8 -*-
"""
Pino · Probador del modelo de edad de adquisición (AoA)

Interfaz interactiva para probar los modelos entrenados en el notebook:
  * Inglés: Gradient Boosting (HistGradientBoostingRegressor) sobre 28.825 palabras (Kuperman et al., 2012).
  * Español: modelo propio + transferencia desde el inglés (Alonso et al., 2015), llevado a años
    con enlace equipercentil.

Ejecutar desde la carpeta eft-machine-learning:
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motor  # noqa: E402

st.set_page_config(page_title="Pino · ¿A qué edad se aprende una palabra?", page_icon="🌲", layout="wide")

COLORES_NIVEL = ["#2E7D32", "#4CAF50", "#FF9800", "#EF6C00", "#C62828"]
NOMBRE_IDIOMA = {"es": "Español", "en": "Inglés"}
EJEMPLOS = {
    "es": [("perro", "dog"), ("mariposa", "butterfly"), ("tren", "train"), ("bicicleta", "bicycle"),
           ("guagua", "baby"), ("palta", "avocado"), ("democracia", "democracy")],
    "en": ["dog", "ball", "butterfly", "dinosaur", "strawberry", "island", "democracy"],
}
RANGOS = {  # (mín, máx, paso) de cada control
    "zipf": (1.0, 7.5, 0.05), "n_letras": (1, 20, 1), "n_fonemas": (1, 20, 1), "n_silabas": (1, 8, 1),
    "grupo_cons_max": (0, 5, 1), "vecinos_ort": (0, 40, 1), "concrecion": (1.0, 5.0, 0.05),
    "complejidad_silabica": (1.0, 3.0, 0.05), "aoa_equivalente_en": (1.5, 17.0, 0.1),
}
OPCIONALES = ["zipf", "grupo_cons_max", "concrecion", "aoa_equivalente_en"]  # pueden quedar "desconocidas"
ETIQUETAS = {
    "zipf": "Frecuencia de uso (escala Zipf)",
    "n_letras": "N.º de letras",
    "n_fonemas": "N.º de fonemas (sonidos)",
    "n_silabas": "N.º de sílabas",
    "grupo_cons_max": "Grupo consonántico más largo",
    "vecinos_ort": "Vecinos ortográficos (palabras a una letra)",
    "concrecion": "Concreción (1 abstracta – 5 concreta)",
    "categoria": "Categoría gramatical",
    "complejidad_silabica": "Complejidad silábica media (CV = 1 … CCVC = 3)",
    "aoa_equivalente_en": "AoA de la traducción inglesa (años)",
}
AYUDAS = {
    "zipf": "log10(frecuencia por millón) + 3. Muy rara ≈ 1–2, común ≈ 4, muy común ≥ 5. Es la variable más importante.",
    "concrecion": "¿Se puede ver, tocar o dibujar? perro ≈ 5, idea ≈ 1,5. Lo concreto se aprende antes.",
    "grupo_cons_max": "Mayor secuencia de consonantes seguidas al pronunciar: 'tr' = 2, 'str' = 3.",
    "vecinos_ort": "Palabras que cambian en una sola letra (cat → hat, bat). Muchos vecinos = se aprende antes.",
    "aoa_equivalente_en": "Edad a la que se aprende la traducción en inglés (Kuperman). Es la 'transferencia' entre idiomas.",
    "complejidad_silabica": "Sílabas directas (ma, pa) = 1; trabadas (tra, pla) = 2,4; mixtas (tren) = 3.",
}


# --------------------------------------------------------------------------- carga
@st.cache_resource(show_spinner="Cargando modelos y normas psicolingüísticas (solo la primera vez)…")
def precargar():
    motor.modelos(); motor.tabla_en(); motor.tabla_es(); motor.vocab_es(); motor.vocab_en()
    motor.cmudict(); motor.concrecion_en(); motor.kuperman(); motor.subtlex_es()
    motor.patrones_en(); motor.patrones_es()
    return True


precargar()
_, MODELO_ES, _, MET = motor.modelos()


# ---------------------------------------------------------------- estado / callbacks
def k(L, var):
    return f"{L}_{var}"


def _clip(var, x):
    lo, hi, paso = RANGOS[var]
    x = min(max(x, lo), hi)
    return int(round(x)) if isinstance(paso, int) else float(round(x, 2))


def cargar_palabra(L: str, palabra: str | None = None, traduccion: str | None = None):
    """Calcula las variables de la palabra y las escribe en los controles."""
    if palabra is not None:
        st.session_state[k(L, "palabra")] = palabra
    if traduccion is not None:
        st.session_state[k(L, "traduccion")] = traduccion
    w = st.session_state.get(k(L, "palabra"), "").strip().lower()
    if not w:
        return
    if L == "en":
        r = motor.rasgos_en(w)
    else:
        r = motor.rasgos_es(w, st.session_state.get(k(L, "traduccion"), ""))
        st.session_state[k(L, "traduccion")] = r["traduccion_en"]
    vars_L = list(RANGOS) if L == "es" else [v for v in RANGOS if v not in ("complejidad_silabica", "aoa_equivalente_en")]
    for var in vars_L:
        val = r.get(var)
        if var in OPCIONALES:
            st.session_state[k(L, var + "_na")] = val is None
        st.session_state[k(L, var)] = _clip(var, val if val is not None else (RANGOS[var][0] + RANGOS[var][1]) / 2)
    st.session_state[k(L, "categoria")] = r["categoria"]
    st.session_state[k(L, "meta")] = {"palabra": w, **{c: r.get(c) for c in ("aoa_real", "fuente", "silabas", "fonemas")}}


def cambio_traduccion(L: str):
    info = motor.info_traduccion(st.session_state.get(k(L, "traduccion"), ""))
    for var in ("aoa_equivalente_en", "concrecion"):
        st.session_state[k(L, var + "_na")] = info[var] is None
        if info[var] is not None:
            st.session_state[k(L, var)] = _clip(var, info[var])


# Streamlit borra el estado de los controles que no se dibujan en una ejecución (p. ej. los del
# otro idioma). Reasignarlos al inicio los conserva al cambiar de idioma.
for _key in list(st.session_state.keys()):
    if _key.startswith(("es_", "en_", "whatif_", "lista_")):
        st.session_state[_key] = st.session_state[_key]

for _L, _ej in (("es", EJEMPLOS["es"][1]), ("en", EJEMPLOS["en"][2])):
    if k(_L, "meta") not in st.session_state:
        if _L == "es":
            cargar_palabra(_L, *_ej)
        else:
            cargar_palabra(_L, _ej)


def valores(L: str) -> dict:
    vars_L = list(RANGOS) if L == "es" else [v for v in RANGOS if v not in ("complejidad_silabica", "aoa_equivalente_en")]
    v = {}
    for var in vars_L:
        v[var] = None if st.session_state.get(k(L, var + "_na"), False) else st.session_state[k(L, var)]
    v["categoria"] = st.session_state[k(L, "categoria")]
    return v


# ------------------------------------------------------------------------ gráficos
def gauge(res: dict, aoa_real: float | None, edad: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(res["aoa"], 1),
        number={"suffix": " años", "font": {"size": 44}},
        gauge={
            "axis": {"range": [0, 14], "tickvals": [0, 2, 4, 6, 8, 10, 12, 14]},
            "bar": {"color": "#263238", "thickness": 0.25},
            "steps": [{"range": [a, b], "color": c} for a, b, c in
                      zip([0, 4, 6, 8, 10], [4, 6, 8, 10, 14], ["#C8E6C9", "#DCEDC8", "#FFE0B2", "#FFCCBC", "#FFCDD2"])],
            "threshold": {"line": {"color": "#1565C0", "width": 4}, "thickness": 0.9, "value": edad},
        },
    ))
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=30, b=0))
    return fig


def tarjeta_nivel(res: dict) -> str:
    c = COLORES_NIVEL[res["nivel"]]
    return (f"<div style='background:{c};color:white;padding:14px 18px;border-radius:14px;'>"
            f"<div style='font-size:0.85rem;opacity:.9'>Nivel sugerido en Pino</div>"
            f"<div style='font-size:1.5rem;font-weight:700'>{res['nivel_nombre']}</div>"
            f"<div style='font-size:0.9rem'>{res['uso']}</div></div>")


def texto_prob(p: float, edad: float) -> str:
    if p >= 0.7:
        return f"🟢 Probablemente **ya la conoce** a los {edad:g} años ({p:.0%})."
    if p >= 0.4:
        return f"🟡 **Está aprendiéndola** alrededor de los {edad:g} años ({p:.0%})."
    return f"🔴 **Todavía es difícil** a los {edad:g} años ({p:.0%})."


# ------------------------------------------------------------------------ barra lateral
with st.sidebar:
    st.markdown("## 🌲 Pino")
    idioma = st.radio("Idioma de la palabra", ["es", "en"], format_func=lambda x: {"es": "🇪🇸 Español", "en": "🇬🇧 Inglés"}[x],
                      horizontal=True, key="idioma")
    edad = st.slider("Edad del niño (años)", 2.0, 12.0, 5.0, 0.5, key="edad",
                     help="Se compara con la edad de adquisición predicha para estimar si la palabra es adecuada.")
    st.divider()
    t = MET["test_en"]["Gradient Boosting"]
    st.markdown("**Modelo inglés:** Gradient Boosting")
    c1, c2 = st.columns(2)
    c1.metric("MAE test (años)", f"{t['MAE test']:.2f}")
    c2.metric("Nivel ±1", f"{t['nivel ±1']:.0%}")
    st.markdown("**Modelo español:** propio + transferencia del inglés")
    c1, c2 = st.columns(2)
    c1.metric("Spearman ρ", f"{MET['espanol']['tabla'][MET['espanol']['mejor_estrategia']]['Spearman']:.2f}")
    c2.metric("Zero-shot ρ", f"{MET['espanol']['spearman_zero_shot']:.2f}")
    st.caption("Niveles: N1 < 4 años · N2 4–6 · N3 6–8 · N4 8–10. "
               "El modelo **propone** y una educadora **valida**.")

L = idioma

st.title("¿A qué edad aprende un niño esta palabra?")
st.caption("Probador interactivo del modelo de edad de adquisición (AoA) de Pino · EFT MLY1101 Machine Learning")

tab1, tab2, tab3, tab4 = st.tabs(["🔮 Predecir una palabra", "🌎 Español vs. inglés", "📋 Nivelar una lección", "📊 Sobre el modelo"])

# =========================================================================== TAB 1
with tab1:
    izq, der = st.columns([1.05, 1], gap="large")
    with izq:
        st.subheader(f"1 · Elige una palabra en {NOMBRE_IDIOMA[L].lower()}")
        st.caption("Escribe una palabra y presiona **Autocompletar**: la app calcula sus variables con las mismas "
                   "reglas del entrenamiento. Después puedes mover cualquier control para ver cómo cambia la predicción.")
        a, b = st.columns([2, 1.3]) if L == "es" else (st.container(), None)
        a.text_input("Palabra", key=k(L, "palabra"), on_change=cargar_palabra, args=(L, None, "" if L == "es" else None))
        if L == "es":
            b.text_input("Traducción al inglés", key=k(L, "traduccion"), on_change=cambio_traduccion, args=(L,),
                         help="Se usa para la transferencia: AoA y concreción de la palabra equivalente en inglés.")
        st.button("⚡ Autocompletar variables", on_click=cargar_palabra, args=(L,), type="primary")
        st.markdown("**Ejemplos:**")
        cols = st.columns(4) + st.columns(4)
        for col, ej in zip(cols, EJEMPLOS[L]):
            if L == "es":
                col.button(ej[0], key=f"ej_{L}_{ej[0]}", on_click=cargar_palabra, args=(L, ej[0], ej[1]), width="stretch")
            else:
                col.button(ej, key=f"ej_{L}_{ej}", on_click=cargar_palabra, args=(L, ej), width="stretch")

        meta = st.session_state[k(L, "meta")]
        info = f"**{meta['palabra']}** · {meta['fuente']}"
        if meta.get("silabas"):
            info += f" · sílabas: `{meta['silabas']}`"
        if meta.get("fonemas"):
            info += f" · fonemas: `{meta['fonemas']}`"
        st.info(info)

        st.subheader("2 · Ajusta las variables clave")
        with st.container(border=True):
            def control(var, cont=st):
                lo, hi, paso = RANGOS[var]
                if var in OPCIONALES:
                    na = cont.checkbox(f"{ETIQUETAS[var]}: desconocida (el modelo la imputa)", key=k(L, var + "_na"))
                    cont.slider(ETIQUETAS[var], lo, hi, step=paso, key=k(L, var), help=AYUDAS.get(var),
                                disabled=na, label_visibility="collapsed")
                else:
                    cont.slider(ETIQUETAS[var], lo, hi, step=paso, key=k(L, var), help=AYUDAS.get(var))

            control("zipf")
            control("concrecion")
            c1, c2, c3 = st.columns(3)
            for var, c in zip(["n_letras", "n_fonemas", "n_silabas"], [c1, c2, c3]):
                c.number_input(ETIQUETAS[var], RANGOS[var][0], RANGOS[var][1], step=1, key=k(L, var))
            c1, c2 = st.columns(2)
            c1.slider(ETIQUETAS["vecinos_ort"], 0, 40, step=1, key=k(L, "vecinos_ort"), help=AYUDAS["vecinos_ort"])
            c2.selectbox(ETIQUETAS["categoria"], motor.CATEGORIAS, key=k(L, "categoria"))
            control("grupo_cons_max")
            if L == "es":
                st.markdown("**Variables propias del español**")
                control("complejidad_silabica")
                control("aoa_equivalente_en")
            v = valores(L)
            st.caption(f"Opacidad (letras − fonemas) calculada: **{v['n_letras'] - v['n_fonemas']}**")

    with der:
        res = motor.predecir(L, v, edad)
        st.subheader("3 · Predicción")
        st.plotly_chart(gauge(res, meta.get("aoa_real"), edad), width="stretch", config={"displayModeBar": False})
        st.markdown(tarjeta_nivel(res), unsafe_allow_html=True)
        st.write("")
        m1, m2, m3 = st.columns(3)
        m1.metric("Edad de adquisición", f"{res['aoa']:.1f} años")
        m2.metric("Rango 80 %", f"{max(res['lo'], 0):.1f} – {res['hi']:.1f}")
        if meta.get("aoa_real") is not None:
            m3.metric("Norma real", f"{meta['aoa_real']:.1f} años", f"{res['aoa'] - meta['aoa_real']:+.1f} error",
                      delta_color="off")
        else:
            m3.metric("Norma real", "—", help="Palabra nueva, sin norma publicada: justo el caso de uso del modelo.")
        st.markdown(texto_prob(res["prob_edad"], edad) + "  \n<small>La línea azul del indicador marca la edad elegida.</small>",
                    unsafe_allow_html=True)
        st.markdown(f"🧩 **Familia de lección (K-Means):** {res['familia']}")
        if L == "es":
            st.caption(f"Escala española (Alonso, 1–11): {res['aoa_escala']:.2f} · "
                       f"predicción del modelo inglés usada como variable: {res['pred_modelo_en']:.1f} años")

        st.subheader("4 · ¿Qué pasaría si…?")
        var_q = st.selectbox("Variar una sola variable y mantener el resto fijo",
                             ["zipf", "concrecion", "n_silabas", "n_letras", "vecinos_ort"] + (["aoa_equivalente_en"] if L == "es" else []),
                             format_func=lambda x: ETIQUETAS[x], key=f"whatif_{L}")
        lo, hi, paso = RANGOS[var_q]
        xs = np.linspace(lo, hi, 30) if isinstance(paso, float) else np.arange(lo, hi + 1)
        df_c = motor.curva(L, v, var_q, xs)
        actual = v.get(var_q)
        base = alt.Chart(df_c).mark_line(color="#4CAF50", strokeWidth=3).encode(
            x=alt.X(f"{var_q}:Q", title=ETIQUETAS[var_q]), y=alt.Y("AoA (años):Q", scale=alt.Scale(zero=False)),
            tooltip=[var_q, alt.Tooltip("AoA (años):Q", format=".2f")])
        capas = [base, alt.Chart(pd.DataFrame({"y": [edad]})).mark_rule(color="#1565C0", strokeDash=[5, 4]).encode(y="y:Q")]
        if actual is not None:
            capas.append(alt.Chart(pd.DataFrame({var_q: [actual], "AoA (años)": [res["aoa"]]}))
                         .mark_point(size=160, filled=True, color="#FF9800").encode(x=f"{var_q}:Q", y="AoA (años):Q"))
        st.altair_chart(alt.layer(*capas).properties(height=240), width="stretch")
        st.caption("Punto naranjo = palabra actual · línea azul = edad del niño. "
                   "Ej.: al subir la frecuencia, la edad de adquisición baja de forma no lineal.")

# =========================================================================== TAB 2
with tab2:
    st.subheader("La misma idea en dos idiomas")
    st.caption("Compara a qué edad se aprende un concepto en español y en inglés. Útil para decidir en qué orden "
               "aparece cada palabra en las lecciones bilingües de Pino.")
    pares_def = "perro = dog\nmariposa = butterfly\nmanzana = apple\ntren = train\nbicicleta = bicycle\nestrella = star\nfuego = fire\nisla = island"
    txt = st.text_area("Pares español = inglés (uno por línea)", pares_def, height=200, key="pares")
    filas = []
    for linea in txt.splitlines():
        if "=" not in linea:
            continue
        w_es, w_en = [x.strip().lower() for x in linea.split("=", 1)]
        if not w_es or not w_en:
            continue
        r_es, r_en = motor.rasgos_es(w_es, w_en), motor.rasgos_en(w_en)
        p_es, p_en = motor.predecir("es", r_es, edad), motor.predecir("en", r_en, edad)
        filas.append({"concepto": f"{w_es} / {w_en}", "Español": p_es["aoa"], "Inglés": p_en["aoa"],
                      "nivel ES": p_es["nivel_nombre"], "nivel EN": p_en["nivel_nombre"],
                      f"P(conoce a los {edad:g}) ES": p_es["prob_edad"], f"P(conoce a los {edad:g}) EN": p_en["prob_edad"],
                      "sílabas ES": r_es["silabas"]})
    if filas:
        df = pd.DataFrame(filas)
        larga = df.melt(id_vars="concepto", value_vars=["Español", "Inglés"], var_name="idioma", value_name="AoA (años)")
        orden = df.sort_values("Español")["concepto"].tolist()
        barras = alt.Chart(larga).mark_bar(cornerRadiusEnd=4).encode(
            y=alt.Y("concepto:N", sort=orden, title=None),
            x=alt.X("AoA (años):Q", scale=alt.Scale(domain=[0, max(12, larga["AoA (años)"].max() + 1)])),
            yOffset="idioma:N",
            color=alt.Color("idioma:N", scale=alt.Scale(domain=["Español", "Inglés"], range=["#FF9800", "#4CAF50"])),
            tooltip=["concepto", "idioma", alt.Tooltip("AoA (años):Q", format=".1f")])
        regla = alt.Chart(pd.DataFrame({"x": [edad]})).mark_rule(color="#1565C0", strokeDash=[5, 4], size=2).encode(x="x:Q")
        st.altair_chart((barras + regla).properties(height=40 * len(df) + 40), width="stretch")
        for c in (f"P(conoce a los {edad:g}) ES", f"P(conoce a los {edad:g}) EN"):
            df[c] = df[c] * 100
        st.dataframe(df, hide_index=True, width="stretch", column_config={
            "Español": st.column_config.NumberColumn("AoA ES (años)", format="%.1f"),
            "Inglés": st.column_config.NumberColumn("AoA EN (años)", format="%.1f"),
            **{c: st.column_config.ProgressColumn(c, format="%.0f%%", min_value=0, max_value=100)
               for c in (f"P(conoce a los {edad:g}) ES", f"P(conoce a los {edad:g}) EN")}})
        st.caption("En inglés la palabra suele llegar más tarde por la **opacidad** ortográfica (letras ≠ sonidos) y "
                   "porque el modelo español aprovecha la norma de la traducción (transferencia entre idiomas).")

# =========================================================================== TAB 3
with tab3:
    st.subheader(f"Ordenar las palabras de una lección ({NOMBRE_IDIOMA[L].lower()})")
    st.caption("Pega una lista de palabras: la app predice su edad de adquisición, las ordena de la más fácil a la más "
               "difícil y marca cuáles son adecuadas para la edad elegida. En español puedes usar `palabra = traducción`.")
    defecto = {"es": "sol\nmesa\nzapato\nplátano = banana\npelota\ncocodrilo\nmurciélago\nvolcán\nfrontera",
               "en": "cat\nsun\napple\nrabbit\npencil\nvolcano\ncastle\nlibrary"}[L]
    st.session_state.setdefault(f"lista_{L}", defecto)
    lista = st.text_area("Palabras (una por línea)", height=220, key=f"lista_{L}")
    filas = []
    for linea in lista.splitlines():
        if not linea.strip():
            continue
        w, _, tr = (x.strip().lower() for x in linea.partition("="))
        r = motor.rasgos_en(w) if L == "en" else motor.rasgos_es(w, tr)
        p = motor.predecir(L, r, edad)
        filas.append({"palabra": w, "AoA predicha (años)": round(p["aoa"], 2),
                      "norma real": np.nan if r["aoa_real"] is None else round(r["aoa_real"], 2),
                      "nivel": p["nivel_nombre"], f"P(conoce a los {edad:g})": p["prob_edad"],
                      "¿apta?": "✅" if p["prob_edad"] >= 0.5 else ("🟡" if p["prob_edad"] >= 0.25 else "⛔"),
                      "familia de lección": p["familia"],
                      "sílabas" if L == "es" else "fonemas": r.get("silabas") if L == "es" else r.get("fonemas")})
    if filas:
        df = pd.DataFrame(filas).sort_values("AoA predicha (años)").reset_index(drop=True)
        df.index = df.index + 1
        c1, c2, c3 = st.columns(3)
        c1.metric("Palabras", len(df))
        c2.metric(f"Aptas para {edad:g} años", int((df[f"P(conoce a los {edad:g})"] >= 0.5).sum()))
        c3.metric("AoA media", f"{df['AoA predicha (años)'].mean():.1f} años")
        pcol = f"P(conoce a los {edad:g})"
        df[pcol] = df[pcol] * 100
        df["norma real"] = df["norma real"].map(lambda x: "—" if pd.isna(x) else f"{x:.1f}")
        st.dataframe(df, width="stretch", column_config={
            "AoA predicha (años)": st.column_config.NumberColumn(format="%.1f"),
            "norma real": st.column_config.TextColumn("norma real (años)"),
            pcol: st.column_config.ProgressColumn(pcol, format="%.0f%%", min_value=0, max_value=100)})
        df[pcol] = df[pcol] / 100
        puntos = alt.Chart(df.reset_index(names="orden")).mark_circle(size=220).encode(
            x=alt.X("AoA predicha (años):Q", scale=alt.Scale(domain=[0, max(12, df["AoA predicha (años)"].max() + 1)])),
            y=alt.Y("palabra:N", sort=df["palabra"].tolist(), title=None),
            color=alt.Color("nivel:N", scale=alt.Scale(domain=motor.NIVELES, range=COLORES_NIVEL), legend=alt.Legend(orient="bottom")),
            tooltip=["palabra", "nivel", alt.Tooltip("AoA predicha (años):Q", format=".1f")])
        regla = alt.Chart(pd.DataFrame({"x": [edad]})).mark_rule(color="#1565C0", strokeDash=[5, 4], size=2).encode(x="x:Q")
        st.altair_chart((puntos + regla).properties(height=34 * len(df) + 60), width="stretch")
        st.download_button("⬇️ Descargar lección nivelada (CSV)", df.to_csv(index_label="orden").encode("utf-8-sig"),
                           file_name=f"leccion_nivelada_{L}.csv", mime="text/csv")

# =========================================================================== TAB 4
with tab4:
    st.subheader("Cómo se eligió el modelo")
    t = MET["test_en"]["Gradient Boosting"]
    c = st.columns(5)
    c[0].metric("MAE test EN · meta ≤ 1,6", f"{t['MAE test']:.2f} años")
    c[1].metric("R² test · meta ≥ 0,55", f"{t['R²']:.2f}")
    c[2].metric("Nivel ±1 · meta ≥ 90 %", f"{t['nivel ±1']:.1%}")
    c[3].metric("Error grave · meta ≤ 2 %", f"{t['error grave']:.2%}")
    c[4].metric("Brecha train–val. · meta ≤ 0,30", f"{MET['cv_repetida_en']['Gradient Boosting']['brecha']:.2f} años")

    a, b = st.columns(2)
    with a:
        st.markdown("**Validación cruzada repetida 5 × 3 (inglés)**")
        cv = pd.DataFrame(MET["cv_repetida_en"]).T[["MAE media", "MAE d.e.", "R² media", "brecha", "t. ajuste (s)"]]
        st.dataframe(cv.style.format("{:.3f}").highlight_min(subset=["MAE media"], color="#C8E6C9"), width="stretch")
        st.caption("Stacking gana por 0,001 años (≈ 9 horas): sin relevancia práctica. Se elige **Gradient Boosting**, "
                   "33 veces más rápido de entrenar y con menor brecha.")
    with b:
        st.markdown("**Español: tres estrategias (CV 5 × 5)**")
        tes = pd.DataFrame(MET["espanol"]["tabla"]).T[["MAE", "R²", "Spearman"]].astype(float)
        st.dataframe(tes.style.format("{:.3f}", na_rep="—"), width="stretch")
        st.caption("C = modelo propio + conocimiento del inglés (AoA de la traducción y predicción del modelo inglés).")
    st.markdown("**Hiperparámetros del modelo elegido**")
    st.json(MET["hiperparametros"]["Gradient Boosting"], expanded=False)
    img = motor.RAIZ / "images"
    g1, g2 = st.columns(2)
    g1.image(str(img / "07_generalizacion_cv_repetida.png"), caption="Generalización: CV repetida y brecha train–validación")
    g2.image(str(img / "09_evaluacion_test.png"), caption="Test: palabras nunca vistas")
    st.caption("Datos: Kuperman et al. (2012), Brysbaert et al. (2014), Alonso et al. (2015), Cuetos et al. (2011), "
               "CMU Pronouncing Dictionary, MultiPic (Duñabeitia et al., 2022).")
