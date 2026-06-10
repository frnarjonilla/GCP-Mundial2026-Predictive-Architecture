SELECT 
    grupo_oficial AS grupo,
    ROUND(AVG(probabilidad_fase_grupos_pct), 2) AS promedio_pase_grupo_pct,
    ROUND(MAX(probabilidad_campeon_pct) - MIN(probabilidad_campeon_pct), 2) AS brecha_competitiva
FROM 
    `mundial_gold.reporte_probabilidades`
GROUP BY 
    grupo_oficial
ORDER BY 
    brecha_competitiva ASC; -- Menor brecha significa un grupo más cerrado y difícil