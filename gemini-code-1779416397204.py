import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

# Configuración inicial de la página
st.set_page_config(page_title="Simulador de Pricing y Promociones", layout="wide")

# ==========================================
# CONSTANTES Y LÓGICA DEL NOTEBOOK
# ==========================================
COLUMNAS_VENTAS = ["SKU", "Precio", "Costo", "Unidades", "Fecha"] # Ajusta según tu archivo original
COLUMNAS_PROMOS = ["SKU", "Promocion_Activa", "Descuento"] # Opcional

ESCENARIOS_CAMBIO_PRECIO = [-0.15, -0.10, -0.05, 0.00, 0.05, 0.10, 0.15]
ESCENARIOS_PROMOCION = {
    "2x1": -0.50,         
    "3x2": -0.3333,       
    "2do al 50%": -0.25   
}

# Función para definir FINAL_ELASTICITY_CLASS
def obtener_clase_elasticidad(elasticidad):
    if elasticidad > 0:
        return "Positiva (Anómala)"
    elif elasticidad == 0:
        return "Perfectamente Inelástica"
    elif elasticidad > -1.0:
        return "Inelástica"
    elif elasticidad == -1.0:
        return "Unitaria"
    else:
        return "Elástica"

# ==========================================
# SECCIÓN 1: CARGA Y VALIDACIÓN DE DATOS
# ==========================================
st.title("📊 Simulador de Elasticidad, Pricing y Promociones")

st.header("1. Carga de Archivos")
st.markdown(f"**Atención:** El archivo de ventas debe contener estrictamente las siguientes columnas: `{', '.join(COLUMNAS_VENTAS)}`")

col1, col2 = st.columns(2)
with col1:
    archivo_ventas = st.file_uploader("Sube tu histórico de ventas (CSV o Excel)", type=["csv", "xlsx"])
with col2:
    archivo_promos = st.file_uploader("Sube tu histórico de promos (Opcional)", type=["csv", "xlsx"])

if archivo_ventas:
    # Leer archivo
    if archivo_ventas.name.endswith('.csv'):
        df_ventas = pd.read_csv(archivo_ventas)
    else:
        df_ventas = pd.read_excel(archivo_ventas)
    
    # Validar columnas
    columnas_faltantes = [col for col in COLUMNAS_VENTAS if col not in df_ventas.columns]
    
    if columnas_faltantes:
        st.error(f"⚠️ Error: El archivo no sirve para el análisis. Faltan las siguientes columnas: {columnas_faltantes}. Por favor, rectifica el nombre de las columnas y vuelve a subir el archivo.")
        st.stop()
    else:
        st.success("✅ Archivo cargado y validado correctamente.")
        
        # ==========================================
        # SECCIÓN 2: SIMULACIÓN Y DASHBOARDS
        # ==========================================
        st.header("2. Análisis por SKU y Simulación")
        
        skus_disponibles = df_ventas["SKU"].unique().tolist()
        
        col_sku, col_elast = st.columns(2)
        with col_sku:
            sku_seleccionado = st.selectbox("Selecciona o escribe un SKU", skus_disponibles)
        with col_elast:
            elasticidad_manual = st.number_input("Ingresa la Elasticidad manualmente (ej. -1.5)", value=-1.0, step=0.1)

        # Definir la clase de elasticidad basada en el input
        final_elasticity_class = obtener_clase_elasticidad(elasticidad_manual)

        # Filtrar datos
        df_sku = df_ventas[df_ventas["SKU"] == sku_seleccionado].copy()
        
        # Simulación de Escenarios
        precio_actual = df_sku["Precio"].mean()
        costo_actual = df_sku["Costo"].mean()
        unidades_base = df_sku["Unidades"].sum()
        
        resultados = []
        
        # Escenarios de Precio
        for variacion in ESCENARIOS_CAMBIO_PRECIO:
            precio_nuevo = precio_actual * (1 + variacion)
            var_unidades = elasticidad_manual * variacion
            unidades_nuevas = max(0, unidades_base * (1 + var_unidades))
            ingreso = precio_nuevo * unidades_nuevas
            margen = (precio_nuevo - costo_actual) * unidades_nuevas
            
            resultados.append({
                "SKU": sku_seleccionado,
                "FINAL_ELASTICITY_CLASS": final_elasticity_class,
                "Escenario": f"Cambio {variacion*100:.0f}%",
                "Tipo": "Precio",
                "Precio_Efectivo": precio_nuevo,
                "Unidades_Simuladas": unidades_nuevas,
                "Ingreso": ingreso,
                "Margen": margen
            })
            
        # Escenarios de Promociones Complejas
        for nombre_promo, descuento in ESCENARIOS_PROMOCION.items():
            precio_nuevo = precio_actual * (1 + descuento)
            var_unidades = elasticidad_manual * descuento
            unidades_nuevas = max(0, unidades_base * (1 + var_unidades))
            ingreso = precio_nuevo * unidades_nuevas
            margen = (precio_nuevo - costo_actual) * unidades_nuevas
            
            resultados.append({
                "SKU": sku_seleccionado,
                "FINAL_ELASTICITY_CLASS": final_elasticity_class,
                "Escenario": nombre_promo,
                "Tipo": "Promoción",
                "Precio_Efectivo": precio_nuevo,
                "Unidades_Simuladas": unidades_nuevas,
                "Ingreso": ingreso,
                "Margen": margen
            })
            
        df_resultados = pd.DataFrame(resultados)
        
        # Determinar Recomendación
        mejor_escenario = df_resultados.loc[df_resultados['Margen'].idxmax()]
        
        if mejor_escenario['Tipo'] == 'Promoción':
            recomendacion = "Bajar precio / promover"
        elif mejor_escenario['Precio_Efectivo'] > precio_actual:
            recomendacion = "Subir precio"
        elif mejor_escenario['Precio_Efectivo'] < precio_actual:
            recomendacion = "Bajar precio / promover"
        else:
            if elasticidad_manual > -1.0: 
                recomendacion = "Mantener precio"
            else:
                recomendacion = "No recomendar"
        
        # Conclusión Personalizada al cambiar el SKU
        st.info(f"💡 **Conclusión para el SKU {sku_seleccionado}:** Con una elasticidad de **{elasticidad_manual}** (Clasificación: **{final_elasticity_class}**), el escenario que maximiza el margen es **{mejor_escenario['Escenario']}**. Por lo tanto, la acción recomendada es **{recomendacion}**.")

        # Dashboards
        st.subheader(f"Curvas de Simulación para SKU {sku_seleccionado}")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Gráfico 1: Unidades vs Precio
        ax1.plot(df_resultados["Precio_Efectivo"], df_resultados["Unidades_Simuladas"], marker="o", color="blue")
        for i, row in df_resultados.iterrows():
            ax1.text(row["Precio_Efectivo"], row["Unidades_Simuladas"], row["Escenario"], fontsize=8, ha='center', va='bottom')
        ax1.set_title("Curva Precio-Demanda (Simulada)")
        ax1.set_xlabel("Precio Efectivo")
        ax1.set_ylabel("Unidades")
        ax1.grid(True, alpha=0.3)
        
        # Gráfico 2: Margen vs Escenarios
        colores = ['orange' if x == 'Promoción' else 'green' for x in df_resultados['Tipo']]
        ax2.bar(df_resultados["Escenario"], df_resultados["Margen"], color=colores)
        ax2.set_title("Margen Proyectado por Escenario")
        ax2.set_ylabel("Margen ($)")
        plt.xticks(rotation=45, ha='right')
        ax2.grid(axis='y', alpha=0.3)
        
        st.pyplot(fig)

        # ==========================================
        # SECCIÓN 3: EXPORTACIÓN DE RESULTADOS
        # ==========================================
        st.header("3. Resumen y Exportación")
        st.dataframe(df_resultados.style.format({"Precio_Efectivo": "${:.2f}", "Ingreso": "${:.2f}", "Margen": "${:.2f}", "Unidades_Simuladas": "{:.0f}"}))
        
        # Generar CSV para descarga
        csv_buffer = io.StringIO()
        df_resultados['Recomendacion_Global'] = recomendacion
        df_resultados.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="📥 Descargar Análisis por SKU (CSV)",
            data=csv_buffer.getvalue(),
            file_name=f"simulacion_pricing_{sku_seleccionado}.csv",
            mime="text/csv",
            type="primary"
        )