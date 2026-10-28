from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path

import engine
import extractors

app = FastAPI(title="CV Match Analyzer")

PAGE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CV Match — passez-vous les tris automatiques ?</title>
<style>
:root{
  --bg:#0d1117; --panel:#161b26; --panel2:#1b2130; --ink:#e8edf5; --muted:#9aa5b5;
  --line:#28304a; --accent:#5b8cff; --good:#39c98e; --mid:#e8b33e; --bad:#f0616d;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:40px 20px 80px}
header{margin-bottom:28px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}
h1 .dot{color:var(--accent)}
.sub{color:var(--muted);margin:0;font-size:14.5px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px;margin-bottom:18px}
label{display:block;font-weight:600;font-size:13px;margin:0 0 8px;color:var(--ink);
  text-transform:uppercase;letter-spacing:.06em}
textarea{width:100%;min-height:190px;background:var(--panel2);color:var(--ink);
  border:1px solid var(--line);border-radius:10px;padding:14px;font:14px/1.5 var(--mono);resize:vertical}
textarea:focus{outline:2px solid var(--accent);outline-offset:-1px}
.drop{border:2px dashed var(--line);border-radius:10px;padding:26px;text-align:center;
  color:var(--muted);cursor:pointer;transition:border-color .15s,background .15s}
.drop.hover,.drop.has{border-color:var(--accent);background:rgba(91,140,255,.06);color:var(--ink)}
.drop .fname{color:var(--accent);font-family:var(--mono);font-size:13px}
button.cta{margin-top:20px;width:100%;padding:15px;border:0;border-radius:10px;cursor:pointer;
  background:var(--accent);color:#fff;font-size:16px;font-weight:700;letter-spacing:.01em}
button.cta:disabled{opacity:.45;cursor:not-allowed}
button.cta:not(:disabled):hover{filter:brightness(1.08)}
.err{color:var(--bad);margin-top:10px;font-size:14px;min-height:20px}
/* résultats */
#res{display:none}
.scorebox{display:flex;gap:26px;align-items:center;background:var(--panel);border:1px solid var(--line);
  border-radius:14px;padding:24px;margin-bottom:18px;flex-wrap:wrap}
.gauge{position:relative;width:132px;height:132px;flex:none}
.gauge svg{transform:rotate(-90deg)}
.gauge .val{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.gauge .val b{font-size:34px;line-height:1}
.gauge .val span{font-size:11px;color:var(--muted);margin-top:2px}
.verdict{flex:1;min-width:240px}
.verdict h2{margin:0 0 6px;font-size:19px}
.verdict p{margin:0;color:var(--muted);font-size:14px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:760px){.cols{grid-template-columns:1fr}}
.panel h3{margin:0 0 12px;font-size:14px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
ul.kw{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:8px}
ul.kw li{background:var(--panel2);border:1px solid var(--line);border-radius:99px;padding:5px 12px;font-size:13.5px}
ul.kw li.ok{border-color:rgba(57,201,142,.5);color:var(--good)}
ul.kw li.ko{border-color:rgba(240,97,109,.5);color:var(--bad)}
ul.kw li.bo{color:var(--mid)}
.meta{color:var(--muted);font-size:14px;margin:0 0 14px}
.meta b{color:var(--ink)}
ol.tips{margin:0;padding-left:20px}
ol.tips li{margin-bottom:8px}
.none{color:var(--muted);font-style:italic}
.again{margin-top:20px;background:none;border:1px solid var(--line);color:var(--muted);
  padding:10px 18px;border-radius:8px;cursor:pointer}
.again:hover{color:var(--ink);border-color:var(--accent)}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>CV<span class="dot">·</span>Match</h1>
    <p class="sub">Votre CV passerait-il les tris automatiques (ATS) ? Collez l'offre, déposez le CV, le verdict tombe.</p>
  </header>

  <section id="form">
    <div class="panel">
      <label for="offer">1 · Texte de l'offre d'emploi</label>
      <textarea id="offer" placeholder="Collez ici l'intégralité de l'offre : missions, compétences requises, expérience, langues, diplôme…"></textarea>
    </div>
    <div class="panel">
      <label>2 · Votre CV (PDF ou DOCX)</label>
      <div class="drop" id="drop">
        <div id="dropIdle">Glissez votre CV ici, ou cliquez pour choisir un fichier<br><span style="font-size:12.5px">PDF · DOCX · TXT — max 5 Mo</span></div>
        <div id="dropFile" style="display:none"></div>
        <input type="file" id="file" accept=".pdf,.docx,.txt,.doc,.md" hidden>
      </div>
    </div>
    <button class="cta" id="go" disabled>Analyser mes chances</button>
    <div class="err" id="err"></div>
  </section>

  <section id="res">
    <div class="scorebox">
      <div class="gauge">
        <svg width="132" height="132">
          <circle cx="66" cy="66" r="56" fill="none" stroke="#28304a" stroke-width="12"/>
          <circle id="arc" cx="66" cy="66" r="56" fill="none" stroke="#5b8cff" stroke-width="12"
                  stroke-linecap="round" stroke-dasharray="351.9" stroke-dashoffset="351.9"/>
        </svg>
        <div class="val"><b id="scoreN">–</b><span>/ 100</span></div>
      </div>
      <div class="verdict">
        <h2 id="verdictT"></h2>
        <p id="verdictS"></p>
      </div>
    </div>

    <div class="cols">
      <div class="panel" id="pMatch">
        <h3>Compétences détectées dans votre CV</h3>
        <ul class="kw" id="okList"></ul>
        <p class="none" id="okEmpty" style="display:none">Aucune compétence de l'offre retrouvée telle quelle.</p>
      </div>
      <div class="panel" id="pMiss">
        <h3>Manquant — exigé par l'offre</h3>
        <ul class="kw" id="koList"></ul>
        <p class="none" id="koEmpty" style="display:none">Rien de manquant côté compétences exigées. 👌</p>
      </div>
    </div>

    <div class="panel" id="pDetails">
      <h3>Lecture automatique de votre CV</h3>
      <p class="meta" id="metaLine"></p>
    </div>

    <div class="panel">
      <h3>Comment augmenter vos chances</h3>
      <ol class="tips" id="tips"></ol>
      <p class="none" id="tipsEmpty" style="display:none">Aucun point de friction détecté — solide dossier.</p>
    </div>

    <button class="again" onclick="location.reload()">↺ Analyser une autre offre</button>
  </section>
</div>

<script>
const $=id=>document.getElementById(id);
let fileData=null;
const drop=$('drop'), input=$('file');
drop.onclick=()=>input.click();
['dragover','dragenter'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.add('hover')}));
['dragleave','drop'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.remove('hover')}));
drop.addEventListener('drop',ev=>{const f=ev.dataTransfer.files[0];if(f)take(f)});
input.onchange=()=>{if(input.files[0])take(input.files[0])};
function take(f){
  if(f.size>5*1024*1024){err('Fichier trop lourd (max 5 Mo)');return}
  fileData=f; drop.classList.add('has');
  $('dropIdle').style.display='none';
  $('dropFile').style.display='block';
  $('dropFile').innerHTML='📄 <span class="fname">'+f.name+'</span> — '+(f.size/1024).toFixed(0)+' Ko';
  err(''); check();
}
$('offer').addEventListener('input',check);
function check(){$('go').disabled=!($('offer').value.trim().length>80&&fileData)}
function err(m){$('err').textContent=m}

$('go').onclick=async()=>{
  err(''); $('go').disabled=true; $('go').textContent='Analyse en cours…';
  const fd=new FormData();
  fd.append('offer',$('offer').value);
  fd.append('file',fileData);
  try{
    const r=await fetch('/api/analyze',{method:'POST',body:fd});
    const j=await r.json();
    if(!r.ok){throw new Error(j.detail||'Erreur serveur')}
    render(j);
  }catch(e){err(e.message);$('go').disabled=false;$('go').textContent='Analyser mes chances'}
};

function render(j){
  $('form').style.display='none'; $('res').style.display='block';
  const C=2*Math.PI*56, pct=j.score/100;
  $('arc').style.strokeDashoffset=C*(1-pct);
  $('arc').style.stroke=j.score>=70?'#39c98e':(j.score>=45?'#e8b33e':'#f0616d');
  $('scoreN').textContent=j.score;
  const v=j.verdict.split('—');
  $('verdictT').textContent=v[0].trim();
  $('verdictT').style.color=j.score>=70?'var(--good)':(j.score>=45?'var(--mid)':'var(--bad)');
  $('verdictS').textContent=v.slice(1).join('—').trim();

  const ok=$('okList'); ok.innerHTML='';
  j.matched.forEach(k=>{const li=document.createElement('li');li.className='ok';li.textContent=k;ok.appendChild(li)});
  if(!j.matched.length)$('okEmpty').style.display='block';

  const ko=$('koList'); ko.innerHTML='';
  j.missing_required.forEach(k=>{const li=document.createElement('li');li.className='ko';li.textContent=k;ko.appendChild(li)});
  j.missing_bonus.forEach(k=>{const li=document.createElement('li');li.className='bo';li.textContent=k+' (bonus)';ko.appendChild(li)});
  if(!j.missing_required.length&&!j.missing_bonus.length)$('koEmpty').style.display='block';

  const d=j.detail; const bits=[];
  bits.push('Expérience : <b>'+(d.annees_cv!=null?('~'+d.annees_cv+' an(s) détectés'):'non détectable automatiquement')+'</b>'
    +(d.annees_requises?(' — l\\'offre exige <b>'+d.annees_requises+' an(s)</b>'):''));
  if(d.diplome) bits.push('Diplôme demandé : <b>'+d.diplome+'</b> — '+(d.diplome_ok?'retrouvé ✓':'non retrouvé ✗'));
  if(d.langues.length) bits.push('Langues : <b>'+d.langues.join(', ')+'</b> — retrouvées : <b>'+(d.langues_ok.length?d.langues_ok.join(', '):'aucune ✗')+'</b>');
  if(j.flags&&(j.flags.tables||j.flags.columns||j.flags.image_heavy||j.flags.low_text_ratio)){
    const f=[]; if(j.flags.tables)f.push('tableaux'); if(j.flags.columns)f.push('colonnes');
    if(j.flags.image_heavy)f.push('beaucoup d\\'images'); if(j.flags.low_text_ratio)f.push('très peu de texte lisible');
    bits.push('⚠ Format ATS-hostile détecté : <b>'+f.join(', ')+'</b>');
  } else bits.push('✓ Format lisible par un ATS (pas de piège majeur détecté)');
  $('metaLine').innerHTML=bits.join('<br>');

  const t=$('tips'); t.innerHTML='';
  j.tips.forEach(x=>{const li=document.createElement('li');li.textContent=x;t.appendChild(li)});
  if(!j.tips.length)$('tipsEmpty').style.display='block';
  window.scrollTo({top:0,behavior:'smooth'});
}
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE

@app.post("/api/analyze")
async def analyze(offer: str = Form(...), file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        return JSONResponse(status_code=413, content={"detail": "Fichier trop lourd (max 5 Mo)"})
    if len(offer.strip()) < 50:
        return JSONResponse(status_code=422, content={"detail": "Offre trop courte — collez le texte complet de l'annonce"})
    try:
        cv_text, flags = extractors.extract(data, file.filename or "")
    except ValueError as e:
        return JSONResponse(status_code=415, content={"detail": str(e)})
    except Exception:
        return JSONResponse(status_code=422, content={"detail": "Impossible de lire ce fichier — essayez un PDF ou DOCX"})
    if len(cv_text.split()) < 20:
        return JSONResponse(status_code=422, content={"detail": "Aucun texte lisible dans ce CV (probablement une image) — utilisez un PDF textuel"})
    result = engine.analyze(offer, cv_text, flags)
    result["flags"] = flags
    return result
