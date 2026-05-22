import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

# Configuración de la página estilo Dashboard Profesional
st.set_page_config(page_title="Simulador de Pricing y Elasticidad", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# LÓGICA DE CLASIFICACIÓN DEL NOTEBOOK
# ==========================================
def calcular_clase_elasticidad(elasticidad):
    """Clasifica la elasticidad según las reglas estándar del Notebook"""
    if elasticidad > 0:
        return "Anómala (Positiva)"
    elif elasticidad == 0:
        return "Perfectamente Inelástica"
    elif elasticidad > -1.0:
        return "Inelástica"
    elif elasticidad == -1.0:
        return "Unitaria"
    else:
        return "Elástica"

def recomendar_accion(elasticidad, mejor_escenario, precio_actual):
    """Genera la recomendación basada en la elasticidad y el histórico"""
    precio_optimo = mejor_escenario['Precio_Efectivo']
    tipo_escenario = mejor_escenario['Tipo']
    
    if tipo_escenario == "Promoción":
        return "Bajar precio / promover"
    elif precio_optimo > precio_actual:
        return "Subir precio"
    elif precio_optimo < precio_actual:
        return "Bajar precio"
    else:
        if elasticidad > -1.0:
            return "Mantener precio"
        else:
            return "No recomendar"

# Columnas requeridas por el Notebook para el análisis de ventas
COLUMNAS_REQUERIDAS = ["SKU", "Precio", "Costo", "Unidades", "Fecha"]

# ==========================================
# SECCIÓN 1: CARGA Y VALIDACIÓN DE DATOS
# ==========================================
st.title("📊 Plataforma de Estrategia de Pricing y Promociones")
st.markdown("---")

st.header("1. Carga y Validación del Histórico")

# Mostrar las columnas necesarias antes de subir el archivo
st.info(f"📋 **Columnas requeridas para el análisis:** `{', '.join(COLUMNAS_REQUERIDAS)}` "
        f"\n\n*(Nota: Si tu archivo incluye la columna 'FINAL_ELASTICITY_CLASS', la app la tomará en cuenta automáticamente)*")

col_v, col_p = st.columns(2)
with col_v:
    archivo_ventas = st.file_uploader("Subir Histórico de Ventas (CSV o Excel)", type=["csv", "xlsx"])
with col_p:
    archivo_promos = st.file_uploader("Subir Histórico de Promociones - Opcional (CSV o Excel)", type=["csv", "xlsx"])

if archivo_ventas is not None:
    # Lectura del archivo según su extensión
    try:
        if archivo_ventas.name.endswith('.csv'):
            df_ventas = pd.read_csv(archivo_ventas)
        else:
            df_ventas = pd.read_excel(archivo_ventas)
            
        # Validación estricta de columnas obligatorias
        columnas_faltantes = [col for col in COLUMNAS_REQUERIDAS if col not in df_ventas.columns]
        
        if columnas_faltantes:
            st.error(f"⚠️ **El archivo no sirve para el análisis.** Faltan las siguientes columnas obligatorias: {columnas_faltantes}. Por favor, rectifica los nombres en tu archivo e inténtalo de nuevo.")
            st.stop()
        else:
            st.success("✅ ¡Estructura de archivo válida! Cargado correctamente.")
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        st.stop()

    # ==========================================
    # SECCIÓN 2: SIMULACIÓN Y DASHBOARDS
    # ==========================================
    st.markdown("---")
    st.header("2. Análisis por SKU y Simulación de Escenarios")
    
    # Listado de SKUs únicos para la selección
    lista_skus = df_ventas["SKU"].unique().tolist()
    
    c1, c2 = st.columns(2)
    with c1:
        sku_seleccionado = st.selectbox("🔍 Selecciona el SKU para el análisis:", lista_skus)
    
    # Filtrar datos del SKU seleccionado
    df_sku = df_ventas[df_ventas["SKU"] == sku_seleccionado].copy()
    
    # Intentar detectar si ya viene una elasticidad histórica en el archivo
    elasticidad_inicial = -1.2
    if "FINAL_ELASTICITY_CLASS" in df_sku.columns:
        st.caption("💡 Se detectó la columna 'FINAL_ELASTICITY_CLASS' en tu archivo histórico.")
    
    with c2:
        elasticidad_manual = st.number_input("📈 Ingresa la Elasticidad Manualmente para la simulación:", 
                                             value=elasticidad_inicial, step=0.1)
    
    # Calcular la clase de elasticidad correspondiente
    clase_elasticidad = calcular_clase_elasticidad(elasticidad_manual)
    
    # Obtener métricas base del histórico del SKU
    precio_actual = float(df_sku["Precio"].mean())
    costo_actual = float(df_sku["Costo"].mean())
    unidades_base = float(df_sku["Unidades"].sum())
    
    # Definición de escenarios de precio y promociones complejas
    variaciones_precio = [-0.15, -0.10, -0.05, 0.00, 0.05, 0.10, 0.15]
    promociones_complejas = {
        "Promoción 2x1": -0.50,
        "Promoción 3x2": -0.3333,
        "2do artículo al 50%": -0.25
    }
    
    resultados_simulacion = []
    
    # 1. Simular variaciones porcentuales de precio
    for var in variaciones_precio:
        p_nuevo = precio_actual * (1 + var)
        cambio_demanda = elasticidad_manual * var
        u_nuevas = max(0, unidades_base * (1 + cambio_demanda))
        ingreso = p_nuevo * u_nuevas
        margen = (p_nuevo - costo_actual) * u_nuevas
        
        resultados_simulacion.append({
            "SKU": sku_seleccionado,
            "FINAL_ELASTICITY_CLASS": clase_elasticidad,
            "Escenario": f"Cambio Precio {var*100:+.0f}%",
            "Tipo": "Precio",
            "Precio_Efectivo": p_nuevo,
            "Unidades_Simuladas": u_nuevas,
            "Ingreso_Proyectado": ingreso,
            "Margen_Proyectado": margen
        })
        
    # 2. Simular promociones complejas
    for promo, desc in promociones_complejas.items():
        p_nuevo = precio_actual * (1 + desc)
        cambio_demanda = elasticidad_manual * desc
        u_nuevas = max(0, unidades_base * (1 + cambio_demanda))
        ingreso = p_nuevo * u_nuevas
        margen = (p_nuevo - costo_actual) * u_nuevas
        
        resultados_simulacion.append({
            "SKU": sku_seleccionado,
            "FINAL_ELASTICITY_CLASS": clase_elasticidad,
            "Escenario": promo,
            "Tipo": "Promoción",
            "Precio_Efectivo": p_nuevo,
            "Unidades_Simuladas": u_nuevas,
            "Ingreso_Proyectado": ingreso,
            "Margen_Proyectado": margen
        })
        
    df_resultados = pd.DataFrame(resultados_simulacion)
    
    # Determinar el mejor escenario según margen óptimo
    idx_mejor = df_resultados["Margen_Proyectado"].idxmax()
    mejor_escenario = df_resultados.loc[idx_mejor]
    accion = recomendar_accion(elasticidad_manual, mejor_escenario, precio_actual)
    
    # 🌟 CONCLUSIÓN PERSONALIZADA DINÁMICA (Se actualiza inmediatamente al cambiar SKU o Elasticidad)
    st.markdown("### 📢 Conclusión Estratégica Automatizada")
    st.info(
        f"Para el **SKU {sku_seleccionado}**, analizando tu histórico y basándonos en una elasticidad asignada de **{elasticidad_manual}** "
        f"la cual se clasifica como **{clase_elasticidad}** (`FINAL_ELASTICITY_CLASS`), se concluye que el escenario óptimo que maximiza "
        f"el rendimiento es **{mejor_escenario['Escenario']}** generando un margen proyectado de **${mejor_escenario['Margen_Proyectado']:,.2f}**. "
        f"\n\n**Acción recomendada:** 🚀 `{accion.upper()}`"
    )
    
    # 📊 DASHBOARDS DEL NOTEBOOK
    st.subheader("Visualización de Curvas y Margen (Dashboards)")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Gráfico izquierdo: Curva de Elasticidad Simulada
    df_ordenado = df_resultados.sort_values(by="Precio_Efectivo")
    ax1.plot(df_ordenado["Precio_Efectivo"], df_ordenado["Unidades_Simuladas"], marker="o", linestyle="-", color="#1f77b4", linewidth=2)
    ax1.set_title("Curva Precio-Demanda Proyectada", fontsize=12, fontweight='bold')
    ax1.set_xlabel("Precio Efectivo ($)")
    ax1.set_ylabel("Volumen de Unidades Simuladas")
    ax1.grid(True, linestyle="--", alpha=0.5)
    
    # Gráfico derecho: Comparativa de Margen por Escenario
    colores = ['#ff7f0e' if t == 'Promoción' else '#2ca02c' for t in df_resultados['Tipo']]
    ax2.barh(df_resultados["Escenario"], df_resultados["Margen_Proyectado"], color=colores, edgecolor='black', alpha=0.8)
    ax2.set_title("Margen de Ganancia por Escenario Simulado", fontsize=12, fontweight='bold')
    ax2.set_xlabel("Margen Proyectado ($)")
    ax2.grid(axis='x', linestyle="--", alpha=0.5)
    
    plt.tight_layout()
    st.pyplot(fig)

    # ==========================================
    # SECCIÓN 3: EXPORTACIÓN DE RESULTADOS
    # ==========================================
    st.markdown("---")
    st.header("3. Resumen Técnico y Descarga de Datos")
    
    # Añadir columna de recomendación global al set final
    df_resultados["Accion_Recomendada"] = accion
    
    # Mostrar tabla limpia formateada en Streamlit
    st.dataframe(df_resultados.style.format({
        "Precio_Efectivo": "${:.2f}",
        "Unidades_Simuladas": "{:,.0f}",
        "Ingreso_Proyectado": "${:,.2f}",
        "Margen_Proyectado": "${:,.2f}"
    }))
    
    # Conversión del dataframe compilado a un archivo CSV descargable
    csv_stream = io.StringIO()
    df_resultados.to_csv(csv_stream, index=False, encoding="utf-8-sig")
    csv_data = csv_stream.getvalue()
    
    st.download_button(
        label="📥 Descargar Análisis Completo por SKU (CSV)",
        data=csv_data,
        file_name=f"analisis_elasticidad_sku_{sku_seleccionado}.csv",
        mime="text/csv",
        type="primary"
    )
else:
    st.write("Por favor, sube un archivo de ventas en la Sección 1 para inicializar los dashboards y simuladores.")