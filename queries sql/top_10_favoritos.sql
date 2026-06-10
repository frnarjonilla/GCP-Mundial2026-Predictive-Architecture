SELECT 
    nombre_seleccion AS seleccion,
    grupo_oficial AS grupo,
    ROUND(probabilidad_campeon_pct, 2) AS probabilidad_campeon_pct
FROM 
    `mundial_gold.reporte_probabilidades`
WHERE 
    probabilidad_campeon_pct > 0
ORDER BY 
    probabilidad_campeon_pct DESC
LIMIT 10;