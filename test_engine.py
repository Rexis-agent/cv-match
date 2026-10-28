"""Test bout-en-bout du moteur (sans serveur)."""
import engine, extractors

OFFRE = """Data Engineer (H/F) — CDI, Paris
Missions : concevoir des pipelines de données, industrialiser nos data products.
Compétences requises :
- 4 ans d'expérience minimum en data
- Python, SQL
- AWS, Docker, Kubernetes
- Airflow ou équivalent (requis)
- Anglais professionnel obligatoire
Apprécié : Snowflake, dbt, Spark
Diplôme : Bac+5"""

CV = """Jean Dupont — Data Engineer
jean.dupont@mail.com — Paris
Expérience professionnelle
2021 – 2024 : Data Engineer chez ACME
- Développement de pipelines ETL en Python et SQL
- Déploiement sur AWS (EKS) avec Docker et Kubernetes
- Orchestration avec Airflow (DAGs quotidiens)
2019 – 2021 : Analyste développeur
- Requêtes SQL complexes, scripts Python
Formation : Master Data Science (2019)
Langues : Anglais courant (C1), Espagnol notions
Compétences : Python, SQL, AWS, Docker, K8s, Airflow, Git"""

r = engine.analyze(OFFRE, CV)
print("score:", r["score"])
print("verdict:", r["verdict"])
print("matched:", r["matched"])
print("missing_required:", r["missing_required"])
print("missing_bonus:", r["missing_bonus"])
print("annees cv:", r["detail"]["annees_cv"], "| requises:", r["detail"]["annees_requises"])
print("langues ok:", r["detail"]["langues_ok"])
print("tips:", len(r["tips"]))

assert 55 <= r["score"] <= 98, "score incohérent"
assert "python" in r["matched"] and "sql" in r["matched"], "hard skills de base non matchées"
assert "kubernetes" in r["matched"], "synonyme k8s->kubernetes non résolu"
assert "airflow" in r["matched"], "airflow requis non matché"
assert r["detail"]["annees_cv"] and r["detail"]["annees_cv"] >= 4, "années non détectées"
assert "Anglais" in r["detail"]["langues_ok"], "anglais non détecté"
print("\n✓ moteur OK")

# test mauvais match
CV2 = "Marc — Commercial. 10 ans d'expérience en vente B2B. Compétences : relation client, prospection, CRM Salesforce."
r2 = engine.analyze(OFFRE, CV2)
print("score CV décalé:", r2["score"])
assert r2["score"] < 45, "CV décalé devrait être rejeté"
print("✓ discrimination OK (rejet profil hors-sujet)")
