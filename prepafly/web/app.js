/* =============================================================================
   PrepaFlyPy — logique de l'interface (client de l'API FastAPI).
   Toute action passe par une route /api/... ; ici on construit les écrans et on
   affiche les réponses. Pas de logique métier (SORA, régimes, PDF) côté client :
   elle vit dans prepafly.core, appelée via l'API. Voir prepafly/server.py.
   ============================================================================= */
"use strict";

/* ---------- Accès API ---------- */
async function apiGet(path){ const r=await fetch(path); if(!r.ok) throw new Error(await r.text()); return r.json(); }
async function apiSend(path,method,body){
  const r=await fetch(path,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})});
  if(!r.ok) throw new Error((await r.text())||r.statusText); return r.json();
}
async function apiPdf(path,body){
  const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})});
  if(!r.ok) throw new Error(await r.text()); return r.blob();
}

/* ---------- État global ---------- */
let store=null, dronesDB=null, meta=null, strings={}, lang='fr';
let current='exploitant', currentDossierId='', dossierTab='mission';
let saveTimer=null, sectionOpen={}, pilotOpen={};

/* ---------- Petits outils de rendu ---------- */
function el(tag,cls,txt){const e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e;}
function card(kick,title,desc){
  const c=el('div','card');
  if(kick)c.appendChild(el('div','kick',kick));
  if(title)c.appendChild(el('h2',null,title));
  if(desc)c.appendChild(el('div','desc',desc));
  return c;
}
/* Carte repliable (accordéon de section). Renvoie {card, body}. */
function collCard(id,kick,title,desc,defOpen){
  if(sectionOpen[id]===undefined) sectionOpen[id]=(defOpen!==false);
  const open=sectionOpen[id];
  const c=el('div','card coll'+(open?' open':''));
  const head=el('div','coll-head'); head.appendChild(el('span','chev','▶'));
  const tt=el('div','coll-title'); if(kick)tt.appendChild(el('div','kick',kick)); tt.appendChild(el('h2',null,title));
  head.appendChild(tt);
  const body=el('div','coll-body'); body.hidden=!open;
  if(desc)body.appendChild(el('div','desc',desc));
  head.onclick=()=>{const o=!body.hidden; body.hidden=o; c.classList.toggle('open',!o); sectionOpen[id]=!o;};
  c.append(head,body); return {card:c,body};
}
/* Champ relié à obj[key] ; sauvegarde différée à chaque modif. */
function field(label,obj,key,opts){
  opts=opts||{};
  const f=el('div','field'+(opts.full?' full':''));
  f.appendChild(el('label',null,label));
  let inp;
  if(opts.type==='textarea'){ inp=el('textarea'); inp.rows=opts.rows||2; }
  else if(opts.type==='select'){
    inp=el('select');
    (opts.options||[]).forEach(o=>{const op=el('option'); op.value=o[0]; op.textContent=o[1]; inp.appendChild(op);});
  } else { inp=el('input'); inp.type=opts.type||'text'; }
  if(opts.readonly){ inp.readOnly=true; if(opts.type==='select') inp.disabled=true; }
  inp.value=(obj[key]!=null?obj[key]:'');
  const ev=(opts.type==='select')?'change':'input';
  inp.addEventListener(ev,()=>{ obj[key]=inp.value; scheduleSave(); if(opts.after)opts.after(inp.value); });
  f.appendChild(inp); return f;
}
function badge(cls,txt){return el('span','badge '+cls,txt);}

/* ---------- Sauvegarde ---------- */
function setSave(t){ const e=document.getElementById('saveState'); if(e)e.textContent=t; }
async function persist(){ try{ await apiSend('/api/store','PUT',store); setSave('Enregistré ✓'); }catch(e){ setSave('Erreur d’enregistrement'); } }
function scheduleSave(){ setSave('Modification…'); clearTimeout(saveTimer); saveTimer=setTimeout(persist,450); }

/* ---------- Constantes métier (libellés d'interface) ---------- */
const CLASSES=[['','—'],['C0','C0'],['C1','C1'],['C2','C2'],['C3','C3'],['C4','C4'],['C5','C5'],['C6','C6']];
const TYPEVOL=[['','—'],['VLOS','VLOS (en vue)'],['BVLOS','BVLOS (hors vue)']];
const ENVOPTS=[['','—'],['hors','Hors zone peuplée'],['peuple','Zone peuplée'],['rassemblement','Rassemblement de personnes']];
const DIST=[['','—'],['150m','≥ 150 m'],['30m','30 m'],['5m','5 m (basse vitesse)'],['0','Survol possible']];
const DENSITE=[['','—'],['ctrl','Zone contrôlée (tiers exclus)'],['d5','< 5 hab/km²'],['d50','< 50 hab/km²'],
  ['d500','< 500 hab/km²'],['d5000','< 5 000 hab/km²'],['d50000','< 50 000 hab/km²'],['dsup','Rassemblement']];
const YN=[['','—'],['yes','Oui'],['no','Non']];
const ARC_RES=[['','(= ARC initial)'],['a','a'],['b','b'],['c','c'],['d','d']];
const MENTIONS=['A1','A2','A3','STS-01','STS-02','CATS'];
const PREVOL=['NOTAM / SUP AIP consultés','Météo dans les limites','Zones & restrictions vérifiées (Géoportail)',
  'Périmètre de sécurité défini','Matériel & hélices vérifiés','Batteries chargées','Assurance RC à jour',
  'Documents à bord (exploitant, télépilote)','Consignes d’urgence rappelées','Briefing équipage effectué'];
const LINKS=[
  {ic:'🌦',t:'Météo France',u:'https://meteofrance.com/',d:'Prévisions locales'},
  {ic:'🛰',t:'Géoportail',u:'https://www.geoportail.gouv.fr/',d:'Cartes & restrictions'},
  {ic:'📋',t:'AlphaTango',u:'https://alphatango.aviation-civile.gouv.fr/',d:'Exploitant & déclarations'},
  {ic:'📢',t:'SOFIA (NOTAM)',u:'https://sofia-briefing.aviation-civile.gouv.fr/',d:'Avis aux navigateurs'},
  {ic:'🏛',t:'DGAC — spécifique',u:'https://www.ecologie.gouv.fr/politiques-publiques/exploitation-drones-categorie-specifique',d:'Réglementation pro'},
  {ic:'📖',t:'EASA — UAS',u:'https://www.easa.europa.eu/en/domains/civil-drones',d:'Cadre européen'},
];
const MARCHES=[
  {ic:'🔎',t:'France Marchés — drone',u:'https://www.francemarches.com/appels-offre/drone',d:'Appels d’offres « drone »'},
  {ic:'🔎',t:'Centrale des marchés',u:'https://centraledesmarches.com/recherche/drone',d:'Recherche « drone »'},
  {ic:'🏛',t:'BOAMP',u:'https://www.boamp.fr/',d:'Bulletin officiel'},
  {ic:'🏛',t:'PLACE — État',u:'https://www.marches-publics.gouv.fr/',d:'Marchés de l’État'},
];

/* ---------- Verrou PIN ---------- */
async function boot(){
  try{ meta=await apiGet('/api/meta'); }catch(e){ meta={version:'?'}; }
  const st=await apiGet('/api/pin/status');
  const t=document.getElementById('lockText'), pin=document.getElementById('pin'),
        pin2=document.getElementById('pin2'), btn=document.getElementById('lockBtn'), err=document.getElementById('lockErr');
  pin.style.display='block'; btn.style.display='block';
  if(!st.set){
    t.textContent='Choisissez un code PIN (4 chiffres min.) pour protéger l’accès.';
    pin2.style.display='block';
    btn.onclick=async()=>{ err.textContent='';
      if(pin.value.length<4){err.textContent='4 chiffres minimum.';return;}
      if(pin.value!==pin2.value){err.textContent='Les codes ne correspondent pas.';return;}
      try{ await apiSend('/api/pin/set','POST',{pin:pin.value}); unlock(); }catch(e){ err.textContent=String(e.message||e); }
    };
  } else {
    t.textContent='Entrez votre code PIN.';
    btn.onclick=async()=>{ err.textContent='';
      const r=await apiSend('/api/pin/verify','POST',{pin:pin.value});
      if(r.ok) unlock(); else err.textContent='Code incorrect.';
    };
    pin.addEventListener('keydown',e=>{ if(e.key==='Enter')btn.click(); });
  }
  pin.focus();
}
async function unlock(){
  document.getElementById('lock').style.display='none';
  document.getElementById('app').style.display='grid';
  store=await apiGet('/api/store');
  dronesDB=await apiGet('/api/drones');
  try{ strings=await apiGet('/api/i18n/'+lang); }catch(e){ strings={}; }
  renderNav(); renderView(); checkUpdate();
}
async function checkUpdate(){
  try{ const u=await apiGet('/api/update'); const bar=document.getElementById('updbar');
    if(u.update_available){ bar.className='updbar';
      bar.innerHTML=''; bar.appendChild(el('span',null,'Mise à jour '+u.latest+' disponible.'));
      const a=el('a','btn sm primary','Télécharger'); a.href=u.url; a.target='_blank'; bar.appendChild(a);
    }
  }catch(e){}
}

/* ---------- Navigation ---------- */
const NAV=[
  ['exploitant','👤 Exploitant'],['pilotes','🧑‍✈️ Télépilotes'],['dossiers','📁 Dossiers de vol'],
  ['SEP','Consultation'],
  ['checklist','✅ Check-list pré-vol'],['docs','📚 Documents / MANEX'],['liens','🔗 Liens & contacts'],
];
function renderNav(){
  const s=document.getElementById('side'); s.innerHTML='';
  s.appendChild(el('div','brand','🚁 PrepaFlyPy'));
  NAV.forEach(([k,label])=>{
    if(k==='SEP'){ s.appendChild(el('div','sep',label)); return; }
    const a=el('a',(current===k?'on':''),label); a.href='#';
    a.onclick=e=>{e.preventDefault(); current=k; currentDossierId=''; renderNav(); renderView();};
    s.appendChild(a);
  });
  const ss=el('div','savestate'); ss.id='saveState'; ss.textContent=''; s.appendChild(ss);
  s.appendChild(el('div','foot','v'+(meta&&meta.version||'?')+' · '+(dronesDB?dronesDB.all.length:0)+' drones DJI'));
}
function renderView(){
  const v=document.getElementById('view'); v.innerHTML='';
  if(currentDossierId){ return viewDossier(v); }
  ({exploitant:viewExploitant,pilotes:viewPilotes,dossiers:viewDossiers,
    checklist:viewChecklistRef,docs:viewDocs,liens:viewLiens}[current]||viewExploitant)(v);
}

/* ---------- Exploitant ---------- */
function viewExploitant(v){
  v.appendChild(el('h1','page-h','Exploitant'));
  v.appendChild(el('p','page-sub','Renseigné une fois, repris dans chaque dossier et document.'));
  const e=store.exploitant;
  const {card:c,body:cb}=collCard('exp-id','Référentiel','Identité de l’exploitant','Alimente le ConOps, les Cerfa et les rapports.');
  const g=el('div','grid');
  g.append(field('Raison sociale',e,'raison'),field('Forme juridique',e,'forme'),
    field('SIRET',e,'siret'),field('N° exploitant UAS',e,'numUAS'),
    field('Responsable',e,'responsable'),field('Assureur RC',e,'assureur'),
    field('Adresse',e,'adresse'),field('N° police assurance',e,'police'),
    field('Code postal',e,'cp'),field('Ville',e,'ville'),
    field('Téléphone',e,'tel'),field('Courriel',e,'mail'));
  cb.appendChild(g); cb.appendChild(field('Notes',e,'notes',{type:'textarea',full:true}));
  v.appendChild(c);

  const {card:lc,body:lb}=collCard('exp-logo','Image de marque','Logo','Repris en en-tête du MANEX et des rapports. Stocké localement.',false);
  const bar=el('div','row-actions');
  const imp=el('button','btn primary','⬆ Importer un logo (PNG/JPG)');
  imp.onclick=()=>{const i=document.createElement('input');i.type='file';i.accept='image/*';i.onchange=()=>importLogo(i.files[0]);i.click();};
  bar.appendChild(imp);
  if(store.logo){const rm=el('button','btn danger','Retirer');rm.onclick=()=>{store.logo='';scheduleSave();renderView();};bar.appendChild(rm);}
  lb.appendChild(bar);
  if(store.logo){const img=document.createElement('img');img.src=store.logo;img.style.cssText='max-height:80px;border:1px solid var(--bord);border-radius:8px;padding:6px;background:#fff';lb.appendChild(img);}
  else lb.appendChild(el('div','note','Aucun logo importé.'));
  v.appendChild(lc);
}
function importLogo(file){
  if(!file)return; if(file.size>2097152){alert('Logo trop lourd (max 2 Mo).');return;}
  const r=new FileReader(); r.onload=()=>{store.logo=r.result;scheduleSave();renderView();}; r.readAsDataURL(file);
}

/* ---------- Télépilotes (accordéon) ---------- */
function viewPilotes(v){
  v.appendChild(el('h1','page-h','Télépilotes'));
  v.appendChild(el('p','page-sub','Cliquez un nom pour dérouler sa fiche. Le référent alimente les formulaires.'));
  const add=el('button','btn primary','+ Ajouter un télépilote');
  add.onclick=()=>{store.pilotes.push({id:'p'+Math.random().toString(36).slice(2,10),prenom:'',nom:'',tel:'',mail:'',numTele:'',brevets:'',mentions:[],habilitations:[],notes:''});scheduleSave();renderView();};
  v.appendChild(add); v.appendChild(el('div',null,'')).style.height='12px';
  if(!store.pilotes.length){ v.appendChild(el('div','note','Aucun télépilote. Ajoutez-en un.')); return; }
  store.pilotes.forEach(p=>{
    if(pilotOpen[p.id]===undefined)pilotOpen[p.id]=false;
    const open=pilotOpen[p.id];
    const acc=el('div','acc'+(open?' open':''));
    const head=el('div','acc-head'); head.appendChild(el('span','chev','▶'));
    const nm=el('div','nm',((p.prenom||'')+' '+(p.nom||'')).trim()||'(sans nom)'); head.appendChild(nm);
    if(store.referent===p.id) head.appendChild(badge('b-green','Référent'));
    const body=el('div','acc-body'); body.hidden=!open;
    head.onclick=()=>{const o=!body.hidden;body.hidden=o;acc.classList.toggle('open',!o);pilotOpen[p.id]=!o;};
    // corps
    const rowb=el('div','row-actions');
    const ref=el('button','btn sm'+(store.referent===p.id?' primary':''),store.referent===p.id?'Référent ✓':'Définir référent');
    ref.onclick=()=>{store.referent=p.id;scheduleSave();renderView();};
    const del=el('button','btn danger sm','Supprimer');
    del.onclick=()=>{if(!confirm('Supprimer ce télépilote ?'))return;store.pilotes=store.pilotes.filter(x=>x.id!==p.id);if(store.referent===p.id)store.referent='';scheduleSave();renderView();};
    rowb.append(ref,del); body.appendChild(rowb);
    const g=el('div','grid');
    g.append(field('Prénom',p,'prenom',{after:()=>{nm.textContent=((p.prenom||'')+' '+(p.nom||'')).trim()||'(sans nom)';}}),
      field('Nom',p,'nom',{after:()=>{nm.textContent=((p.prenom||'')+' '+(p.nom||'')).trim()||'(sans nom)';}}),
      field('Téléphone',p,'tel'),field('Courriel',p,'mail'),
      field('N° télépilote',p,'numTele'),field('Brevets / formations',p,'brevets'));
    body.appendChild(g);
    // mentions (cases à cocher)
    body.appendChild(el('div','note','Mentions / qualifications'));
    const chips=el('div','chips');
    MENTIONS.forEach(m=>{const on=p.mentions.includes(m);const b=el('button','chip'+(on?' on':''),m);
      b.onclick=()=>{if(p.mentions.includes(m))p.mentions=p.mentions.filter(x=>x!==m);else p.mentions.push(m);scheduleSave();renderView();};chips.appendChild(b);});
    body.appendChild(chips);
    // habilitations avec dates
    body.appendChild(el('div','note','Habilitations (avec date de validité)'));
    p.habilitations.forEach((h,i)=>{
      const row=el('div','row-actions');
      const it=el('input');it.value=h.t||'';it.placeholder='Intitulé (ex. NF C 18-510)';it.style.flex='1';
      it.oninput=()=>{h.t=it.value;scheduleSave();};
      const dt=el('input');dt.type='date';dt.value=h.d||'';dt.oninput=()=>{h.d=dt.value;scheduleSave();renderView();};
      const stt=habStatus(h.d); const bd=stt?badge('b-'+stt.cls,stt.txt):badge('b-grey','—');
      const rm=el('button','btn danger sm','−');rm.onclick=()=>{p.habilitations.splice(i,1);scheduleSave();renderView();};
      row.append(it,dt,bd,rm); body.appendChild(row);
    });
    const addH=el('button','btn sm','+ Habilitation');addH.onclick=()=>{p.habilitations.push({t:'',d:''});scheduleSave();renderView();};
    body.appendChild(addH);
    body.appendChild(field('Notes',p,'notes',{type:'textarea',full:true}));
    acc.append(head,body); v.appendChild(acc);
  });
}
function habStatus(d){ if(!d)return null; const t=new Date();t.setHours(0,0,0,0); const dt=new Date(d+'T00:00:00'); if(isNaN(dt))return null;
  const days=Math.round((dt-t)/86400000); if(days<0)return{cls:'red',txt:'Périmé'}; if(days<=60)return{cls:'orange',txt:'À renouveler ('+days+' j)'}; return{cls:'green',txt:'Valide'};}

/* ---------- Dossiers (liste) ---------- */
function viewDossiers(v){
  v.appendChild(el('h1','page-h','Dossiers de vol'));
  v.appendChild(el('p','page-sub','Une mission = un dossier (appareil, régime, analyse, check-list, journal, PDF).'));
  const add=el('button','btn primary','+ Nouveau dossier');
  add.onclick=()=>{const d=emptyDossier();d.titre='Nouvelle mission';d.date=new Date().toISOString().slice(0,10);store.dossiers.push(d);store.currentId=d.id;currentDossierId=d.id;dossierTab='mission';scheduleSave();renderView();};
  v.appendChild(add); v.appendChild(el('div',null,'')).style.height='12px';
  if(!store.dossiers.length){ v.appendChild(el('div','note','Aucun dossier.')); return; }
  store.dossiers.forEach(d=>{
    const c=card(null,null,null); c.style.cursor='pointer';
    c.onclick=()=>{currentDossierId=d.id;store.currentId=d.id;dossierTab='mission';renderView();};
    const h=el('div',null); h.style.cssText='display:flex;justify-content:space-between;align-items:center;gap:10px';
    const left=el('div'); left.appendChild(el('h2',null,d.titre||'(sans titre)'));
    left.appendChild(el('div','note',[d.lieu||d.siteVille,d.date].filter(Boolean).join(' · ')||'—'));
    h.appendChild(left);
    if(d.regime) h.appendChild(badge('b-blue',(({open:'OPEN',sts:'STS',pdra:'PDRA',sora:'SORA'})[d.regime])||d.regime));
    c.appendChild(h); v.appendChild(c);
  });
}
function emptyDossier(){return {id:'d'+Math.random().toString(36).slice(2,10),titre:'',date:'',lieu:'',notes:'',client:'',
  dateDebut:'',dateFin:'',hauteurMax:'',classeC:'',typeVol:'',environnement:'',distanceTiers:'',
  siteAdresse:'',siteCp:'',siteVille:'',lat:'',lon:'',icao:'',meteo:{},regime:'',sousCategorie:'',pdra:'',
  appareil:{key:'',marque:'',modele:'',masse:'',serie:''},
  grc:{dim:'',vit:'',densite:'',mini:false,m1a:'none',m1b:'none',m1c:'none',m2:'none'},
  arc:{atypical:'',fl600:'',airport:'',airportClass:'',above500:'',adsb:'',eac:'',urban:'',residual:'',reduceJust:'',tacJust:''},
  prevol:{},journal:[],forms:{regime:'',expType:'morale',derogType:'',aotGestionnaire:'',aotObjet:''}};}
function curDossier(){ return store.dossiers.find(d=>d.id===currentDossierId)||null; }

/* ---------- Dossier (détail à onglets) ---------- */
function viewDossier(v){
  const D=curDossier(); if(!D){currentDossierId='';return renderView();}
  const top=el('div',null); top.style.cssText='display:flex;justify-content:space-between;align-items:center';
  const back=el('button','btn sm','← Dossiers'); back.onclick=()=>{currentDossierId='';renderView();};
  top.appendChild(back);
  const del=el('button','btn danger sm','Supprimer ce dossier');
  del.onclick=()=>{if(!confirm('Supprimer ce dossier ?'))return;store.dossiers=store.dossiers.filter(x=>x.id!==D.id);currentDossierId='';scheduleSave();renderView();};
  top.appendChild(del); v.appendChild(top);
  v.appendChild(el('h1','page-h',D.titre||'Mission'));
  const tabs=el('div','tabs');
  const TABS=[['mission','Mission & site'],['regime','Régime'],['conformite','Conformité'],['sora','SORA'],
    ['prevol','Check-list'],['journal','Journal'],['docs','Documents']];
  TABS.forEach(([k,label])=>{const b=el('button','tab'+(dossierTab===k?' on':''),label);b.onclick=()=>{dossierTab=k;renderView();};tabs.appendChild(b);});
  v.appendChild(tabs);
  ({mission:tabMission,regime:tabRegime,conformite:tabConformite,sora:tabSora,prevol:tabPrevol,journal:tabJournal,docs:tabDocs}[dossierTab])(v,D);
}

function tabMission(v,D){
  const c=card('Mission','Informations générales','Ces champs alimentent aussi les formulaires et la recommandation de régime.');
  const g=el('div','grid');
  g.append(field('Intitulé',D,'titre',{after:()=>{}}),field('Client',D,'client'),
    field('Date début',D,'dateDebut',{type:'date'}),field('Date fin',D,'dateFin',{type:'date'}),
    field('Hauteur max (m)',D,'hauteurMax',{type:'number'}),
    field('Type de vol',D,'typeVol',{type:'select',options:TYPEVOL}),
    field('Environnement',D,'environnement',{type:'select',options:ENVOPTS}),
    field('Distance aux tiers',D,'distanceTiers',{type:'select',options:DIST}));
  c.appendChild(g); c.appendChild(field('Notes de mission',D,'notes',{type:'textarea',full:true})); v.appendChild(c);

  const ac=card('Appareil','Aéronef utilisé','Choisissez un modèle DJI : dimension, vitesse et masse se remplissent seules.');
  const opts=[['','— Choisir un modèle DJI / saisie manuelle —']]; let lastCat='';
  dronesDB.all.forEach(d=>{opts.push([d.key,(d.cat!==lastCat?'【'+d.cat+'】 ':'')+'DJI '+d.modele]);lastCat=d.cat;});
  opts.push(['manuel','✎ Saisie manuelle (autre marque)']);
  ac.appendChild(field('Modèle',D.appareil,'key',{type:'select',options:opts,after:()=>applyModel(D)}));
  const isDji=!!dronesDB.all.find(d=>d.key===D.appareil.key);
  const g2=el('div','grid3');
  g2.append(field('Marque',D.appareil,'marque',{readonly:isDji}),field('Modèle',D.appareil,'modele',{readonly:isDji}),
    field('Classe C',D,'classeC',{type:'select',options:CLASSES}),
    field('Dimension (m)',D.grc,'dim',{readonly:isDji}),field('Vitesse max (m/s)',D.grc,'vit',{readonly:isDji}),
    field('Masse (g)',D.appareil,'masse',{readonly:isDji}),field('N° de série',D.appareil,'serie',{full:true}));
  ac.appendChild(g2); v.appendChild(ac);

  const mc=card('Site','Repérage & météo','Localisez par adresse ou sur la carte ; relevez la météo par code OACI.');
  const g3=el('div','grid');
  g3.append(field('Adresse',D,'siteAdresse'),field('Ville',D,'siteVille'),
    field('Code postal',D,'siteCp'),field('Code OACI (météo)',D,'icao'),
    field('Latitude',D,'lat'),field('Longitude',D,'lon'));
  mc.appendChild(g3);
  const bar=el('div','row-actions');
  const geo=el('button','btn','📍 Localiser l’adresse');geo.onclick=()=>geocodeSite(D);
  const map=el('button','btn','🗺 Carte / pointer');map.onclick=()=>openMap(D);
  const met=el('button','btn','🌦 Relever la météo');met.onclick=()=>releveMeteo(D);
  bar.append(geo,map,met); mc.appendChild(bar);
  if(D.meteo&&D.meteo.metar){mc.appendChild(el('div','note','METAR : '+D.meteo.metar));}
  v.appendChild(mc);
}
function applyModel(D){
  const d=dronesDB.all.find(x=>x.key===D.appareil.key);
  if(d){D.appareil.marque='DJI';D.appareil.modele=d.modele;D.appareil.masse=String(d.masse);
    D.grc.dim=String(d.dim);D.grc.vit=String(d.vit);D.grc.mini=(d.masse<250&&d.vit<=25);if(d.c)D.classeC=d.c;}
  else if(D.appareil.key!=='manuel'){D.appareil.marque='';D.appareil.modele='';D.appareil.masse='';D.grc.dim='';D.grc.vit='';}
  scheduleSave(); renderView();
}
async function geocodeSite(D){
  const q=[D.siteAdresse,D.siteCp,D.siteVille].filter(Boolean).join(' ');
  if(!q){alert('Renseignez l’adresse.');return;}
  try{const r=await apiGet('/api/geocode?q='+encodeURIComponent(q));D.lat=r.lat.toFixed(6);D.lon=r.lon.toFixed(6);if(!D.lieu)D.lieu=r.label;scheduleSave();renderView();}
  catch(e){alert('Localisation impossible : '+(e.message||e));}
}
async function releveMeteo(D){
  if(!D.icao){alert('Renseignez le code OACI (ex. LFRS).');return;}
  try{const r=await apiGet('/api/weather?icao='+encodeURIComponent(D.icao));D.meteo=r;scheduleSave();renderView();
    if(r.error)alert('Météo indisponible : '+r.error);}
  catch(e){alert('Météo indisponible : '+(e.message||e));}
}
function openMap(D){
  const ov=el('div','mapmodal');const box=el('div','mapbox');
  const head=el('div','pdfhead');head.appendChild(el('b',null,'Pointer le site de vol'));
  const close=el('button','btn sm primary','Fermer');head.appendChild(close);
  const md=el('div');md.id='map';box.append(head,md);ov.appendChild(box);document.body.appendChild(ov);
  const lat=parseFloat(D.lat)||46.7,lon=parseFloat(D.lon)||-1.4;
  const m=L.map('map').setView([lat,lon],D.lat?14:6);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'}).addTo(m);
  let marker=D.lat?L.marker([lat,lon]).addTo(m):null;
  m.on('click',e=>{if(marker)marker.setLatLng(e.latlng);else marker=L.marker(e.latlng).addTo(m);
    D.lat=e.latlng.lat.toFixed(6);D.lon=e.latlng.lng.toFixed(6);scheduleSave();});
  close.onclick=()=>{document.body.removeChild(ov);renderView();};
  setTimeout(()=>m.invalidateSize(),120);
}

function tabRegime(v,D){
  const c=card('Régime d’exploitation','Quel cadre pour cette mission ?','L’assistant propose le régime le plus adapté. Vous gardez le choix.');
  const box=el('div','result');box.innerHTML='<div><div class="big">…</div><div class="lbl">Recommandé</div></div>';
  c.appendChild(box); v.appendChild(c);
  apiSend('/api/regime','POST',D).then(rec=>{
    box.innerHTML='';
    const l=el('div');l.innerHTML='<div class="big">'+(rec.short||'—')+'</div><div class="lbl">Recommandé</div>';
    const r=el('div');r.style.cssText='border-left:1px solid #cfe0f6;padding-left:14px;flex:1';
    r.innerHTML='<b>'+rec.label+(rec.sub?' — '+rec.sub:'')+'</b><div class="note">'+rec.why+'</div>';
    box.append(l,r);
    if(rec.missing)c.appendChild(el('div','warn',rec.missing));
    const choose=el('div','row-actions');
    [['open','Ouverte'],['sts','STS'],['pdra','PDRA'],['sora','SORA']].forEach(([k,lab])=>{
      const b=el('button','btn'+(D.regime===k?' primary':''),lab+(rec.regime===k?' ✓ conseillé':''));
      b.onclick=()=>{D.regime=k;if(k==='open'&&rec.sub)D.sousCategorie=rec.sub;scheduleSave();renderView();};choose.appendChild(b);
    });
    c.appendChild(el('div','note','Régime retenu :'));c.appendChild(choose);
    if(D.regime==='open'){c.appendChild(field('Sous-catégorie',D,'sousCategorie',{type:'select',options:[['','—'],['A1','A1'],['A2','A2'],['A3','A3']]}));}
    if(D.regime==='pdra'){c.appendChild(field('PDRA visé',D,'pdra',{type:'select',options:[['','—'],['S01','S01'],['S02','S02'],['G01','G01'],['G02','G02'],['G03','G03']]}));}
  });
}
function tabConformite(v,D){
  if(D.regime==='sora'){ v.appendChild(card('SORA',null,'La conformité SORA se fait dans l’onglet SORA.')); return; }
  if(D.regime==='open'){
    const c=card('Catégorie ouverte','Contrôle de conformité','Vérifie la cohérence sous-catégorie / classe / conditions.');
    v.appendChild(c);
    apiSend('/api/regime/open','POST',D).then(res=>{
      c.appendChild(badge(res.ok?'b-green':'b-orange',res.ok?'Conforme':'Points à vérifier'));
      res.items.forEach(it=>{const r=el('div','ck');r.appendChild(el('span',null,it.ok?'✅':'⚠️'));r.appendChild(el('span',null,it.text));c.appendChild(r);});
    });
    return;
  }
  const lbl={sts:'STS',pdra:'PDRA'}[D.regime]||'—';
  const c=card('Catégorie spécifique — '+lbl,'Rappels','La conformité exacte se lit sur la fiche officielle du scénario retenu.');
  c.appendChild(el('div','note',D.regime==='sts'
    ? 'STS-01 : VLOS, drone C5, zone au sol contrôlée. STS-02 : BVLOS avec observateurs, drone C6, zone peu peuplée. Déclaration à la DGAC.'
    : 'PDRA : scénario de risque prédéfini (méthode SORA pré-instruite). Demande d’autorisation d’exploitation.'));
  v.appendChild(c);
}
function tabSora(v,D){
  const g=card('Risque au sol — GRC','Étapes 1-3','Dimension et vitesse viennent de l’appareil ; densité + atténuations donnent le GRC.');
  const gg=el('div','grid');
  gg.append(field('Dimension (m)',D.grc,'dim'),field('Vitesse (m/s)',D.grc,'vit'),
    field('Densité population',D.grc,'densite',{type:'select',options:DENSITE}),
    field('M1(A) refuge',D.grc,'m1a',{type:'select',options:[['none','Absent/Faible'],['low','Faible'],['med','Moyenne']]}),
    field('M1(B) restrictions',D.grc,'m1b',{type:'select',options:[['none','Absent'],['med','Moyenne'],['high','Haute']]}),
    field('M2 impact',D.grc,'m2',{type:'select',options:[['none','Absent/Faible'],['med','Moyenne'],['high','Haute']]}));
  g.appendChild(gg); v.appendChild(g);
  const a=card('Risque air — ARC','Étapes 4-6','Arbre de décision de l’espace aérien.');
  const ag=el('div','grid');
  ag.append(field('Espace atypique/ségrégué',D.arc,'atypical',{type:'select',options:YN}),
    field('> FL600',D.arc,'fl600',{type:'select',options:YN}),
    field('Proche aérodrome',D.arc,'airport',{type:'select',options:YN}),
    field('… en zone à trafic',D.arc,'airportClass',{type:'select',options:YN}),
    field('> 500 ft AGL',D.arc,'above500',{type:'select',options:YN}),
    field('Zone urbaine',D.arc,'urban',{type:'select',options:YN}),
    field('ARC final (si réduction)',D.arc,'residual',{type:'select',options:ARC_RES}));
  a.appendChild(ag); v.appendChild(a);
  const res=card('Résultat','SAIL & OSO',''); const out=el('div');res.appendChild(out);v.appendChild(res);
  const btn=el('button','btn primary','Calculer le SORA');btn.onclick=()=>runSora(D,out);res.insertBefore(btn,out);
  runSora(D,out);
}
async function runSora(D,out){
  const r=await apiSend('/api/sora','POST',{grc:D.grc,arc:D.arc}); out.innerHTML='';
  if(!r.valid){out.appendChild(el('div','warn','Renseignez dimension, vitesse et densité pour le calcul du GRC.'));}
  const box=el('div','result');
  box.innerHTML='<div><div class="big">'+(r.sail||'—')+'</div><div class="lbl">SAIL</div></div>'+
    '<div style="border-left:1px solid #cfe0f6;padding-left:14px;flex:1"><b>iGRC '+(r.igrc??'—')+' → GRC '+(r.grc??'—')+'</b>'+
    '<div class="note">ARC '+(r.arcInitial||'—').toUpperCase()+' → '+(r.arcResidual||'—').toUpperCase()+'</div></div>';
  out.appendChild(box);
  if(r.cumulConflict)out.appendChild(el('div','warn','M1(A) moyenne et M1(B) ne sont pas cumulables : vérifiez la justification.'));
  if(r.osoReq&&r.osoReq.length){
    const t=el('table');t.style.cssText='width:100%;border-collapse:collapse;margin-top:10px;font-size:12.5px';
    r.osoReq.forEach(o=>{const tr=el('tr');
      const td1=el('td',null,'OSO '+o.id);td1.style.cssText='padding:4px 6px;border-bottom:1px solid var(--bord);width:70px';
      const td2=el('td',null,o.t);td2.style.cssText='padding:4px 6px;border-bottom:1px solid var(--bord)';
      const td3=el('td');td3.style.cssText='padding:4px 6px;border-bottom:1px solid var(--bord);width:120px';
      const cls={'L':'b-yellow','M':'b-orange','H':'b-red','-':'b-grey'}[o.lvl];
      const txt={'L':'Faible','M':'Moyen','H':'Haut','-':'Non requis'}[o.lvl];
      td3.appendChild(badge(cls,txt));tr.append(td1,td2,td3);t.appendChild(tr);});
    out.appendChild(t);
  }
}
function tabPrevol(v,D){
  const c=card('Préparation','Check-list pré-vol','À cocher avant décollage. Repris dans le dossier PDF.');
  PREVOL.forEach(item=>{const r=el('label','ck');const cb=el('input');cb.type='checkbox';cb.checked=!!D.prevol[item];
    cb.onchange=()=>{D.prevol[item]=cb.checked;scheduleSave();};r.append(cb,el('span',null,item));c.appendChild(r);});
  v.appendChild(c);
}
function tabJournal(v,D){
  const c=card('Après-vol','Journal de vol','Une ligne par session : horaires, nombre de vols, incidents.');
  (D.journal||[]).forEach((s,i)=>{const row=el('div','row-actions');
    const dt=el('input');dt.type='date';dt.value=s.date||'';dt.oninput=()=>{s.date=dt.value;scheduleSave();};
    const h1=el('input');h1.type='time';h1.value=s.debut||'';h1.oninput=()=>{s.debut=h1.value;scheduleSave();};
    const h2=el('input');h2.type='time';h2.value=s.fin||'';h2.oninput=()=>{s.fin=h2.value;scheduleSave();};
    const nb=el('input');nb.type='number';nb.placeholder='vols';nb.style.width='70px';nb.value=s.nb||'';nb.oninput=()=>{s.nb=nb.value;scheduleSave();};
    const inc=el('input');inc.placeholder='Incidents';inc.style.flex='1';inc.value=s.incidents||'';inc.oninput=()=>{s.incidents=inc.value;scheduleSave();};
    const rm=el('button','btn danger sm','−');rm.onclick=()=>{D.journal.splice(i,1);scheduleSave();renderView();};
    row.append(dt,h1,h2,nb,inc,rm);c.appendChild(row);});
  const add=el('button','btn sm','+ Session');add.onclick=()=>{D.journal.push({date:new Date().toISOString().slice(0,10),debut:'',fin:'',nb:'',incidents:''});scheduleSave();renderView();};
  c.appendChild(add); v.appendChild(c);
}
function tabDocs(v,D){
  const c=card('Documents','Générer les PDF','Dossier de vol, rapport client, et formulaires pré-remplis.');
  const bar=el('div','row-actions');
  bar.appendChild(pdfBtn('📄 Dossier de vol','/api/report/dossier',{dossierId:D.id}));
  bar.appendChild(pdfBtn('🧾 Rapport client','/api/report/rapport',{dossierId:D.id}));
  c.appendChild(bar);
  const bar2=el('div','row-actions');
  bar2.appendChild(pdfBtn('Cerfa 15476','/api/form/cerfa',{dossierId:D.id}));
  bar2.appendChild(pdfBtn('Dérogation','/api/form/derog',{dossierId:D.id}));
  bar2.appendChild(pdfBtn('Lettre AOT','/api/form/aot',{dossierId:D.id}));
  c.appendChild(el('div','note','Formulaires officiels :'));c.appendChild(bar2);
  v.appendChild(c);
}
function pdfBtn(label,path,body){
  const b=el('button','btn primary',label);
  b.onclick=async()=>{try{const blob=await apiPdf(path,body);openPdf(blob,label);}catch(e){alert('Génération impossible : '+(e.message||e));}};
  return b;
}
function openPdf(blob,title){
  const url=URL.createObjectURL(blob);
  const ov=el('div','pdfmodal');const box=el('div','pdfbox');
  const head=el('div','pdfhead');head.appendChild(el('b',null,title));
  const dl=el('a','btn sm','Enregistrer');dl.href=url;dl.download=(title.replace(/[^\w]+/g,'_')||'document')+'.pdf';head.appendChild(dl);
  const close=el('button','btn sm primary','Fermer');head.appendChild(close);
  const fr=el('iframe','pdfframe');fr.src=url;box.append(head,fr);ov.appendChild(box);document.body.appendChild(ov);
  close.onclick=()=>{URL.revokeObjectURL(url);document.body.removeChild(ov);};
}

/* ---------- Check-list de référence (consultable) ---------- */
function viewChecklistRef(v){
  v.appendChild(el('h1','page-h','Check-list pré-vol (référence)'));
  v.appendChild(el('p','page-sub','Consultable sans monter de dossier — utile en préparation ou en contrôle.'));
  const c=card('Terrain','Points à vérifier avant décollage','');
  PREVOL.forEach(i=>{const r=el('div','ck');r.append(el('span',null,'☐'),el('span',null,i));c.appendChild(r);});
  v.appendChild(c);
}

/* ---------- Documents / MANEX / sauvegarde ---------- */
function viewDocs(v){
  v.appendChild(el('h1','page-h','Documents / MANEX'));
  v.appendChild(el('p','page-sub','Importez vos justificatifs (MANEX, assurance, attestations) pour les consulter et les présenter en contrôle.'));
  const {card:c,body:cb}=collCard('docs-justif','Justificatifs','Vos documents','',true);
  const imp=el('button','btn primary','⬆ Importer un document');
  imp.onclick=()=>{const i=document.createElement('input');i.type='file';i.onchange=()=>uploadDoc(i.files[0]);i.click();};
  cb.appendChild(imp); const list=el('div');list.id='docslist';cb.appendChild(list);v.appendChild(c);loadDocs();

  const {card:mc,body:mb}=collCard('docs-manex','MANEX','Générer une trame de MANEX','Manuel pré-rempli depuis votre référentiel, plan A-E. À relire et adapter.',false);
  mb.appendChild(pdfBtn('📘 Générer la trame MANEX','/api/report/manex',{}));v.appendChild(mc);

  const {card:sb,body:sd}=collCard('docs-save','Sécurité','Sauvegarde des données','Exportez / réimportez toutes vos données (JSON).',false);
  const bar=el('div','row-actions');
  const ex=el('button','btn primary','💾 Exporter mes données');ex.onclick=()=>{window.location='/api/backup';};
  const im=el('button','btn','📥 Importer des données');im.onclick=()=>{const i=document.createElement('input');i.type='file';i.accept='.json';i.onchange=()=>restoreBackup(i.files[0]);i.click();};
  bar.append(ex,im);sd.appendChild(bar);sd.appendChild(el('div','note','L’import remplace les données actuelles.'));v.appendChild(sb);
}
async function loadDocs(){
  const list=document.getElementById('docslist');if(!list)return;list.innerHTML='';
  let docs=[];try{docs=await apiGet('/api/docs');}catch(e){}
  if(!docs.length){list.appendChild(el('div','note','Aucun document importé.'));return;}
  docs.forEach(d=>{const row=el('div','row-actions');
    const nm=el('div',null,d.name);nm.style.cssText='flex:1;font-size:13.5px';
    row.appendChild(nm);row.appendChild(badge('b-grey',fmtSize(d.size)));
    const lire=el('button','btn sm primary','Lire');lire.onclick=()=>window.open('/api/docs/'+encodeURIComponent(d.name),'_blank');
    const exp=el('a','btn sm');exp.textContent='Exporter';exp.href='/api/docs/'+encodeURIComponent(d.name);exp.download=d.name;
    const del=el('button','btn danger sm','🗑');del.onclick=async()=>{if(!confirm('Supprimer '+d.name+' ?'))return;await fetch('/api/docs/'+encodeURIComponent(d.name),{method:'DELETE'});loadDocs();};
    row.append(lire,exp,del);list.appendChild(row);});
}
function fmtSize(n){if(n<1024)return n+' o';if(n<1048576)return(n/1024).toFixed(0)+' Ko';return(n/1048576).toFixed(1)+' Mo';}
async function uploadDoc(file){if(!file)return;const fd=new FormData();fd.append('file',file);
  try{await fetch('/api/docs',{method:'POST',body:fd});loadDocs();}catch(e){alert('Import impossible : '+e);}}
async function restoreBackup(file){if(!file)return;const txt=await file.text();let data;try{data=JSON.parse(txt);}catch(e){alert('JSON invalide.');return;}
  if(!confirm('Remplacer les données actuelles ?'))return;
  await apiSend('/api/backup','POST',data);store=await apiGet('/api/store');current='exploitant';renderNav();renderView();}

/* ---------- Liens ---------- */
function viewLiens(v){
  v.appendChild(el('h1','page-h','Liens & contacts'));
  v.appendChild(el('p','page-sub','Ressources officielles, marchés publics et code source.'));
  v.appendChild(linkCard('l-utiles','Ressources','Liens utiles','',LINKS,true));
  v.appendChild(linkCard('l-marches','Business','Marchés publics & appels d’offres','',MARCHES,false));
  const src=[
    {ic:'💻',t:'Code source (GitHub)',u:(meta&&meta.repo)||'https://github.com/paul-jnn/PrepaFlyPy',d:'Dépôt public'},
    {ic:'📦',t:'Versions',u:(meta&&meta.releases)||'https://github.com/paul-jnn/PrepaFlyPy/releases',d:'Téléchargements'},
    {ic:'📖',t:'Dossier technique',u:((meta&&meta.repo)||'https://github.com/paul-jnn/PrepaFlyPy')+'/blob/main/docs/DOSSIER_TECHNIQUE.md',d:'Documentation'},
  ];
  v.appendChild(linkCard('l-source','Application','Code source & documentation','Application libre et ouverte.',src,false));
}
function linkCard(id,kick,title,desc,items,defOpen){
  const {card:c,body:b}=collCard(id,kick,title,desc,defOpen);
  const list=el('div','linklist');
  items.forEach(l=>{const a=el('a');a.href=l.u;a.target='_blank';
    a.innerHTML='<span class="ic">'+l.ic+'</span><span>'+l.t+'<small>'+l.d+'</small></span>';list.appendChild(a);});
  b.appendChild(list);return c;
}

/* ---------- Démarrage ---------- */
boot();
