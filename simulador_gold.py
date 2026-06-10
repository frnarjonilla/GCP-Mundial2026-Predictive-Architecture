from google.cloud import bigquery
import pandas as pd
import numpy as np
import collections

def simular_torneo_montecarlo():
    # 1. CONEXIÓN A BIGQUERY USANDO TU ARCHIVO DE CLAVES NATIVO
    client = bigquery.Client.from_service_account_json("claves_gcp.json")
    
    query = """
        SELECT nombre_seleccion, ranking_fifa, fuerza_ataque, fuerza_defensa
        FROM `mundial_silver.dim_fuerzas_selecciones`
    """
    df_selecciones = client.query(query).to_dataframe()
    
    # 2. DICCIONARIO REAL Y DEFINITIVO DE GRUPOS - FIFA WORLD CUP 2026
    grupos_oficiales = {
        'Grupo A': ['Mexico', 'South Africa', 'South Korea', 'Czech Republic'],
        'Grupo B': ['Canada', 'Bosnia and Herzegovina', 'Qatar', 'Switzerland'],
        'Grupo C': ['Brazil', 'Morocco', 'Haiti', 'Scotland'],
        'Grupo D': ['United States', 'Paraguay', 'Australia', 'Turkey'],
        'Grupo E': ['Germany', 'Curaçao', 'Ivory Coast', 'Ecuador'],
        'Grupo F': ['Netherlands', 'Japan', 'Sweden', 'Tunisia'],
        'Grupo G': ['Belgium', 'Egypt', 'Iran', 'New Zealand'],
        'Grupo H': ['Spain', 'Cape Verde', 'Saudi Arabia', 'Uruguay'],
        'Grupo I': ['France', 'Senegal', 'Iraq', 'Norway'],
        'Grupo J': ['Argentina', 'Algeria', 'Austria', 'Jordan'],
        'Grupo K': ['Portugal', 'DR Congo', 'Uzbekistan', 'Colombia'],
        'Grupo L': ['England', 'Croatia', 'Ghana', 'Panama']
    }
    
    # Mapear grupos al DataFrame
    mapeo_grupos = {}
    for grupo, equipos in grupos_oficiales.items():
        for eq in equipos:
            mapeo_grupos[eq] = grupo
            
    df_selecciones['grupo'] = df_selecciones['nombre_seleccion'].map(mapeo_grupos)
    df_mundial = df_selecciones[df_selecciones['grupo'].notna()].copy()
    
    fuerzas = df_mundial.set_index('nombre_seleccion').to_dict(orient='index')
    
    N_SIMULACIONES = 10000
    exitos = collections.defaultdict(lambda: {'fase_grupos': 0, 'dieciseisavos': 0, 'octavos': 0, 'cuartos': 0, 'semifinal': 0, 'finalista': 0, 'campeon': 0})
    
    MEDIA_GOLES = 1.25  
    
    def simular_partido(local, visitante, eliminatoria=False):
        f_loc = fuerzas.get(local, {'fuerza_ataque': 1.0, 'fuerza_defensa': 1.0})
        f_vis = fuerzas.get(visitante, {'fuerza_ataque': 1.0, 'fuerza_defensa': 1.0})
        
        lambda_local = f_loc['fuerza_ataque'] * f_vis['fuerza_defensa'] * MEDIA_GOLES
        lambda_visitante = f_vis['fuerza_ataque'] * f_loc['fuerza_defensa'] * MEDIA_GOLES
        
        goles_local = np.random.poisson(max(lambda_local, 0.05))
        goles_visitante = np.random.poisson(max(lambda_visitante, 0.05))
        
        if eliminatoria and goles_local == goles_visitante:
            return (1, 0) if np.random.rand() > 0.5 else (0, 1)
            
        return goles_local, goles_visitante

    print("Ejecutando las 10.000 simulaciones CON LOS GRUPOS REALES DE LA FIFA...")
    
    for _ in range(N_SIMULACIONES):
        clasificados_fase_final = []
        terceros_reporte = []
        
        # --- FASE DE GRUPOS ---
        for grupo, equipos in grupos_oficiales.items():
            pts = {eq: 0 for eq in equipos}
            goles_favor = {eq: 0 for eq in equipos}
            
            for i in range(len(equipos)):
                for j in range(i + 1, len(equipos)):
                    eq1, eq2 = equipos[i], equipos[j]
                    g1, g2 = simular_partido(eq1, eq2, eliminatoria=False)
                    
                    if g1 > g2:
                        pts[eq1] += 3
                    elif g2 > g1:
                        pts[eq2] += 3
                    else:
                        pts[eq1] += 1
                        pts[eq2] += 1
                    goles_favor[eq1] += g1
                    goles_favor[eq2] += g2
            
            posiciones = sorted(equipos, key=lambda x: (pts[x], goles_favor[x]), reverse=True)
            
            # Pasan los dos primeros de forma directa (Sumamos hito)
            clasificados_fase_final.append(posiciones[0])
            clasificados_fase_final.append(posiciones[1])
            exitos[posiciones[0]]['fase_grupos'] += 1
            exitos[posiciones[1]]['fase_grupos'] += 1
            
            # Guardar el tercero para la repesca
            terceros_reporte.append({'equipo': posiciones[2], 'puntos': pts[posiciones[2]], 'goles': goles_favor[posiciones[2]]})

        # Clasificar a los 8 mejores terceros globales
        mejores_terceros = sorted(terceros_reporte, key=lambda x: (x['puntos'], x['goles']), reverse=True)[:8]
        for t in mejores_terceros:
            clasificados_fase_final.append(t['equipo'])
            exitos[t['equipo']]['fase_grupos'] += 1  # Solo suma si pasa la repesca
            
        # --- FASE ELIMINATORIA DIRECTA ---
        for eq in clasificados_fase_final: exitos[eq]['dieciseisavos'] += 1
        
        # 1. Dieciseisavos
        octavos = []
        for i in range(0, 32, 2):
            g1, g2 = simular_partido(clasificados_fase_final[i], clasificados_fase_final[i+1], eliminatoria=True)
            octavos.append(clasificados_fase_final[i] if g1 > g2 else clasificados_fase_final[i+1])
            
        # 2. Octavos
        for eq in octavos: exitos[eq]['octavos'] += 1
        cuartos = []
        for i in range(0, 16, 2):
            g1, g2 = simular_partido(octavos[i], octavos[i+1], eliminatoria=True)
            cuartos.append(octavos[i] if g1 > g2 else octavos[i+1])
            
        # 3. Cuartos
        for eq in cuartos: exitos[eq]['cuartos'] += 1
        semis = []
        for i in range(0, 8, 2):
            g1, g2 = simular_partido(cuartos[i], cuartos[i+1], eliminatoria=True)
            semis.append(cuartos[i] if g1 > g2 else cuartos[i+1])
            
        # 4. Semifinales
        for eq in semis: exitos[eq]['semifinal'] += 1
        g1, g2 = simular_partido(semis[0], semis[1], eliminatoria=True)
        f1 = semis[0] if g1 > g2 else semis[1]
        g3, g4 = simular_partido(semis[2], semis[3], eliminatoria=True)
        f2 = semis[2] if g3 > g4 else semis[3]
        
        # 5. Final
        exitos[f1]['finalista'] += 1
        exitos[f2]['finalista'] += 1
        
        gf1, gf2 = simular_partido(f1, f2, eliminatoria=True)
        campeon = f1 if gf1 > gf2 else f2
        exitos[campeon]['campeon'] += 1

   # 5. GENERAR DATAFRAME DE RESULTADOS EN ESPAÑOL (Con todas las fases completas)
    filas_reporte = []
    for eq, conteos in exitos.items():
        if eq in mapeo_grupos:
            filas_reporte.append({
                'nombre_seleccion': eq,
                'grupo_oficial': mapeo_grupos[eq],
                'probabilidad_fase_grupos_pct': (conteos['fase_grupos'] / N_SIMULACIONES) * 100,
                'probabilidad_dieciseisavos_pct': (conteos['dieciseisavos'] / N_SIMULACIONES) * 100,
                'probabilidad_octavos_pct': (conteos['octavos'] / N_SIMULACIONES) * 100,
                'probabilidad_cuartos_pct': (conteos['cuartos'] / N_SIMULACIONES) * 100,
                'probabilidad_semifinal_pct': (conteos['semifinal'] / N_SIMULACIONES) * 100,
                'probabilidad_final_pct': (conteos['finalista'] / N_SIMULACIONES) * 100,  # Jugar la final
                'probabilidad_campeon_pct': (conteos['campeon'] / N_SIMULACIONES) * 100   # Ganar el mundial
            })
            
    df_gold = pd.DataFrame(filas_reporte).fillna(0)
    df_gold = df_gold.sort_values(by='probabilidad_campeon_pct', ascending=False).reset_index(drop=True)
    
    # 6. ENVIAR RESULTADOS A LA CAPA GOLD
    tabla_destino = "mundial_gold.reporte_probabilidades"
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    
    client.load_table_from_dataframe(df_gold, tabla_destino, job_config=job_config).result()
    print(f"¡Éxito absoluto! La capa Gold REAL e HISTÓRICA se ha actualizado en '{tabla_destino}'.")

if __name__ == "__main__":
    simular_torneo_montecarlo()