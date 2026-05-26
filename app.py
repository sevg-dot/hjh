
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import warnings
import os

warnings.filterwarnings("ignore")

# ── Colores UCLA ─────────────────────────────────────────────────────────────
BLUE   = "#007B99"
ORANGE = "#F39200"
GREY   = "#848585"
PALETTE = [BLUE, ORANGE, GREY, "#A9D6E5", "#F9C784", "#5BA4CF", "#E8A838"]

st.set_page_config(
    page_title="Dashboard IT — Funlam",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
  .block-container { padding-top: 1rem; }
  .header-bar {
    background: linear-gradient(135deg, #007B99, #005f78);
    padding: 1rem 1.5rem; border-radius: 10px; margin-bottom: 1.2rem;
  }
  .header-bar h1 { color: white; margin: 0; font-size: 1.5rem; font-weight: 700; }
  .header-bar p  { color: rgba(255,255,255,0.8); margin: 0; font-size: 0.85rem; }
  .kpi { background:white; border-radius:10px; padding:1rem 1.2rem;
         border-left:5px solid #007B99; box-shadow:0 2px 8px rgba(0,0,0,0.08); }
  .kpi.or { border-left-color:#F39200; }
  .kpi.gr { border-left-color:#28a745; }
  .kpi.gy { border-left-color:#848585; }
  .kpi.rd { border-left-color:#dc3545; }
  .kpi-label { font-size:0.72rem; color:#848585; text-transform:uppercase;
               letter-spacing:.05em; font-weight:600; }
  .kpi-value { font-size:1.9rem; font-weight:800; color:#1a1a2e; line-height:1.1; }
  .kpi-sub   { font-size:0.73rem; color:#848585; margin-top:2px; }
  .stTabs [data-baseweb="tab"] { font-weight:600; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-bar">
  <h1>🖥️ Dashboard de Infraestructura Tecnológica</h1>
  <p>Universidad Católica Luis Amigó · Departamento de Infraestructura TI · ISE009 Big Data</p>
  <p><small>Sugerencia: El modo claro permite una mayor armonía visual</small></p>
</div>
""", unsafe_allow_html=True)

# ── KPI helper ────────────────────────────────────────────────────────────────
def kpi(label, value, sub="", variant=""):
    st.markdown(f"""
    <div class="kpi {variant}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

# ── Funciones de Carga de Datos ──────────────────────────────────────────
@st.cache_data(show_spinner=False)
def cargar_datos_procesados(uploaded_tickets, uploaded_inventario, uploaded_software, uploaded_actividades):
    def detectar_header(xl, hoja, max_filas=6):
        df_raw = xl.parse(hoja, header=None, nrows=max_filas)
        mejor_fila, mejor_score = 0, -1
        for i, row in df_raw.iterrows():
            score = sum(2 if isinstance(v, str) and v.strip() else
                        1 if pd.notna(v) else 0 for v in row)
            if score > mejor_score:
                mejor_score, mejor_fila = score, i
        return int(mejor_fila)

    def leer_hoja(xl, hoja, h=None):
        h = h if h is not None else detectar_header(xl, hoja)
        df = xl.parse(hoja, header=h).dropna(how="all").dropna(axis=1, how="all")
        cols = [str(c).strip() if not str(c).startswith("Unnamed") else f"_col_{i}"
                for i, c in enumerate(df.columns)]
        df.columns = cols
        df = df[[c for c in cols if not c.startswith("_col_")]]
        return df.reset_index(drop=True)

    # reparar encoding
    def fix_mojibake(text):
        if isinstance(text, str):
            try:
                return text.encode("latin1").decode("utf-8")
            except (UnicodeDecodeError, UnicodeEncodeError):
                return text
        return text

    # Inicializar DataFrames vacíos para evitar errores si no se cargan todos
    con = pd.DataFrame()
    det = pd.DataFrame()
    inv = pd.DataFrame()
    eventos = pd.DataFrame()
    ups = pd.DataFrame()
    sw = pd.DataFrame()
    act = pd.DataFrame()

    if uploaded_tickets:
        xl_t = pd.ExcelFile(uploaded_tickets)
        det  = leer_hoja(xl_t, "DETALLADO", h=0)
        for col in det.select_dtypes("object").columns:
            det[col] = det[col].apply(fix_mojibake)
        det["Fecha de Creación"] = pd.to_datetime(
            det.get("Fecha de Creación", det.get("Fecha de CreaciÃ³n", pd.NaT)), errors="coerce")
        det["mes"]        = det["Fecha de Creación"].dt.month
        det["año"]        = det["Fecha de Creación"].dt.year
        det["mes_label"]  = det["Fecha de Creación"].dt.strftime("%b %Y")
        det["dia_semana"] = det["Fecha de Creación"].dt.day_name()
        con = leer_hoja(xl_t, "CONSOLIDADO")

    if uploaded_inventario:
        xl_i = pd.ExcelFile(uploaded_inventario)
        def inv_hoja(hoja, tipo):
            d = leer_hoja(xl_i, hoja)
            d["TIPO_EQUIPO"] = tipo
            return d
        inv = pd.concat([
            inv_hoja("Servidores",          "Servidor"),
            inv_hoja("Switches de datos",   "Switch"),
            inv_hoja("Access Point",        "Access Point"),
            inv_hoja("Seguridad Perimetral","Seguridad Perimetral"),
            inv_hoja("UPS",                 "UPS"),
        ], ignore_index=True)
        eventos = leer_hoja(xl_i, "Registro y Gestión")
        ups = leer_hoja(xl_i, "UPS")
        if "FECHA ÚLTIMO CAMBIO DE BATERÍAS" in ups.columns:
            ups["FECHA ÚLTIMO CAMBIO DE BATERÍAS"] = pd.to_datetime(
                ups["FECHA ÚLTIMO CAMBIO DE BATERÍAS"], errors="coerce")
            ups["dias_desde_cambio"] = (pd.Timestamp.now() - ups["FECHA ÚLTIMO CAMBIO DE BATERÍAS"]).dt.days

    if uploaded_software:
        xl_s = pd.ExcelFile(uploaded_software)
        def prep_sw(hoja, cat):
            d = leer_hoja(xl_s, hoja)
            d["CATEGORIA"] = cat
            if "FECHA DE VENCIMIENTO" in d.columns:
                d["FECHA DE VENCIMIENTO"] = pd.to_datetime(d["FECHA DE VENCIMIENTO"], errors="coerce")
                d["dias_para_vencer"] = (d["FECHA DE VENCIMIENTO"] - pd.Timestamp.now()).dt.days
                d["estado_licencia"] = d["dias_para_vencer"].apply(
                    lambda x: "Sin fecha" if pd.isna(x) else
                              "Vencida" if x < 0 else
                              "Por vencer (<60d)" if x <= 60 else "Vigente")
            return d
        sw = pd.concat([prep_sw("SOTWARE EDUCACION",  "Educativo"),
                        prep_sw("SOTWARE OPERACIONAL", "Operacional")], ignore_index=True)

    if uploaded_actividades:
        xl_a = pd.ExcelFile(uploaded_actividades)
        act  = leer_hoja(xl_a, xl_a.sheet_names[0], h=0)
        for col in ["Fecha de creación", "Fecha estimada de cierre", "Fecha real de cierre"]:
            if col in act.columns:
                act[col] = pd.to_datetime(act[col], errors="coerce")
        if {"Fecha real de cierre","Fecha estimada de cierre"} <= set(act.columns):
            act["dias_retraso"] = (act["Fecha real de cierre"] - act["Fecha estimada de cierre"]).dt.days

    return con, det, inv, eventos, ups, sw, act


# ════════════════════════════════════════════════════════════════════
# UPLOAD FILES
# ════════════════════════════════════════════════════════════════════
st.sidebar.header("📂 Cargar Archivos Excel")
uploaded_tickets = st.sidebar.file_uploader("Cargar Tickets (tickets.xlsx)", type=["xlsx"]) # , help="tickets (1).xlsx")
uploaded_inventario = st.sidebar.file_uploader("Cargar Inventario (01.Inventario Infraestructura de Misión Crítica.xlsx)", type=["xlsx"]) # , help="01.Inventario Infraestructura de Misión Crítica (1).xlsx")
uploaded_software = st.sidebar.file_uploader("Cargar Software (Inventario Software Institucional - Eduactivo y Operacional.xlsx)", type=["xlsx"]) # , help="Inventario Software Institucional - Eduactivo y Operacional (1).xlsx")
uploaded_actividades = st.sidebar.file_uploader("Cargar Actividades (Reporte de actividades desarrollo 2026-01.xlsx)", type=["xlsx"]) # , help="Reporte de actividades desarrollo 2026-01 (1).xlsx")



con, det, inv, eventos, ups, sw, act = cargar_datos_procesados(uploaded_tickets, uploaded_inventario, uploaded_software, uploaded_actividades)

# ════════════════════════════════════════════════════════════════════
# TABS PRINCIPALES
# ════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "🎫 Tickets de Soporte",
    "🖥️ Inventario de Infraestructura",
    "💿 Software & Licencias",
    "🛠️ Actividades de Desarrollo",
])

# ═══════════════════════════════════
# TAB 1 — TICKETS
# ═══════════════════════════════════
with tab1:
    if uploaded_tickets:
        # Filtros sidebar
        with st.sidebar:
            st.markdown("### 🎫 Filtros de Tickets")
            tipos_disp = sorted(det["tipo"].dropna().unique()) if "tipo" in det.columns else []
            tipos_sel = st.multiselect("Tipo de ticket:", tipos_disp, default=tipos_disp)
            estados_disp = sorted(det["Estado"].dropna().unique()) if "Estado" in det.columns else []
            estados_sel = st.multiselect("Estado:", estados_disp, default=estados_disp)

        df_t = det.copy()
        if tipos_sel and "tipo" in df_t.columns:
            df_t = df_t[df_t["tipo"].isin(tipos_sel)]
        if estados_sel and "Estado" in df_t.columns:
            df_t = df_t[df_t["Estado"].isin(estados_sel)]

        # KPIs
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("Total Tickets", f"{len(df_t):,}", f"de {len(det):,} totales")
        abiertos = len(df_t[df_t["Estado"]=="Abierto"]) if "Estado" in df_t.columns else 0
        with c2: kpi("Abiertos", f"{abiertos:,}", "pendientes de resolución", "or")
        cerrados = len(df_t[df_t["Estado"]=="Cerrar"]) if "Estado" in df_t.columns else 0
        with c3: kpi("Cerrados", f"{cerrados:,}", f"{cerrados/max(len(df_t),1)*100:.1f}% del total", "gr")
        en_curso = len(df_t[df_t["Estado"]=="En curso"]) if "Estado" in df_t.columns else 0
        with c4: kpi("En Curso", f"{en_curso:,}", "en proceso", "gy")

        st.markdown("<br>", unsafe_allow_html=True)
        g1, g2 = st.columns(2)

        with g1:
            if "tipo" in df_t.columns:
                conteo = df_t["tipo"].value_counts().reset_index()
                conteo.columns = ["Tipo","Cantidad"]
                fig = px.bar(conteo, x="Cantidad", y="Tipo", orientation="h",
                             color_discrete_sequence=[BLUE],
                             title="Tickets por Tipo",
                             text="Cantidad")
                fig.update_traces(textposition="outside")
                fig.update_layout(showlegend=False, plot_bgcolor="white",
                                  margin=dict(t=40,b=10), height=320)
                st.plotly_chart(fig, use_container_width=True)

        with g2:
            if "Estado" in df_t.columns:
                conteo_e = df_t["Estado"].value_counts().reset_index()
                conteo_e.columns = ["Estado","Cantidad"]
                fig2 = px.pie(conteo_e, names="Estado", values="Cantidad",
                              color_discrete_sequence=PALETTE,
                              title="Distribución por Estado",
                              hole=0.45)
                fig2.update_layout(margin=dict(t=40,b=10), height=320)
                st.plotly_chart(fig2, use_container_width=True)

        if "mes_label" in df_t.columns:
            tend = (df_t.groupby(["año","mes","mes_label"]).size()
                    .reset_index(name="tickets")
                    .sort_values(["año","mes"]))
            fig3 = px.line(tend, x="mes_label", y="tickets",
                           markers=True, color_discrete_sequence=[BLUE],
                           title="Volumen Mensual de Tickets")
            fig3.update_layout(plot_bgcolor="white", xaxis_title="Período",
                               yaxis_title="Tickets", margin=dict(t=40,b=10))
            fig3.update_traces(fill="tozeroy", fillcolor="rgba(0,123,153,0.08)")
            st.plotly_chart(fig3, use_container_width=True)

        if "dia_semana" in df_t.columns:
            orden_dias = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            labels_es  = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles",
                          "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado","Sunday":"Domingo"}
            by_day = df_t["dia_semana"].value_counts().reindex(orden_dias).reset_index()
            by_day.columns = ["dia","tickets"]
            by_day["dia"] = by_day["dia"].map(labels_es)
            fig4 = px.bar(by_day, x="dia", y="tickets",
                          color_discrete_sequence=[ORANGE],
                          title="Tickets por Día de la Semana", text="tickets")
            fig4.update_traces(textposition="outside")
            fig4.update_layout(plot_bgcolor="white", margin=dict(t=40,b=10), height=320)
            st.plotly_chart(fig4, use_container_width=True)

        if "Empleado" in df_t.columns:
            by_emp = df_t["Empleado"].value_counts().head(10).reset_index()
            by_emp.columns = ["Empleado","Tickets"]
            by_emp["Empleado"] = by_emp["Empleado"].str.split("<").str[0].str.strip()
            fig5 = px.bar(by_emp, x="Tickets", y="Empleado", orientation="h",
                          color_discrete_sequence=[GREY],
                          title="Top 10 Empleados con más Tickets asignados",
                          text="Tickets")
            fig5.update_traces(textposition="outside")
            fig5.update_layout(plot_bgcolor="white", margin=dict(t=40,b=10), height=360)
            st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("Por favor, sube el archivo de Tickets para ver esta sección.")

# ═══════════════════════════════════
# TAB 2 — INVENTARIO
# ═══════════════════════════════════
with tab2:
    if uploaded_inventario:
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("Equipos Totales", f"{len(inv):,}", "en inventario")
        serv_n = len(inv[inv["TIPO_EQUIPO"]=="Servidor"]) if "TIPO_EQUIPO" in inv.columns else 0
        with c2: kpi("Servidores", f"{serv_n}", "físicos y virtuales", "or")
        ap_n = len(inv[inv["TIPO_EQUIPO"]=="Access Point"]) if "TIPO_EQUIPO" in inv.columns else 0
        with c3: kpi("Access Points", f"{ap_n}", "puntos de acceso WiFi", "gr")
        ups_n = len(inv[inv["TIPO_EQUIPO"]=="UPS"]) if "TIPO_EQUIPO" in inv.columns else 0
        with c4: kpi("UPS", f"{ups_n}", "sistemas de respaldo eléctrico", "gy")

        st.markdown("<br>", unsafe_allow_html=True)
        g1, g2 = st.columns(2)

        with g1:
            if "TIPO_EQUIPO" in inv.columns:
                conteo_tipo = inv["TIPO_EQUIPO"].value_counts().reset_index()
                conteo_tipo.columns = ["Tipo","Cantidad"]
                fig = px.bar(conteo_tipo, x="Tipo", y="Cantidad",
                             color_discrete_sequence=[BLUE],
                             title="Equipos por Tipo", text="Cantidad")
                fig.update_traces(textposition="outside")
                fig.update_layout(plot_bgcolor="white", margin=dict(t=40,b=10), height=320)
                st.plotly_chart(fig, use_container_width=True)

        with g2:
            if "CENTRO REGIONAL" in inv.columns:
                conteo_sede = inv["CENTRO REGIONAL"].value_counts().reset_index()
                conteo_sede.columns = ["Sede","Cantidad"]
                fig2 = px.pie(conteo_sede, names="Sede", values="Cantidad",
                              color_discrete_sequence=PALETTE,
                              title="Equipos por Sede", hole=0.4)
                fig2.update_layout(margin=dict(t=40,b=10), height=320)
                st.plotly_chart(fig2, use_container_width=True)

        if "TIPO DE INSTALACIÓN" in inv.columns:
            g1b, g2b = st.columns(2)
            with g1b:
                inst = inv["TIPO DE INSTALACIÓN"].value_counts().reset_index()
                inst.columns = ["Instalación","Cantidad"]
                fig3 = px.pie(inst, names="Instalación", values="Cantidad",
                              color_discrete_sequence=[BLUE, ORANGE],
                              title="On Premise vs Nube", hole=0.4)
                fig3.update_layout(margin=dict(t=40,b=10), height=300)
                st.plotly_chart(fig3, use_container_width=True)

            with g2b:
                if "MISIÓN CRÍTICA" in inv.columns:
                    mc = inv["MISIÓN CRÍTICA"].value_counts().reset_index()
                    mc.columns = ["Crítico","Cantidad"]
                    fig4 = px.bar(mc, x="Crítico", y="Cantidad",
                                  color_discrete_sequence=[ORANGE, GREY],
                                  title="Equipos de Misión Crítica", text="Cantidad")
                    fig4.update_traces(textposition="outside")
                    fig4.update_layout(plot_bgcolor="white", margin=dict(t=40,b=10), height=300)
                    st.plotly_chart(fig4, use_container_width=True)

        if "dias_desde_cambio" in ups.columns:
            st.markdown("####  Estado de Baterías UPS")
            ups_mostrar = ups[[c for c in ["UBICACIÓN","MARCA","MODELO","CAPACIDAD",
                                            "FECHA ÚLTIMO CAMBIO DE BATERÍAS","dias_desde_cambio"]
                               if c in ups.columns]].copy()
            ups_mostrar = ups_mostrar.sort_values("dias_desde_cambio", ascending=False)
            st.dataframe(ups_mostrar, use_container_width=True, height=260)

        if not eventos.empty:
            st.markdown("#### ⚠️ Registro de Eventos e Incidentes")
            st.dataframe(eventos, use_container_width=True, height=200)
    else:
        st.info("Por favor, sube el archivo de Inventario para ver esta sección.")

# ═══════════════════════════════════
# TAB 3 — SOFTWARE
# ═══════════════════════════════════
with tab3:
    if uploaded_software:
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("Licencias Totales", f"{len(sw):,}", "edu + operacional")
        lic = sw[sw.get("SOFTWARE","") == "Licenciado"] if "SOFTWARE" in sw.columns else sw
        with c2: kpi("Licenciadas", f"{len(lic):,}", "", "or")
        if "estado_licencia" in sw.columns:
            venc = len(sw[sw["estado_licencia"]=="Vencida"])
            pv   = len(sw[sw["estado_licencia"]=="Por vencer (<60d)"])
            with c3: kpi("Vencidas", f"{venc}", "requieren renovación", "rd")
            with c4: kpi("Por Vencer", f"{pv}", "en menos de 60 días", "or")

        st.markdown("<br>", unsafe_allow_html=True)
        g1, g2 = st.columns(2)

        with g1:
            if "CATEGORIA" in sw.columns:
                cat = sw["CATEGORIA"].value_counts().reset_index()
                cat.columns = ["Categoría","Cantidad"]
                fig = px.pie(cat, names="Categoría", values="Cantidad",
                             color_discrete_sequence=[BLUE, ORANGE],
                             title="Software Educativo vs Operacional", hole=0.4)
                fig.update_layout(margin=dict(t=40,b=10), height=300)
                st.plotly_chart(fig, use_container_width=True)

        with g2:
            if "estado_licencia" in sw.columns:
                est = sw["estado_licencia"].value_counts().reset_index()
                est.columns = ["Estado","Cantidad"]
                color_map = {"Vigente":"#28a745","Por vencer (<60d)":ORANGE,
                             "Vencida":"#dc3545","Sin fecha":GREY}
                fig2 = px.bar(est, x="Estado", y="Cantidad",
                              color="Estado", color_discrete_map=color_map,
                              title="Estado de Licencias", text="Cantidad")
                fig2.update_traces(textposition="outside")
                fig2.update_layout(showlegend=False, plot_bgcolor="white",
                                   margin=dict(t=40,b=10), height=300)
                st.plotly_chart(fig2, use_container_width=True)

        if "PROVEEDOR" in sw.columns:
            top_prov = sw["PROVEEDOR"].value_counts().head(10).reset_index()
            top_prov.columns = ["Proveedor","Cantidad"]
            fig3 = px.bar(top_prov, x="Cantidad", y="Proveedor", orientation="h",
                          color_discrete_sequence=[GREY],
                          title="Top Proveedores de Software", text="Cantidad")
            fig3.update_traces(textposition="outside")
            fig3.update_layout(plot_bgcolor="white", margin=dict(t=40,b=10), height=350)
            st.plotly_chart(fig3, use_container_width=True)

        if "estado_licencia" in sw.columns:
            st.markdown("####  Licencias que requieren atención")
            urgentes = sw[sw["estado_licencia"].isin(["Vencida","Por vencer (<60d)"])]
            cols_sw = [c for c in ["NOMBRE SOFTWARE","CATEGORIA","PROVEEDOR",
                                    "FECHA DE VENCIMIENTO","dias_para_vencer","estado_licencia"]
                       if c in urgentes.columns]
            st.dataframe(urgentes[cols_sw].sort_values("dias_para_vencer"),
                         use_container_width=True, height=280)
    else:
        st.info("Por favor, sube el archivo de Software para ver esta sección.")

# ═══════════════════════════════════
# TAB 4 — ACTIVIDADES DE DESARROLLO
# ═══════════════════════════════════
with tab4:
    if uploaded_actividades:
        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("Total Ítems", f"{len(act):,}", "bugs + user stories")
        if "Tipo" in act.columns:
            bugs = len(act[act["Tipo"]=="Bug"])
            us   = len(act[act["Tipo"]=="User Story"])
            with c2: kpi("Bugs", f"{bugs}", "defectos reportados", "rd")
            with c3: kpi("User Stories", f"{us}", "funcionalidades", "or")
        if "Estado" in act.columns:
            cerr = len(act[act["Estado"]=="Closed"])
            with c4: kpi("Cerrados", f"{cerr}",
                         f"{cerr/max(len(act),1)*100:.1f}% completados", "gr")

        st.markdown("<br>", unsafe_allow_html=True)
        g1, g2 = st.columns(2)

        with g1:
            if "Estado" in act.columns:
                est = act["Estado"].value_counts().reset_index()
                est.columns = ["Estado","Cantidad"]
                color_map = {"Closed":"#28a745","Resolved":BLUE,
                             "Active":ORANGE,"New":GREY}
                fig = px.bar(est, x="Cantidad", y="Estado", orientation="h",
                             color="Estado", color_discrete_map=color_map,
                             title="Ítems por Estado", text="Cantidad")
                fig.update_traces(textposition="outside")
                fig.update_layout(showlegend=False, plot_bgcolor="white",
                                  margin=dict(t=40,b=10), height=300)
                st.plotly_chart(fig, use_container_width=True)

        with g2:
            if "Tipo" in act.columns:
                tipo = act["Tipo"].value_counts().reset_index()
                tipo.columns = ["Tipo","Cantidad"]
                fig2 = px.pie(tipo, names="Tipo", values="Cantidad",
                              color_discrete_sequence=[ORANGE, BLUE],
                              title="Bugs vs User Stories", hole=0.4)
                fig2.update_layout(margin=dict(t=40,b=10), height=300)
                st.plotly_chart(fig2, use_container_width=True)

        if "Asignado a" in act.columns:
            by_dev = act["Asignado a"].value_counts().reset_index()
            by_dev.columns = ["Desarrollador","Ítems"]
            by_dev["Desarrollador"] = by_dev["Desarrollador"].str.split("<").str[0].str.strip()
            fig3 = px.bar(by_dev, x="Ítems", y="Desarrollador", orientation="h",
                          color_discrete_sequence=[BLUE],
                          title="Carga por Desarrollador", text="Ítems")
            fig3.update_traces(textposition="outside")
            fig3.update_layout(plot_bgcolor="white", margin=dict(t=40,b=10), height=300)
            st.plotly_chart(fig3, use_container_width=True)

        if "dias_retraso" in act.columns:
            act_cerr = act[act["Estado"]=="Closed"].dropna(subset=["dias_retraso"])
            if not act_cerr.empty:
                fig4 = px.histogram(act_cerr, x="dias_retraso", nbins=20,
                                    color_discrete_sequence=[ORANGE],
                                    title="Distribución de Días de Retraso (ítems cerrados)")
                fig4.add_vline(x=0, line_dash="dash", line_color="red",
                               annotation_text="Sin retraso")
                fig4.update_layout(plot_bgcolor="white", margin=dict(t=40,b=10))
                st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Por favor, sube el archivo de Actividades para ver esta sección.")
