# 🏆 Mundial 2026 Predictive Model & Simulator (Monte Carlo & Poisson)

Arquitectura de datos end-to-end bajo metodología **Medallion** implementada íntegramente en **Google Cloud Platform (GCP)** y **Python** para predecir y simular los resultados del Mundial de la FIFA 2026 mediante procesos probabilísticos.

## 🏗️ Arquitectura del Pipeline (Medallion)

El proyecto está estructurado en tres capas lógicas para garantizar la trazabilidad, limpieza y escalabilidad de los datos:

* **Capa Bronze (Raw):** Ingesta y tratamiento de datos históricos de partidos internacionales y rankings FIFA, automatizando el mapeo de esquemas y tipos de datos dinámicos mediante BigQuery.
* **Capa Silver (Trusted):** Desarrollo de una **Google Cloud Function** en Python que consume los datos de la capa Bronze y calcula matemáticamente los factores de **Fuerza de Ataque** y **Fuerza de Defensa** de las selecciones utilizando una **Distribución de Poisson**.
* **Capa Gold (Curated/Insights):** Script maestro en Python optimizado para interactuar de forma nativa con **BigQuery** mediante cuentas de servicio (IAM). Ejecuta un algoritmo de **Monte Carlo con 10.000 iteraciones** integrando el cuadro real de grupos de la FIFA (formato de 48 selecciones) y calcula las probabilidades de supervivencia por cada fase del torneo.

## 📊 Principales Insights (Resultados del Modelo)
Tras la simulación masiva del torneo antes del pitido inicial, el modelo destaca a **España como la máxima candidata al título con un 17.0% de probabilidad**, impulsada por su alto índice de pegada ofensiva ($3.68$) calculado en la capa Silver, superando a selecciones como Brasil (13.25%) y Argentina (10.34%).

## 🛠️ Tecnologías Utilizadas
* **Cloud Provider:** Google Cloud Platform (GCP) — Cloud Functions, Cloud Run, IAM service accounts.
* **Data Warehouse:** Google BigQuery.
* **Language & Libraries:** Python 3.12 (Pandas, NumPy, Google Cloud BigQuery Client).
* **Visualization:** Power BI (Conexión directa vía BigQuery REST API).