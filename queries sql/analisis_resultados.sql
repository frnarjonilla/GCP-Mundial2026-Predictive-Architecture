SELECT 
    nombre_seleccion, 
    grupo_oficial, 
    ROUND(probabilidad_fase_grupos_pct, 2) AS pasa_grupos_pct,
    ROUND(probabilidad_cuartos_pct, 2) AS cuartos_pct,
    ROUND(probabilidad_semifinal_pct, 2) AS semis_pct,
    ROUND(probabilidad_final_pct, 2) AS llega_a_final_pct,
    ROUND(probabilidad_campeon_pct, 2) AS campeon_pct
FROM `mundial_gold.reporte_probabilidades`