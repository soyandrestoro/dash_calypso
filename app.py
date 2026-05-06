import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(
    page_title="Dashboard Energético",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Constantes ────────────────────────────────────────────────────────────────

MESES_COLS = ['nov-2025', 'dic-2025', 'ene-2026', 'feb-2026', 'mar-2026', 'abr-2026']
MESES_KEYS = ['2025-11', '2025-12', '2026-01', '2026-02', '2026-03', '2026-04']
MESES_LABEL = {
    '2025-11': 'Noviembre',
    '2025-12': 'Diciembre',
    '2026-01': 'Enero',
    '2026-02': 'Febrero',
    '2026-03': 'Marzo',
    '2026-04': 'Abril',
}
MESES_TARIFA = {
    '2025-11': 'noviembre 1, 2025',
    '2025-12': 'diciembre 1, 2025',
    '2026-01': 'enero 1, 2026',
    '2026-02': 'febrero 1, 2026',
    '2026-03': 'marzo 1, 2026',
    '2026-04': 'abril 1, 2026',
}

# (Nombre en columna Operador del CSV de consumo) → archivo de tarifas
OPERADORES = {
    'Afinia':       'Tarifas Calypso - Completo.xlsx - Afinia Tarifas.csv',
    'Aire':         'Tarifas Calypso - Completo.xlsx - Aire Tarifas.csv',
    'Celsia':       'Tarifas Calypso - Completo.xlsx - Celsia Tarifas.csv',
    'Cens':         'Tarifas Calypso - Completo.xlsx - Cens Tarifas.csv',
    'Chec':         'Tarifas Calypso - Completo.xlsx - Chec Tarifas.csv',
    'Electrohuila': 'Tarifas Calypso - Completo.xlsx - Electrohuila Tarifas.csv',
    'Enel':         'Tarifas Calypso - Completo.xlsx - Enel Tarifas.csv',
    'Epm':          'Tarifas Calypso - Completo.xlsx - Epm Tarifas.csv',
    'Neu':          'Tarifas Calypso - Completo.xlsx - Neu Tarifas.csv',
    'Qi Energy':    'Tarifas Calypso - Completo.xlsx - Qi Energy Tarifas.csv',
    'Vatia':        'Tarifas Calypso - Completo.xlsx - Vatia Tarifas .csv',
}

CONSUMOS_FILES = {
    'Afinia':       'Fronterias Calypso Act - Afinia.csv',
    'Aire':         'Fronterias Calypso Act - Aire.csv',
    'Celsia':       'Fronterias Calypso Act - Celsia.csv',
    'Cens':         'Fronterias Calypso Act - Cens.csv',
    'Chec':         'Fronterias Calypso Act - Chec.csv',
    'Electrohuila': 'Fronterias Calypso Act - Electrohuila.csv',
    'Enel':         'Fronterias Calypso Act - Enel.csv',
    'Epm':          'Fronterias Calypso Act - Epm.csv',
    'Neu':          'Fronterias Calypso Act - Neu.csv',
    'Qi Energy':    'Fronterias Calypso Act - Qi Energy.csv',
    'Vatia':        'Fronterias Calypso Act - Vatia.csv',
}

TODOS_ARCHIVOS = list(CONSUMOS_FILES.values()) + list(OPERADORES.values())

# ── Helpers ───────────────────────────────────────────────────────────────────

def limpiar_num_es(v):
    """Número con punto como separador de miles y coma como decimal → float."""
    if pd.isna(v):
        return 0.0
    s = str(v).strip()
    if not s:
        return 0.0
    s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0

def mtimes_csv():
    result = []
    for f in TODOS_ARCHIVOS:
        try:
            result.append(os.path.getmtime(f))
        except FileNotFoundError:
            result.append(0)
    return tuple(result)

# ── Carga ─────────────────────────────────────────────────────────────────────

@st.cache_data
def cargar_datos(mtimes):
    # 1. Tarifas: (operador, nivel_normalizado, mes_tarifa) → (tarifa_op, tarifa_bia)
    tarifas = {}
    for op, fname in OPERADORES.items():
        try:
            raw = pd.read_csv(fname, header=None, dtype=str)
        except FileNotFoundError:
            continue

        # Identificar filas de cabecera (contienen 'Mes' en la primera celda)
        header_rows = raw[raw.iloc[:, 0].str.strip().str.lower() == 'mes'].index.tolist()

        for i, h_idx in enumerate(header_rows):
            next_h = header_rows[i + 1] if i + 1 < len(header_rows) else len(raw)
            bloque = raw.iloc[h_idx + 1: next_h].copy()
            bloque.columns = raw.iloc[h_idx].str.strip().tolist()
            bloque = bloque.dropna(subset=[bloque.columns[0]])
            bloque = bloque[bloque.iloc[:, 0].str.strip() != '']

            col_nivel = bloque.columns[1]
            col_op    = bloque.columns[2]
            col_bia   = bloque.columns[3]

            for _, row in bloque.iterrows():
                mes_str = str(row[bloque.columns[0]]).strip().strip('"')
                nivel   = str(row[col_nivel]).strip()
                t_op    = limpiar_num_es(row[col_op])
                t_bia   = limpiar_num_es(row[col_bia])
                tarifas[(op, nivel, mes_str)] = (t_op, t_bia)

    # 2. Consumos
    registros = []
    for op, fname in CONSUMOS_FILES.items():
        try:
            df_raw = pd.read_csv(fname, dtype=str, encoding='latin1')
        except FileNotFoundError:
            continue

        df_raw.columns = [c.strip() for c in df_raw.columns]
        df_raw = df_raw.dropna(subset=[df_raw.columns[0]])
        df_raw = df_raw[df_raw.iloc[:, 0].str.strip() != '']

        # Columna de sede siempre es la primera
        col_sede = df_raw.columns[0]
        # Nivel en tarifa: los nuevos archivos tienen "1" → usar "1 Usuario"
        nivel_tarifa = '1 Usuario'

        for _, row in df_raw.iterrows():
            sede = str(row[col_sede]).strip()

            for mes_col, mes_key in zip(MESES_COLS, MESES_KEYS):
                if mes_col not in df_raw.columns:
                    continue
                try:
                    consumo = float(str(row[mes_col]).strip().replace(',', '.'))
                except (ValueError, AttributeError):
                    consumo = 0.0
                if consumo <= 0:
                    continue

                mes_tarifa = MESES_TARIFA[mes_key]
                t = tarifas.get((op, nivel_tarifa, mes_tarifa))
                if t is None:
                    for k in tarifas:
                        if k[0] == op and k[1].strip() == nivel_tarifa and k[2] == mes_tarifa:
                            t = tarifas[k]
                            break
                if t is None:
                    continue

                tarifa_op, tarifa_bia = t
                costo_op  = consumo * tarifa_op
                costo_bia = consumo * tarifa_bia
                ahorro    = costo_op - costo_bia

                registros.append({
                    'sede':       sede,
                    'operador':   op,
                    'nivel':      nivel_tarifa,
                    'mes':        mes_key,
                    'consumo':    consumo,
                    'tarifa_op':  tarifa_op,
                    'tarifa_bia': tarifa_bia,
                    'costo_op':   costo_op,
                    'costo_bia':  costo_bia,
                    'ahorro':     ahorro,
                })

    return pd.DataFrame(registros)

df = cargar_datos(mtimes_csv())

# ── Header ────────────────────────────────────────────────────────────────────

logo_path = "Bia-energy-1-1024x597.webp"
if os.path.exists(logo_path):
    col_logo, col_title = st.columns([1, 6])
    with col_logo:
        st.image(logo_path, width=120)
    with col_title:
        st.markdown("## Dashboard Energético")
        st.markdown("**Calypso** | Distribuidor vs BIA | Nov 2025 – Abr 2026")
else:
    st.title("⚡ Dashboard Energético")
    st.markdown("**Calypso** | Distribuidor vs BIA | Nov 2025 – Abr 2026")

st.markdown("---")

# ── Filtros ───────────────────────────────────────────────────────────────────

if 'ultimo_op' not in st.session_state:
    st.session_state.ultimo_op = ""
if 'ultimo_nivel' not in st.session_state:
    st.session_state.ultimo_nivel = ""

def reiniciar_filtros():
    st.session_state['busqueda_widget']       = ""
    st.session_state['op_widget']             = "Todos"
    st.session_state['nivel_widget']          = "Todos"
    st.session_state['sede_widget']           = "Todos"
    st.session_state['mes_widget']            = "Todos"
    st.session_state['heatmap_sedes_widget']  = []
    st.session_state['detalle_sedes_widget']  = []
    st.session_state['ranking_sede_widget']   = "Todos"
    st.session_state.ultimo_op    = ""
    st.session_state.ultimo_nivel = ""

st.markdown("""
<style>
div[data-testid="stForm"], .filtros-box {
    background: #0e1117;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 10px;
    padding: 18px 20px 10px 20px;
    margin-bottom: 16px;
}
div[data-baseweb="select"] > div {
    background-color: #1c2333 !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 6px !important;
}
div[data-baseweb="input"] > div {
    background-color: #1c2333 !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 6px !important;
}
</style>
<div class="filtros-box">
""", unsafe_allow_html=True)

col_titulo, col_btn = st.columns([6, 1])
with col_titulo:
    st.markdown("### 🔎 Filtros")
with col_btn:
    st.markdown("<div style='padding-top:28px'>", unsafe_allow_html=True)
    st.button("✕ Limpiar", on_click=reiniciar_filtros, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

busqueda = st.text_input("Buscar por sede",
                         placeholder="Ej: ENGATIVA", key="busqueda_widget")

c1, c2, c3, c4 = st.columns(4)

TODOS = "Todos"

with c1:
    op_opts = [TODOS] + sorted(df['operador'].unique().tolist())
    op_sel  = st.selectbox("Operador / Distribuidor", op_opts, index=0, key="op_widget")
    operador = "" if op_sel == TODOS else op_sel

# Reset cascada: operador → nivel
if operador != st.session_state.ultimo_op:
    st.session_state.ultimo_op = operador
    for k in ('nivel_widget', 'sede_widget'):
        if k in st.session_state:
            del st.session_state[k]
    st.session_state.ultimo_nivel = ""

pool_op = df if not operador else df[df['operador'] == operador]

with c2:
    niv_opts = [TODOS] + sorted(pool_op['nivel'].unique().tolist())
    niv_sel  = st.selectbox("Nivel de Tensión", niv_opts, index=0, key="nivel_widget")
    nivel    = "" if niv_sel == TODOS else niv_sel

# Reset cascada: nivel → sede
if nivel != st.session_state.ultimo_nivel:
    st.session_state.ultimo_nivel = nivel
    if 'sede_widget' in st.session_state:
        del st.session_state['sede_widget']

pool_niv   = pool_op if not nivel else pool_op[pool_op['nivel'] == nivel]
sedes_disp = [TODOS] + sorted(pool_niv['sede'].astype(str).unique().tolist())

with c3:
    sede_sel = st.selectbox("Sede", sedes_disp, index=0, key="sede_widget")
    sede     = "" if sede_sel == TODOS else sede_sel

with c4:
    mes_opts = [TODOS] + MESES_KEYS
    mes_sel  = st.selectbox("Mes", mes_opts, index=0,
                            format_func=lambda x: MESES_LABEL.get(x, x) if x != TODOS else TODOS,
                            key="mes_widget")
    mes = "" if mes_sel == TODOS else mes_sel

st.markdown("</div>", unsafe_allow_html=True)

# Aplicar filtros
filtrado = df.copy()
if busqueda:
    filtrado = filtrado[filtrado['sede'].str.contains(busqueda, case=False, na=False)]
if operador:
    filtrado = filtrado[filtrado['operador'] == operador]
if nivel:
    filtrado = filtrado[filtrado['nivel'] == nivel]
if sede:
    filtrado = filtrado[filtrado['sede'].astype(str) == sede]
if mes:
    filtrado = filtrado[filtrado['mes'] == mes]

st.markdown("---")
partes = []
if busqueda:  partes.append(f"**Búsqueda:** {busqueda}")
if operador:  partes.append(f"**Operador:** {operador}")
if nivel:     partes.append(f"**Nivel:** {nivel}")
if sede:      partes.append(f"**Sede:** {sede}")
if mes:       partes.append(f"**Mes:** {MESES_LABEL.get(mes, mes)}")
prefijo = "Filtros activos: " + " • ".join(partes) if partes else "Mostrando todos los datos"
st.info(f"{prefijo} • **{len(filtrado)} registros**")

# ── Tarjetas ──────────────────────────────────────────────────────────────────

total_consumo = filtrado['consumo'].sum()
total_op      = filtrado['costo_op'].sum()
total_bia     = filtrado['costo_bia'].sum()
ahorro_total  = filtrado['ahorro'].sum()

st.markdown("### Resumen")
c1, c2, c3, c4 = st.columns(4)

c1.metric("Consumo", f"{total_consumo:,.0f} kWh",
          help="Energía total en el período seleccionado")
c2.metric("Costo con Distribuidor", f"${total_op:,.0f}",
          help="Costo total pagando tarifa del distribuidor")
c3.metric("Costo con BIA", f"${total_bia:,.0f}",
          help="Costo total pagando tarifa BIA")

if ahorro_total > 0:
    delta_color = "normal"
    delta_txt   = f"${ahorro_total:,.0f} ahorrado"
else:
    delta_color = "inverse"
    delta_txt   = f"${abs(ahorro_total):,.0f} más caro"

c4.metric("Ahorro vs Distribuidor", f"${ahorro_total:,.0f}",
          delta=delta_txt, delta_color=delta_color,
          help="Distribuidor − BIA. Positivo = BIA más barato")

# ── Gráficos ──────────────────────────────────────────────────────────────────

if len(filtrado) > 0:
    st.markdown("---")
    st.markdown("### Visualizaciones")

    # ── Tarifas por mes ───────────────────────────────────────────────────────
    st.markdown("#### Comportamiento de Tarifas ($/kWh)")

    tarifas_mes = (
        filtrado
        .groupby(['mes', 'operador', 'nivel'], as_index=False)
        .agg(tarifa_op=('tarifa_op', 'first'), tarifa_bia=('tarifa_bia', 'first'))
        .sort_values(['operador', 'nivel', 'mes'])
    )

    PALETTE_OP = ['#FFB627', '#FF7F50', '#FF4F7B', '#C878E0',
                  '#7555F3', '#09B4CC', '#2ECC71', '#F1C40F',
                  '#E67E22', '#E74C3C']
    PALETTE_BIA = ['#0080FF', '#00BCD4', '#00E5FF', '#69F0AE',
                   '#B2FF59', '#FFFF00', '#FFD740', '#FF6E40',
                   '#FF1744', '#D500F9']

    combos = tarifas_mes.groupby(['operador', 'nivel']).size().index.tolist()

    fig_tarifas = go.Figure()
    for idx, (op, niv) in enumerate(combos):
        sub = tarifas_mes[(tarifas_mes['operador'] == op) & (tarifas_mes['nivel'] == niv)]
        c_op  = PALETTE_OP[idx % len(PALETTE_OP)]
        c_bia = PALETTE_BIA[idx % len(PALETTE_BIA)]
        lbl   = f"{op} · {niv}"
        fig_tarifas.add_trace(go.Scatter(
            x=sub['mes'], y=sub['tarifa_op'],
            mode='lines+markers', name=f'Dist. · {lbl}',
            line=dict(color=c_op, width=1.5, shape='spline'),
            marker=dict(size=5, symbol='circle', color=c_op),
            hovertemplate='$%{y:,.2f}/kWh<extra>Dist. · ' + lbl + '</extra>',
        ))
        fig_tarifas.add_trace(go.Scatter(
            x=sub['mes'], y=sub['tarifa_bia'],
            mode='lines+markers', name=f'BIA · {lbl}',
            line=dict(color=c_bia, width=1.5, dash='dot', shape='spline'),
            marker=dict(size=5, symbol='diamond', color=c_bia),
            hovertemplate='$%{y:,.2f}/kWh<extra>BIA · ' + lbl + '</extra>',
        ))

    fig_tarifas.update_layout(
        hovermode='x unified', template='plotly_dark', height=380,
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', yanchor='bottom', y=1.04,
                    xanchor='left', x=0, font=dict(size=10),
                    bgcolor='rgba(0,0,0,0)', borderwidth=0),
        xaxis=dict(title='', tickfont=dict(size=11), showgrid=True,
                   gridcolor='rgba(140,155,176,0.12)', zeroline=False),
        yaxis=dict(title='$/kWh', tickfont=dict(size=11), tickformat='$,.0f',
                   showgrid=True, gridcolor='rgba(140,155,176,0.12)', zeroline=False),
        margin=dict(t=10, b=40, l=70, r=20),
        hoverlabel=dict(bgcolor='#101525', bordercolor='#1A2035', font=dict(size=12)),
    )
    st.plotly_chart(fig_tarifas, use_container_width=True)

    por_mes = (
        filtrado
        .groupby('mes', as_index=False)
        .agg(
            ahorro=('ahorro', 'sum'),
            costo_op=('costo_op', 'sum'),
            costo_bia=('costo_bia', 'sum'),
            consumo=('consumo', 'sum'),
        )
        .sort_values('mes')
    )

    # ── Waterfall de ahorro ───────────────────────────────────────────────────
    meses_wf   = list(por_mes['mes']) + ['Total']
    valores_wf = list(por_mes['ahorro'])
    medidas_wf = ['relative'] * len(por_mes) + ['total']
    textos_wf  = [f"${v:,.0f}" for v in por_mes['ahorro']] + [f"${sum(por_mes['ahorro']):,.0f}"]

    fig_wf = go.Figure(go.Waterfall(
        orientation='v', measure=medidas_wf, x=meses_wf,
        y=valores_wf + [0], text=textos_wf,
        textposition='outside', textfont=dict(size=11),
        connector=dict(line=dict(color='#8C9BB0', width=1)),
        increasing=dict(marker=dict(color='#2ECC71')),
        decreasing=dict(marker=dict(color='#E74C3C')),
        totals=dict(marker=dict(color='#7555F3')),
    ))
    fig_wf.update_layout(
        title='Ahorro Mensual (Distribuidor − BIA)',
        xaxis_title='Mes', yaxis_title='Monto ($)',
        template='plotly_dark', height=420, showlegend=False,
    )
    st.plotly_chart(fig_wf, use_container_width=True)

    # ── Heatmap + Participación de Sede ──────────────────────────────────────
    por_sede = (
        filtrado
        .groupby('sede', as_index=False)
        .agg(consumo=('consumo', 'sum'), ahorro=('ahorro', 'sum'),
             operador=('operador', 'first'), nivel=('nivel', 'first'))
    )

    st.info("🗺️ **Mapa de calor:** Cada celda muestra el ahorro de una sede en un mes. "
            "**Verde** = BIA es más barato que el distribuidor. "
            "**Rojo** = el distribuidor resultó más barato ese mes. "
            "Selecciona las sedes que quieres comparar.")

    sedes_disp_hm = sorted(filtrado['sede'].astype(str).unique().tolist())
    sedes_hm = st.multiselect(
        "Sedes en el mapa de calor",
        options=sedes_disp_hm, default=[],
        placeholder="Selecciona una o varias sedes para visualizar…",
        key="heatmap_sedes_widget",
    )

    c1, c2 = st.columns(2)

    with c1:
        if not sedes_hm:
            st.info("Selecciona al menos una sede arriba para ver el mapa de calor.")
        else:
            df_hm = filtrado[filtrado['sede'].astype(str).isin(sedes_hm)]
            pivot = df_hm.pivot_table(
                index='sede', columns='mes', values='ahorro',
                aggfunc='sum', fill_value=0,
            )
            cols_ord = [m for m in MESES_KEYS if m in pivot.columns]
            pivot = pivot[cols_ord]
            pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=True).index]

            fig_hm = go.Figure(go.Heatmap(
                z=pivot.values, x=list(pivot.columns),
                y=[str(c) for c in pivot.index],
                colorscale=[[0.0, '#E74C3C'], [0.5, '#101525'], [1.0, '#2ECC71']],
                zmid=0, hoverongaps=False,
                hovertemplate='<b>%{y}</b><br>Mes: %{x}<br>Ahorro: $%{z:,.0f}<extra></extra>',
                colorbar=dict(title='Ahorro ($)', tickformat='$,.0f'),
            ))
            fig_hm.update_layout(
                title='Ahorro por Sede y Mes',
                xaxis_title='Mes', yaxis_title='',
                template='plotly_dark',
                height=max(300, len(pivot) * 40 + 100),
            )
            st.plotly_chart(fig_hm, use_container_width=True)

    with c2:
        st.markdown("**Participación de Sede**")
        st.info("📊 **¿Qué mide este panel?** Muestra cuánto representa una sede dentro del **total de todas las sedes y operadores**. Los porcentajes no cambian con los filtros — siempre reflejan el peso real de esa sede en el universo completo.")
        ranking = por_sede.sort_values('ahorro', ascending=False)
        sede_opts = ["Todos"] + ranking['sede'].astype(str).tolist()
        sede_sel = st.selectbox("Selecciona una sede", sede_opts, index=0,
                                key="ranking_sede_widget")

        if sede_sel == "Todos":
            st.info("Selecciona una sede para ver su participación en el resultado global.")
        else:
            det = filtrado[filtrado['sede'].astype(str) == sede_sel]
            niv_sede  = det['nivel'].iloc[0]    if len(det) else '—'
            op_sede   = det['operador'].iloc[0] if len(det) else '—'
            s_consumo = det['consumo'].sum()
            s_ahorro  = det['ahorro'].sum()
            s_op      = det['costo_op'].sum()
            s_bia     = det['costo_bia'].sum()

            g_consumo = df['consumo'].sum()
            g_ahorro  = df['ahorro'].sum()
            g_op      = df['costo_op'].sum()
            g_bia     = df['costo_bia'].sum()

            def _pct(a, b): return round(a / b * 100, 1) if b else 0.0

            p_consumo = _pct(s_consumo, g_consumo)
            p_ahorro  = _pct(s_ahorro,  g_ahorro)
            p_op      = _pct(s_op,      g_op)
            p_bia     = _pct(s_bia,     g_bia)

            c_ahorro = '#2ECC71' if s_ahorro >= 0 else '#E74C3C'
            st.markdown(
                f"<span style='color:#8C9BB0;font-size:0.82em'>{op_sede} · {niv_sede}</span>&nbsp;&nbsp;"
                f"<span style='color:{c_ahorro};font-weight:600'>Ahorro: ${s_ahorro:,.0f}</span>",
                unsafe_allow_html=True,
            )

            ma, mb = st.columns(2)
            ma.metric("⚡ Consumo",        f"{p_consumo:.1f}%", f"{s_consumo:,.0f} kWh", delta_color="off")
            mb.metric("💰 Ahorro",         f"{p_ahorro:.1f}%",  f"${s_ahorro:,.0f}",     delta_color="off")
            mc, md = st.columns(2)
            mc.metric("🔴 Costo Dist.",    f"{p_op:.1f}%",      f"${s_op:,.0f}",         delta_color="off")
            md.metric("🟢 Costo BIA",      f"{p_bia:.1f}%",     f"${s_bia:,.0f}",        delta_color="off")

            labels = ['Consumo', 'Ahorro', 'Costo Dist.', 'Costo BIA']
            vals   = [p_consumo, p_ahorro, p_op, p_bia]
            colors = ['#09B4CC', c_ahorro, '#FFB627', '#7555F3']

            fig_p = go.Figure()
            fig_p.add_trace(go.Bar(x=[100] * 4, y=labels, orientation='h',
                                   marker_color='rgba(140,155,176,0.1)',
                                   showlegend=False, hoverinfo='skip'))
            fig_p.add_trace(go.Bar(x=vals, y=labels, orientation='h',
                                   marker_color=colors,
                                   text=[f"{v:.1f}%" for v in vals],
                                   textposition='inside',
                                   textfont=dict(size=12, color='#FFFFFF'),
                                   showlegend=False,
                                   hovertemplate='%{y}: %{x:.1f}%<extra></extra>'))
            fig_p.update_layout(
                barmode='overlay', template='plotly_dark', height=240,
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(range=[0, 100], showgrid=False, showticklabels=False, zeroline=False),
                yaxis=dict(showgrid=False, tickfont=dict(size=11)),
                margin=dict(t=0, b=10, l=110, r=20),
            )
            st.plotly_chart(fig_p, use_container_width=True)

    c1, c2 = st.columns(2)

    with c1:
        fig = go.Figure([
            go.Bar(x=por_mes['mes'], y=por_mes['costo_op'],
                   name='Distribuidor', marker_color='#7555F3',
                   text=[f"${v:,.0f}" for v in por_mes['costo_op']],
                   textposition='outside', textfont=dict(size=10, color='#8C9BB0'),
                   hovertemplate='Dist. %{x}: $%{y:,.0f}<extra></extra>'),
            go.Bar(x=por_mes['mes'], y=por_mes['costo_bia'],
                   name='BIA', marker_color='#09B4CC',
                   text=[f"${v:,.0f}" for v in por_mes['costo_bia']],
                   textposition='outside', textfont=dict(size=10, color='#8C9BB0'),
                   hovertemplate='BIA %{x}: $%{y:,.0f}<extra></extra>'),
        ])
        fig.update_layout(
            title="Costo Comparativo (Distribuidor vs BIA)",
            xaxis_title="", yaxis_title="$",
            barmode='group', hovermode='x unified',
            template='plotly_dark', height=420,
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation='h', yanchor='top', y=-0.15, xanchor='center', x=0.5,
                        bgcolor='rgba(0,0,0,0)', borderwidth=0),
            yaxis=dict(showgrid=True, gridcolor='rgba(140,155,176,0.12)', zeroline=False),
            xaxis=dict(showgrid=False),
            margin=dict(t=40, b=60, l=60, r=20),
            uniformtext=dict(mode='hide', minsize=9),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        por_mes['acumulado'] = por_mes['ahorro'].cumsum()
        fig = go.Figure([
            go.Scatter(x=por_mes['mes'], y=por_mes['acumulado'],
                       mode='lines+markers', name='Acumulado',
                       line=dict(color='#09B4CC', width=3), fill='tozeroy')
        ])
        fig.update_layout(
            title="Ahorro Acumulado por Período",
            xaxis_title="Mes", yaxis_title="$ Acumulado",
            hovermode='x', template='plotly_dark', height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Tabla detallada ───────────────────────────────────────────────────────
    st.markdown("---")
    col_tit, col_filt = st.columns([2, 3])
    with col_tit:
        st.markdown("### Detalle de Datos")
    with col_filt:
        sedes_tabla_opts = sorted(filtrado['sede'].astype(str).unique().tolist())
        sedes_tabla_sel  = st.multiselect(
            "sede_detalle", options=sedes_tabla_opts, default=[],
            placeholder="Filtrar por sede — global si no seleccionas",
            key="detalle_sedes_widget", label_visibility="collapsed",
        )

    base_filtrado = (
        filtrado if not sedes_tabla_sel
        else filtrado[filtrado['sede'].astype(str).isin(sedes_tabla_sel)]
    )

    tabla = base_filtrado[[
        'sede', 'operador', 'nivel', 'mes', 'consumo',
        'tarifa_op', 'tarifa_bia', 'costo_op', 'costo_bia', 'ahorro',
    ]].copy()

    tabla.columns = [
        'Sede', 'Operador', 'Nivel', 'Mes', 'Consumo (kWh)',
        'Tarifa Dist. ($/kWh)', 'Tarifa BIA ($/kWh)',
        'Costo Distribuidor ($)', 'Costo BIA ($)', 'Ahorro ($)',
    ]

    tabla['Consumo (kWh)']        = tabla['Consumo (kWh)'].apply(lambda x: f"{x:,.0f}")
    tabla['Tarifa Dist. ($/kWh)'] = tabla['Tarifa Dist. ($/kWh)'].apply(lambda x: f"${x:,.2f}")
    tabla['Tarifa BIA ($/kWh)']   = tabla['Tarifa BIA ($/kWh)'].apply(lambda x: f"${x:,.2f}")
    for col in ['Costo Distribuidor ($)', 'Costo BIA ($)', 'Ahorro ($)']:
        tabla[col] = tabla[col].apply(lambda x: f"${x:,.0f}")

    st.dataframe(tabla, use_container_width=True, hide_index=True)
    st.download_button("📥 Descargar como CSV", tabla.to_csv(index=False),
                       "dashboard_energetico.csv", "text/csv")

else:
    st.warning("No hay registros que coincidan con los filtros seleccionados.")

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown("---")
n_sedes     = df['sede'].nunique()
n_registros = len(df)
st.markdown(f"""
<div style='text-align:center;color:#8C9BB0;font-size:0.9em'>
    Dashboard Energético • Nov 2025 – Abr 2026 • {n_sedes} Sedes • {n_registros} Registros
</div>
""", unsafe_allow_html=True)
