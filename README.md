# CV Match Analyzer
Analyseur de compatibilité CV ↔ offre d'emploi — simule les filtres ATS automatiques.

## Lancer
```bash
cd ~/cv-match && .venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

## Ce que ça fait
- L'utilisateur colle le texte de l'offre + uploade son CV (PDF ou DOCX)
- L'app extrait les exigences de l'offre (compétences, outils, années d'expérience, langues, diplômes)
- Elle compare avec le contenu du CV
- Score de passage des tris ATS + détail par critère + mots-clés manquants + conseils

## Analyse (moteur ATS simulé, sans LLM)
1. Extraction keywords pondérées (hard skills, softwares, méthodologies) — dictionnaire FR/EN
2. Matching flou (stemming léger, synonymes: k8s↔kubernetes, react.js↔react)
3. Expérience: détection des années réclamées vs dates du CV
4. Pénalité formatage ATS-hostile (tables, colonnes, images détectées dans le PDF)
5. Score global 0-100 avec seuils: <40 rejeté, 40-70 incertain, >70 passe
