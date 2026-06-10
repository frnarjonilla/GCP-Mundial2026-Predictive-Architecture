import functions_framework
from google.cloud import bigquery
import pandas as pd
import numpy as np

@functions_framework.http
def calcular_fuerzas_poisson(request):
    client = bigquery.Client()
    
    # 1. Obtener el último ranking FIFA disponible para cada país
    query_ranking = """
        WITH ranking_reciente AS (
            SELECT 
                team as equipo,
                CAST(rank AS INT64) as ranking,
                CAST(total_points AS FLOAT64) as puntos,
                ROW_NUMBER() OVER(PARTITION BY team ORDER BY semester DESC) as rn
            FROM `mundial_bronze.raw_ranking_fifa`
        )
        SELECT equipo, ranking, puntos 
        FROM ranking_reciente 
        WHERE rn = 1
    """
    df_ranking = client.query(query_ranking).to_dataframe()
    
    # 2. Extraer los partidos históricos (desde 2014 y no amistosos)
    query_partidos = """
        SELECT 
            home_team, 
            away_team, 
            CAST(home_score AS INT64) as home_score, 
            CAST(away_score AS INT64) as away_score
        FROM `mundial_bronze.raw_historico_partidos`
        WHERE SAFE_CAST(date AS DATE) >= '2014-01-01'
          AND tournament != 'Friendly'
    """
    df_partidos = client.query(query_partidos).to_dataframe()
    
    if df_partidos.empty or df_ranking.empty:
        return "Error: No se pudieron leer los datos de las tablas de Bronze", 500

    # 3. Cruzar partidos con el ranking de ambos equipos
    # Añadimos ranking del local
    df_m = pd.merge(df_partidos, df_ranking.rename(columns={'equipo': 'home_team', 'ranking': 'rank_home'}), on='home_team', how='inner')
    # Añadimos ranking del visitante
    df_m = pd.merge(df_m, df_ranking.rename(columns={'equipo': 'away_team', 'ranking': 'rank_away'}), on='away_team', how='inner')
    
    # 4. FUNCIÓN DE PONDERACIÓN (Factor de Calidad del Rival)
    # Si el rival está en el Top 30, el gol vale el 100%. A peor ranking, menos vale el gol.
    def calcular_factor(rank_rival):
        if rank_rival <= 30:
            return 1.0
        elif rank_rival <= 70:
            return 0.5
        elif rank_rival <= 100:
            return 0.2
        else:
            return 0.05 # Golear a selecciones muy bajas apenas suma

    df_m['factor_home'] = df_m['rank_away'].apply(calcular_factor) # El local recibe factor según el nivel del visitante
    df_m['factor_away'] = df_m['rank_home'].apply(calcular_factor) # El visitante recibe factor según el nivel del local
    
    # Aplicar ponderación a los goles
    df_m['goles_casa_pond'] = df_m['home_score'] * df_m['factor_home']
    df_m['goles_fuera_pond'] = df_m['away_score'] * df_m['factor_away']
    df_m['goles_rec_casa_pond'] = df_m['away_score'] * df_m['factor_home']
    df_m['goles_rec_fuera_pond'] = df_m['home_score'] * df_m['factor_away']
    
    # 5. Medias globales ponderadas
    media_goles_casa = df_m['goles_casa_pond'].mean()
    media_goles_fuera = df_m['goles_fuera_pond'].mean()
    media_global = (media_goles_casa + media_goles_fuera) / 2
    
    # 6. Agrupar estadísticas por selección
    stats_casa = df_m.groupby('home_team').agg(
        goles_anotados_casa=('goles_casa_pond', 'sum'),
        goles_recibidos_casa=('goles_rec_casa_pond', 'sum'),
        partidos_casa=('home_team', 'count')
    ).reset_index().rename(columns={'home_team': 'equipo'})
    
    stats_fuera = df_m.groupby('away_team').agg(
        goles_anotados_fuera=('goles_fuera_pond', 'sum'),
        goles_recibidos_fuera=('goles_rec_fuera_pond', 'sum'),
        partidos_fuera=('away_team', 'count')
    ).reset_index().rename(columns={'away_team': 'equipo'})
    
    stats = pd.merge(stats_casa, stats_fuera, on='equipo', how='outer').fillna(0)
    
    stats['partidos_totales'] = stats['partidos_casa'] + stats['partidos_fuera']
    stats['goles_anotados'] = stats['goles_anotados_casa'] + stats['goles_anotados_fuera']
    stats['goles_recibidos'] = stats['goles_recibidos_casa'] + stats['goles_recibidos_fuera']
    
    # Filtrar países con un mínimo de rodaje competitivo (al menos 10 partidos oficiales)
    stats = stats[stats['partidos_totales'] >= 10]
    
    # Calcular fuerzas finales de Poisson dividiendo por la media global
    stats['fuerza_ataque'] = (stats['goles_anotados'] / stats['partidos_totales']) / media_global
    stats['fuerza_defensa'] = (stats['goles_recibidos'] / stats['partidos_totales']) / media_global
    
    # 7. Unir con los datos limpios del ranking final para la capa Silver
    df_silver = pd.merge(stats, df_ranking, on='equipo', how='inner')
    
    df_silver = df_silver[['equipo', 'ranking', 'fuerza_ataque', 'fuerza_defensa']].copy()
    df_silver.columns = ['nombre_seleccion', 'ranking_fifa', 'fuerza_ataque', 'fuerza_defensa']
    
    df_silver['id_seleccion'] = df_silver['nombre_seleccion'].str[:3].str.upper()
    df_silver['grupo'] = None
    
    # Ordenar columnas
    df_silver = df_silver[['id_seleccion', 'nombre_seleccion', 'grupo', 'ranking_fifa', 'fuerza_ataque', 'fuerza_defensa']]
    
    # 8. Guardar en BigQuery
    table_id = "mundial_silver.dim_fuerzas_selecciones"
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    client.load_table_from_dataframe(df_silver, table_id, job_config=job_config).result()
    
    return f"Éxito: Se han calculado y guardado las fuerzas ponderadas de {len(df_silver)} selecciones oficiales.", 200