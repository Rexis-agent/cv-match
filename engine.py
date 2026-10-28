"""Moteur d'analyse CV ↔ offre — simule un tri ATS automatique (sans LLM)."""
import re
import unicodedata
from datetime import date

# ---------------------------------------------------------------- normalisation
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()

def stem(w: str) -> str:
    for suf in ("ations", "ation", "atifs", "atives", "atif", "ative",
                "ements", "ement", "ités", "ité", "ances", "ance",
                "ings", "ing", "ies", "ers", "ies", "es", "s", "x"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[: -len(suf)]
    return w

# ---------------------------------------------------------------- dictionnaires
SYNONYMS = [
    {"javascript", "js", "ecmascript"},
    {"typescript", "ts"},
    {"kubernetes", "k8s"},
    {"docker", "conteneurisation", "containerisation"},
    {"react", "reactjs", "react.js"},
    {"react native", "reactnative"},
    {"node", "nodejs", "node.js"},
    {"vue", "vuejs", "vue.js"},
    {"angular"},
    {"next", "nextjs", "next.js"},
    {"python", "py"},
    {"machine learning", "ml", "apprentissage automatique"},
    {"deep learning", "dl"},
    {"intelligence artificielle", "ai", "ia"},
    {"llm", "grand modele de langage", "grands modeles de langage"},
    {"nlp", "traitement du langage naturel", "natural language processing"},
    {"sql", "mysql", "postgresql", "postgres", "mariadb"},
    {"nosql", "mongodb", "mongo", "cassandra", "redis"},
    {"aws", "amazon web services"},
    {"gcp", "google cloud", "google cloud platform"},
    {"azure", "microsoft azure"},
    {"ci cd", "cicd", "ci/cd", "integration continue", "continuous integration"},
    {"devops"},
    {"gitlab", "git"},
    {"github"},
    {"jenkins"},
    {"terraform", "iac", "infrastructure as code"},
    {"ansible"},
    {"agile", "scrum", "kanban", "methodes agiles"},
    {"rest", "restful", "api rest"},
    {"graphql", "apollo"},
    {"microservices", "architecture microservice", "microservice"},
    {"php"},
    {"laravel", "symfony"},
    {"java", "java ee", "jee"},
    {"spring", "spring boot", "springboot"},
    {"csharp", "c#", "dotnet", ".net"},
    {"cpp", "c++"},
    {"rust"},
    {"go", "golang"},
    {"swift", "ios"},
    {"kotlin", "android"},
    {"flutter", "dart"},
    {"figma", "ui ux", "ux ui", "ux design", "ui design", "product design"},
    {"photoshop", "adobe photoshop"},
    {"illustrator", "adobe illustrator"},
    {"indesign", "adobe indesign"},
    {"after effects", "adobe after effects"},
    {"excel", "microsoft excel", "vba"},
    {"powerpoint", "microsoft powerpoint"},
    {"word", "microsoft word"},
    {"sap"},
    {"salesforce", "crm", "hubspot"},
    {"seo", "referencement naturel", "referencement"},
    {"sea", "google ads", "adwords"},
    {"google analytics", "ga4", "analytics"},
    {"wordpress", "cms"},
    {"shopify", "e commerce", "ecommerce", "commerce en ligne"},
    {"stripe", "paiement"},
    {"tableau", "power bi", "powerbi", "looker", "dataviz", "data visualisation", "metabase", "superset"},
    {"spark", "pyspark", "apache spark"},
    {"hadoop", "big data"},
    {"airflow", "dagster", "orchestration"},
    {"dbt", "data build tool"},
    {"snowflake", "databricks", "redshift", "bigquery", "data warehouse", "entrepot de donnees"},
    {"etl", "elt", "pipelines de donnees", "pipeline"},
    {"powerpoint"},
    {"jira", "confluence", "atlassian"},
    {"notion", "asana", "trello", "slack", "teams"},
    {"bilingue", "anglais courant", "english fluent", "fluent english", "anglais professionnel"},
    {"francais", "french"},
    {"allemand", "german"},
    {"espagnol", "spanish"},
    {"espagnol"},
]

KNOWN_SKILLS = sorted({s for grp in SYNONYMS for s in grp}, key=len, reverse=True)

STOP_FR = set("""et ou de des du d un une pour avec dans sur par au aux ce cette ces que qui
quoi dont ou est sont sera seraient avoir avoirs plus moins tres tres bien non oui
the and of for with in on at to by as is are be been was were will would can could
you your our their his her its it this that these those from or per via job role
poste mission offres emploi candidat candidate profil recherche CDI CDD stage
description responsibilities missions responsibilities experience experiences
ans annees year years mois minimum minimum requise requises exige exiges souhaite
souhaitees apprecie appreciated atout plus bucky salaire salary avantages benefits
a of""".split())

def canon_set(word: str) -> frozenset:
    for grp in SYNONYMS:
        if word in grp:
            return frozenset(grp)
    return frozenset({word})

DIPLOME_EQ = {}
for _k in ("bac +5", "bac+5", "bac 5", "master", "ingenieur", "engineer", "engineer degree", "mba"):
    DIPLOME_EQ[_k] = "BAC5"
for _k in ("bac +3", "bac+3", "bac 3", "licence", "bachelor"):
    DIPLOME_EQ[_k] = "BAC3"
for _k in ("phd", "doctorat"):
    DIPLOME_EQ[_k] = "DOC"

# ---------------------------------------------------------------- extraction offre
SKILL_CONTEXT = re.compile(
    r"(comp[eé]tences?|ma[îi]tris(?:er|e|ez)|connaissances?|exp[eé]rience(?:s)? (?:avec|de|en)|"
    r"skills?|profils?|stack|techniques?|outils?|tools?|technologies|frameworks?|logiciels?|"
    r"vous ma[îi]trisez|requise?|exig[eé](?:e|es)|souhait[eé](?:e|es))", re.I)

def extract_offer_requirements(offer_text: str):
    """Retourne (skills_requises, skills_appreciees, annees_exp, langues, diplome)."""
    n = norm(offer_text)
    # découper en segments aux transitions de statut (Requis/Requis -> Apprecié -> ...) même
    # si tout est sur une seule ligne: chaque compétence hérite du marqueur le plus proche AVANT elle.
    lines = offer_text.splitlines()
    lines = [seg for l in lines for seg in re.split(
        r"(?=(?:comp[eé]tences? (?:requises?)?|requirements?|appreci[eé]e?s?|nice to haves?|"
        r"requis(?:e|es)?|exig[eé](?:e|es)|obligatoire|appr[eé]ci[eé](?:e|es)|atouts?|bonus|"
        r"profil recherch[eé]|missions?|vous ma[îi]trisez|ma[îi]triser?))", l, flags=re.I)]
    found = {}
    for skill in KNOWN_SKILLS:
        pat = r"(?<![a-z0-9])" + re.escape(norm(skill)) + r"(?![a-z0-9])"
        for i, line in enumerate(lines):
            if re.search(pat, norm(line)):
                # exigé si la ligne OU une voisine contient un marqueur fort, sinon contexte large
                ctx = " ".join(lines[max(0, i - 1): i + 2])
                strong = re.search(
                    r"(requise?|exig[eé]|obligatoire|imp[eé]ratif|must|necessary|indispensable|"
                    r"vous ma[îi]trisez|ma[îi]trise parfaite|solid(?:e|es) (?:comp[eé]tence|connaissance|exp[eé]rience))",
                    line, re.I)
                bonus_only = re.search(r"(appr[eé]ci|atout|bonus|nice.to.have|would.be.a|est un plus|sont un plus)", ctx, re.I)
                medium = SKILL_CONTEXT.search(ctx) and not bonus_only
                bucket = found.setdefault(canon_set(skill).__iter__().__next__() if canon_set(skill) else skill,
                                          {"label": skill, "required": False, "seen": False})
                bucket["seen"] = True
                bucket["required"] = bucket["required"] or bool(strong or medium)
    # années d'expérience demandées
    m = re.search(r"(\d+)\s*(?:\+)?\s*(?:ans|an|ann[eé]es?|years?|yr)s?\s*(?:d'|de |of )?"
                  r"(?:exp[eé]rience|experience)", n)
    annees = int(m.group(1)) if m else None
    # langues
    langues = []
    if re.search(r"anglais", n) or re.search(r"english", n):
        langues.append("Anglais")
    if re.search(r"allemand", n) or re.search(r"german", n):
        langues.append("Allemand")
    if re.search(r"espagnol", n) or re.search(r"spanish", n):
        langues.append("Espagnol")
    # diplôme
    m = re.search(r"(bac\s*\+?\s*5|bac\s*\+?\s*3|master|licence|bachelor|ing[eé]nieur|engineer(?:ing)? degree|phd|doctorat|mba)", n)
    diplome = m.group(1) if m else None
    skills = [v for v in found.values()]
    return skills, annees, langues, diplome

# ---------------------------------------------------------------- matching CV
def cv_text_stats(cv_text: str):
    n = norm(cv_text)
    words = set(stem(w) for w in re.findall(r"[a-z0-9+#.]{2,}", n))
    return n, words

def skill_in_cv(skill_label: str, n_cv: str, stems_cv: set) -> bool:
    pat = r"(?<![a-z0-9])" + re.escape(norm(skill_label)) + r"(?![a-z0-9])"
    if re.search(pat, n_cv):
        return True
    # tentative par stem du dernier mot (ex: "orchestration" -> "orchestr")
    toks = [stem(t) for t in norm(skill_label).split() if t not in STOP_FR]
    if toks and all(t in stems_cv or any(s.startswith(t[:6]) for s in stems_cv) for t in toks):
        return True
    # synonymes du groupe
    for syn in canon_set(norm(skill_label)):
        if syn == norm(skill_label):
            continue
        pat2 = r"(?<![a-z0-9])" + re.escape(syn) + r"(?![a-z0-9])"
        if re.search(pat2, n_cv):
            return True
    return False

def cv_years_of_experience(cv_text: str) -> int | None:
    """Max entre: somme des périodes datées, et mention 'X ans d'expérience'."""
    n = norm(cv_text)
    # périodes 2019-2022 / 01/2020 - 03/2023
    spans = re.findall(r"(20\d{2})\s*(?:[/\-–]|a|to|jusqu'a|jusqua)\s*(20\d{2}|aujourdhui|present|now|actuel|current)", n)
    total = 0
    for a, b in spans:
        try:
            y1 = int(a)
            y2 = int(b) if b.isdigit() else date.today().year
            if 1990 <= y1 <= date.today().year + 1 and 0 <= y2 - y1 <= 45:
                total += y2 - y1
        except ValueError:
            pass
    m = re.search(r"(\d+)\s*\+?\s*(?:ans?|annees?|years?)\s*(?:d'|de |of )?(?:exp[eé]rience|experience)", n)
    if m:
        return max(int(m.group(1)), total)
    return total if total else None

# ---------------------------------------------------------------- score ATS
def analyze(offer_text: str, cv_text: str, pdf_flags: dict | None = None) -> dict:
    skills, annees_req, langues, diplome = extract_offer_requirements(offer_text)
    n_cv, stems_cv = cv_text_stats(cv_text)
    cv_years = cv_years_of_experience(cv_text)

    matched, missing_required, missing_bonus = [], [], []
    for s in skills:
        ok = skill_in_cv(s["label"], n_cv, stems_cv)
        entry = {"label": s["label"], "required": s["required"], "found": ok}
        (matched if ok else (missing_required if s["required"] else missing_bonus)).append(entry)

    def _dip_ok():
        if not diplome:
            return False
        want = DIPLOME_EQ.get(diplome, diplome)
        # le CV satisfait le diplôme si n'importe quelle mention du même niveau (ou supérieur) y figure
        order = ["BAC3", "BAC5", "DOC"]
        if want in order:
            floor = order.index(want)
            for lbl, lvl in DIPLOME_EQ.items():
                if order.index(lvl) >= floor:
                    pat = r"(?<![a-z0-9])" + re.escape(norm(lbl)) + r"(?![a-z0-9])"
                    if re.search(pat, n_cv):
                        return True
            return False
        return skill_in_cv(diplome, n_cv, stems_cv)

    detail = {"skills": matched + missing_required + missing_bonus,
              "annees_requises": annees_req, "annees_cv": cv_years,
              "langues": langues, "diplome": diplome,
              "langues_ok": [l for l in langues if skill_in_cv(l, n_cv, stems_cv)],
              "diplome_ok": _dip_ok()}

    # ---- score
    n_req = len(missing_required) + len([m for m in matched if m["required"]])
    n_bonus = len(missing_bonus) + len([m for m in matched if not m["required"]])
    score = 70.0
    if n_req:
        score -= 45 * (len(missing_required) / max(n_req, 1))  # jusqu'à -45 sur requis manquants
    if n_bonus:
        # le bonus ne pèse pleinement que si le requis est déjà fragile ( calibration:
        # 100% requis matché -> max -4 ; 0% requis matché -> max -12)
        req_cov = 1 - (len(missing_required) / max(n_req, 1))
        w = 2 + 8 * (1 - req_cov)
        score -= w * (len(missing_bonus) / max(n_bonus, 1))
    if annees_req and cv_years:
        if cv_years < annees_req:
            score -= min(20, (annees_req - cv_years) * 4)
        else:
            score += 3
    elif annees_req and not cv_years:
        score -= 6  # non détectable = léger doute ATS
    if langues and not detail["langues_ok"]:
        score -= 8
    if diplome and not detail["diplome_ok"]:
        score -= 5
    # pénalité formatage ATS-hostile
    if pdf_flags:
        if pdf_flags.get("tables"):
            score -= 6
        if pdf_flags.get("columns"):
            score -= 5
        if pdf_flags.get("image_heavy"):
            score -= 4
        if pdf_flags.get("low_text_ratio"):
            score -= 8
    score = max(2, min(98, round(score)))

    if score >= 70:
        verdict = "PASSE — votre CV a de fortes chances de franchir le tri automatique"
    elif score >= 45:
        verdict = "INCERTAIN — le tri automatique peut vous écarter : corrigez les manques ci-dessous"
    else:
        verdict = "REJET PROBABLE — trop de critères automatiques non satisfaits"

    # conseils
    tips = []
    for m in missing_required[:8]:
        tips.append(f"Ajoutez ou rendez explicite la compétence requise : « {m['label']} »")
    if annees_req and cv_years and cv_years < annees_req:
        tips.append(f"L'offre demande {annees_req} ans d'expérience ; vos dates laissent lire ~{cv_years} ans — mettez le total d'expérience en évidence en haut du CV.")
    if annees_req and not cv_years:
        tips.append("Vos années d'expérience ne sont pas lisibles automatiquement — ajoutez des dates complètes (MM/AAAA) et un total d'expérience.")
    if pdf_flags and pdf_flags.get("tables"):
        tips.append("Votre CV contient des tableaux — la plupart des ATS les lisent mal. Préférez du texte simple et des puces.")
    if pdf_flags and pdf_flags.get("columns"):
        tips.append("Mise en page à colonnes détectée — les ATS lisent souvent les colonnes dans le mauvais ordre. Une colonne unique est plus sûre.")
    if pdf_flags and pdf_flags.get("low_text_ratio"):
        tips.append("Peu de texte extrait : si votre CV est une image ou un design très graphique, l'ATS ne lit presque rien. Exportez un CV textuel.")
    if len(cv_text.split()) < 150:
        tips.append("CV très court détecté — les ATS comme les recruteurs attendent plus de contenu (expériences détaillées, outils, résultats).")
    if not missing_required and score < 85 and not tips:
        tips.append("Tous les critères détectés sont présents — pensez aussi à adapter le titre de votre CV à l'intitulé exact du poste.")

    return {"score": score, "verdict": verdict,
            "detail": detail,
            "matched": [m["label"] for m in matched],
            "missing_required": [m["label"] for m in missing_required],
            "missing_bonus": [m["label"] for m in missing_bonus],
            "tips": tips}
