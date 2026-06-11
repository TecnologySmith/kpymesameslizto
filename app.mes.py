import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración inicial de la página (Título en pestaña y layout ancho)
st.set_page_config(page_title="Analizador de Chats Multi-Mes Lizto Software", layout="wide")

# Título principal de la interfaz
st.title("📊 Analizador de Chats lizto Pro (Comparativa Mensual Cronológica)")
st.markdown("Sube tu archivo de Excel para procesar y comparar las métricas de agentes, tiempos y categorías ordenadas cronológicamente.")

# --- 1. CARGA DE ARCHIVOS ---
uploaded_file = st.file_uploader("Elige un archivo Excel", type=["xlsx", "xls"])

if uploaded_file:
    # Lectura del archivo Excel usando pandas
    df = pd.read_excel(uploaded_file)
    
    try:
        # Conversión de la columna fecha a formato datetime de Python
        df['Fecha Creación'] = pd.to_datetime(df['Fecha Creación'])
        
        # --- 2. FILTRO LATERAL (SIDEBAR) ---
        st.sidebar.header("Filtros")
        fecha_min = df['Fecha Creación'].min().date()
        fecha_max = df['Fecha Creación'].max().date()
        
        # Widget para seleccionar rango de fechas
        rango_fechas = st.sidebar.date_input(
            "Selecciona el rango de fechas",
            value=(fecha_min, fecha_max),
            min_value=fecha_min,
            max_value=fecha_max
        )

        # Aplicación del filtro de fechas si el usuario seleccionó un rango válido
        if len(rango_fechas) == 2:
            inicio, fin = rango_fechas
            mask = (df['Fecha Creación'].dt.date >= inicio) & (df['Fecha Creación'].dt.date <= fin)
            df = df.loc[mask]

        # --- 3. PROCESAMIENTO DE DATOS TEMPORALES Y DE MES ---
        df['Hora'] = df['Fecha Creación'].dt.hour
        df['Día del Mes'] = df['Fecha Creación'].dt.day
        df['Nombre Día'] = df['Fecha Creación'].dt.day_name()
        df['Fecha'] = df['Fecha Creación'].dt.date
        df['Año'] = df['Fecha Creación'].dt.year
        df['Mes_Num'] = df['Fecha Creación'].dt.month
        
        # Diccionarios de traducción para estandarizar en español
        traduccion_dias = {
            'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
            'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        traduccion_meses = {
            1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
        }
        
        df['Día Semana'] = df['Nombre Día'].map(traduccion_dias)
        df['Nombre Mes'] = df['Mes_Num'].map(traduccion_meses)
        
        # Columna clave: "Mes" (Formato: '2026 - Ene') que agrupa año y mes evitando colisiones multi-año
        df['Mes'] = df['Año'].astype(str) + " - " + df['Nombre Mes']
        
        # --- SOLUCIÓN AL ORDENAMIENTO CRONOLÓGICO DE LOS MESES ---
        # 1. Generamos dinámicamente las combinaciones válidas de Año - Mes basadas en los datos cargados
        periodos_unicos = df[['Año', 'Mes_Num']].drop_duplicates().sort_values(['Año', 'Mes_Num'])
        orden_meses_correcto = (periodos_unicos['Año'].astype(str) + " - " + periodos_unicos['Mes_Num'].map(traduccion_meses)).tolist()
        
        # 2. Convertimos la columna 'Mes' en una categoría ordenada usando la lista cronológica estricta
        df['Mes'] = pd.Categorical(df['Mes'], categories=orden_meses_correcto, ordered=True)
        
        # Forzar orden lógico de los días de la semana
        orden_espanol_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        df['Día Semana'] = pd.Categorical(df['Día Semana'], categories=orden_espanol_dias, ordered=True)
        
        # Ordenamos el DataFrame base por las categorías para asegurar coherencia en tablas y gráficas
        df = df.sort_values(['Mes', 'Fecha Creación'])

        # --- 4. CÁLCULO DE KPIs (INDICADORES CLAVE) ---
        total_chats = len(df)
        total_agentes = df['Agente'].nunique() if 'Agente' in df.columns else 0
        meses_unicos = df['Mes'].nunique()
        promedio_mes = round(total_chats / meses_unicos, 1) if meses_unicos > 0 else 0

        # Mostrar métricas en 3 columnas
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Chats Global", f"{total_chats:,}")
        m2.metric("Agentes Activos", total_agentes)
        m3.metric("Promedio Chats / Mes", promedio_mes)
        
        st.divider()

        # --- 5. SECCIÓN: DESEMPEÑO POR AGENTE Y COMPARATIVA ---
        if 'Agente' in df.columns:
            st.header("👨‍💻 Desempeño de Agentes por Mes")
            
            # Agrupación por Agente y Mes (observed=False mantiene consistencia en categorizados)
            agente_counts = df.groupby(['Agente', 'Mes'], observed=False).size().reset_index(name='Total Chats')
            
            # Construcción de Tabla Dinámica (Pivot Table) respetando el orden de las columnas categóricas
            df_tabla_agentes = df.pivot_table(index='Agente', columns='Mes', values='Fecha Creación', 
                                              aggfunc='count', fill_value=0, observed=False).reset_index()
            
            # Asegurar que las columnas del DataFrame de la tabla sigan el orden cronológico establecido
            columnas_meses = [c for c in orden_meses_correcto if c in df_tabla_agentes.columns]
            df_tabla_agentes = df_tabla_agentes[['Agente'] + columnas_meses]
            
            # Añadir Fila de Totales Dinámicos por mes
            fila_total_ag = pd.DataFrame([['TOTAL'] + [df_tabla_agentes[c].sum() for c in columnas_meses]], 
                                         columns=df_tabla_agentes.columns)
            df_tabla_agentes = pd.concat([df_tabla_agentes, fila_total_ag], ignore_index=True)

            col1, col2 = st.columns([1, 2])
            with col1:
                st.write("**Matriz Comparativa Mensual**")
                st.dataframe(df_tabla_agentes, use_container_width=True, hide_index=True)
            
            with col2:
                # Gráfico de barras agrupado por mes (barmode='group'). Plotly hereda el orden de las categorías de Pandas.
                fig_agente = px.bar(agente_counts, x='Agente', y='Total Chats', color='Mes', 
                                    barmode='group', text_auto=True,
                                    category_orders={"Mes": orden_meses_correcto},
                                    title="Distribución y Carga de Agentes Comparada")
                st.plotly_chart(fig_agente, use_container_width=True)

            st.divider()

        # --- 6. SECCIÓN: ANÁLISIS HORARIO COMPARATIVO ---
        st.header("⏰ Volumen Horario por Mes")
        hora_counts = df.groupby(['Hora', 'Mes'], observed=False).size().reset_index(name='Cantidad')
        
        fig_hora = px.line(hora_counts, x='Hora', y='Cantidad', color='Mes', markers=True,
                           category_orders={"Mes": orden_meses_correcto},
                           title="Flujo e Intensidad de Chats por Hora")
        st.plotly_chart(fig_hora, use_container_width=True)

        st.divider()

        # --- 7. SECCIÓN: ANÁLISIS CALENDARIO MENSUAL ---
        col_a, col_b = st.columns(2)

        with col_a:
            st.header("📅 Por Día del Mes")
            dia_mes_counts = df.groupby(['Día del Mes', 'Mes'], observed=False).size().reset_index(name='Cantidad')
            
            fig_dia = px.bar(dia_mes_counts, x='Día del Mes', y='Cantidad', color='Mes', 
                             barmode='group', category_orders={"Mes": orden_meses_correcto},
                             title="Volumen diario indexado por Mes")
            st.plotly_chart(fig_dia, use_container_width=True)

        with col_b:
            st.header("🗓️ Por Día de la Semana")
            dia_semana_counts = df.groupby(['Día Semana', 'Mes'], observed=False).size().reset_index(name='Cantidad')
            
            fig_semana = px.bar(dia_semana_counts, x='Día Semana', y='Cantidad', color='Mes', 
                                barmode='group', category_orders={"Mes": orden_meses_correcto, "Día Semana": orden_espanol_dias},
                                title="Rendimiento del Tráfico Semanal")
            st.plotly_chart(fig_semana, use_container_width=True)

        st.divider()

        # --- 8. SECCIÓN: ANÁLISIS POR CLASIFICACIÓN COMPARATIVO ---
        if 'Clasificación' in df.columns:
            st.header("🏷️ Análisis por Clasificación y Mes")
            
            class_counts = df.groupby(['Clasificación', 'Mes'], observed=False).size().reset_index(name='Total Chats')
            
            # Creación de Tabla Dinámica para Clasificaciones
            df_tabla_class = df.pivot_table(index='Clasificación', columns='Mes', values='Fecha Creación', 
                                              aggfunc='count', fill_value=0, observed=False).reset_index()
            
            # Reordenar columnas de la tabla dinámica
            df_tabla_class = df_tabla_class[['Clasificación'] + columnas_meses]
            
            fila_total_cl = pd.DataFrame([['TOTAL'] + [df_tabla_class[c].sum() for c in columnas_meses]], 
                                         columns=df_tabla_class.columns)
            df_tabla_class = pd.concat([df_tabla_class, fila_total_cl], ignore_index=True)

            col_c1, col_c2 = st.columns([1, 2])
            with col_c1:
                st.write("**Resumen de Categorías por Mes**")
                st.dataframe(df_tabla_class, use_container_width=True, hide_index=True)
            
            with col_c2:
                fig_class = px.bar(class_counts, x='Clasificación', y='Total Chats', color='Mes', 
                                    barmode='group', text_auto=True,
                                    category_orders={"Mes": orden_meses_correcto},
                                    title="Evolución de Tipologías de Chat")
                st.plotly_chart(fig_class, use_container_width=True)
        else:
            st.warning("No se encontró la columna 'Clasificación' en el archivo.")

        st.divider()

    except Exception as e:
        st.error(f"Error en el procesamiento de las estructuras de datos: {e}")

else:
    st.info("Esperando archivo... Asegúrate de que el Excel tenga las columnas: 'Agente', 'Fecha Creación' y 'Clasificación'.")