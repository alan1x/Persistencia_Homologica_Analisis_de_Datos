"""Visualización estática de los resultados del cruce topológico-censal."""
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

from . import config

# Configuración visual
sns.set_theme(style="whitegrid")
COLORES_PRIORIDAD = {
    "Crítico": "#b2182b",
    "Alto": "#ef8a62",
    "Moderado": "#fddbc7",
    "Bajo": "#67a9cf",
}

def graficar_impacto_poblacional(df_prioridad, region):
    """Genera un gráfico compuesto (Matriz de Riesgo y Barras Apiladas) 
    para entender el impacto demográfico real de los huecos.
    """
    if len(df_prioridad) == 0:
        return None

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle(f"[{region}] Diagnóstico de Vulnerabilidad en Zonas sin Cobertura", 
                 fontsize=16, fontweight="bold", y=1.02)

    df_prioridad = df_prioridad.copy()
    df_prioridad["nivel_str"] = df_prioridad["nivel_prioridad"].astype(str)
    
    # ---------------------------------------------------------
    # 1. Matriz de Riesgo (Cuadrantes) en lugar del Scatter
    # ---------------------------------------------------------
    ax = axes[0]
    
    # Eje X: Población Afectada (Volumen del problema)
    # Eje Y: Porcentaje Sin Seguro (Vulnerabilidad / Severidad)
    sns.scatterplot(
        data=df_prioridad,
        x="pob_afectada",
        y="pct_sin_salud_prom",
        hue="nivel_str",
        palette=COLORES_PRIORIDAD,
        s=150, # Tamaño de burbuja fijo para evitar ruido visual
        alpha=0.85,
        edgecolor="k",
        ax=ax
    )
    
    # Líneas de cuadrante (Medianas)
    median_pob = df_prioridad["pob_afectada"].median()
    median_pct = df_prioridad["pct_sin_salud_prom"].median()
    
    ax.axvline(median_pob, color="gray", linestyle="--", alpha=0.5)
    ax.axhline(median_pct, color="gray", linestyle="--", alpha=0.5)
    
    # Anotar cuadrante crítico (arriba a la derecha)
    ax.text(0.95, 0.95, "ZONA CRÍTICA\nAlta Población +\nAlta Vulnerabilidad", 
            transform=ax.transAxes, ha="right", va="top", 
            fontsize=11, fontweight="bold", color="#b2182b", alpha=0.8,
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=3))
            
    ax.set_title("Matriz de Riesgo de los Huecos Topológicos", fontsize=13)
    ax.set_xlabel("Población Total viviendo en el hueco", fontsize=11)
    ax.set_ylabel("% de esa población SIN seguro médico", fontsize=11)
    
    # Etiquetar los 5 huecos más poblados para contexto
    top5 = df_prioridad.nlargest(5, "pob_afectada")
    for _, row in top5.iterrows():
        ax.annotate(
            f"#{int(row['hueco_id'])}",
            (row["pob_afectada"], row["pct_sin_salud_prom"]),
            xytext=(6, 6), textcoords="offset points",
            fontsize=10, fontweight="bold"
        )
        
    ax.legend(title="Prioridad", bbox_to_anchor=(1.05, 1), loc='upper left')

    # ---------------------------------------------------------
    # 2. Bar Chart: Composición de los Peores Huecos (Limpiado)
    # ---------------------------------------------------------
    ax = axes[1]
    
    top10 = df_prioridad.nlargest(10, "pob_afectada").copy()
    top10["pob_con_salud"] = top10["pob_afectada"] - top10["pob_sin_salud"]
    top10["hueco_label"] = "Hueco #" + top10["hueco_id"].astype(int).astype(str)
    
    # Ordenar para que el mayor quede arriba
    top10 = top10.sort_values("pob_afectada", ascending=True)
    
    bar_width = 0.7
    y_pos = np.arange(len(top10))
    
    # Barra de vulnerables (Sin seguro)
    ax.barh(y_pos, top10["pob_sin_salud"], bar_width, 
            label="Sin Seguro Médico", color="#b2182b", edgecolor="white")
    # Barra de los que tienen seguro pero están en el hueco
    ax.barh(y_pos, top10["pob_con_salud"], bar_width, left=top10["pob_sin_salud"], 
            label="Con Seguro (pero sin clínica cercana)", color="#d1e5f0", edgecolor="white")
    
    # Anotar el porcentaje exacto dentro de la barra roja
    for i, (_, row) in enumerate(top10.iterrows()):
        pct = row["pct_sin_salud_prom"]
        # Posicionar el texto un poco hacia la izquierda del borde derecho de la barra roja
        # Si la barra es muy pequeña, lo ponemos a la derecha
        x_pos = row["pob_sin_salud"] / 2
        ax.text(x_pos, i, f"{pct:.1f}%", 
                va='center', ha='center', color='white', fontweight='bold', fontsize=9)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(top10["hueco_label"], fontsize=11)
    ax.set_title("Top 10 Peores Huecos por Volumen Poblacional", fontsize=13)
    ax.set_xlabel("Número total de personas afectadas", fontsize=11)
    ax.legend(loc='lower right')
    
    plt.tight_layout()
    
    # Guardar
    ruta = config.FIGURAS_DIR / f"matriz_riesgo_{region}.png"
    plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    
    print(f"  Gráfico guardado: {ruta}")
    return ruta
