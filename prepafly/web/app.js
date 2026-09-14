/* =============================================================================
   PrepaFlyPy — logique de l'interface (client de l'API FastAPI).
   Toute action passe par une route /api/... ; ici on construit les écrans et on
   affiche les réponses. Pas de logique métier (SORA, régimes, PDF) côté client :
   elle vit dans prepafly.core, appelée via l'API. Voir prepafly/server.py.
   Interface bilingue FR/EN : tout libellé visible passe par t('clé') (voir i18n.py).
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
try{ lang=localStorage.getItem('prepafly_lang')||'fr'; }catch(e){}

/* Traduction : renvoie la chaîne de la langue courante, avec substitution {var}. */
function t(k,vars){ let s=(strings&&strings[k])||k; if(vars){for(const kk in vars)s=s.split('{'+kk+'}').join(vars[kk]);} return s; }
async function loadStrings(){ try{ strings=await apiGet('/api/i18n/'+lang); }catch(e){ strings={}; } }
async function setLang(code){ if(code===lang)return; lang=code; try{ localStorage.setItem('prepafly_lang',code); }catch(e){}
  await loadStrings(); renderNav(); renderView(); }

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
  // Exemple grisé (placeholder) : guide l'utilisateur, disparaît dès la saisie.
  if(opts.ph && opts.type!=='select' && opts.type!=='date') inp.placeholder=opts.ph;
  if(opts.readonly){ inp.readOnly=true; if(opts.type==='select') inp.disabled=true; }
  inp.value=(obj[key]!=null?obj[key]:'');
  const ev=(opts.type==='select')?'change':'input';
  inp.addEventListener(ev,()=>{ obj[key]=inp.value; scheduleSave(); if(opts.after)opts.after(inp.value); });
  f.appendChild(inp); return f;
}
function badge(cls,txt){return el('span','badge '+cls,txt);}

/* ---------- Sauvegarde ---------- */
function setSave(msg){ const e=document.getElementById('saveState'); if(e)e.textContent=msg; }
async function persist(){ try{ await apiSend('/api/store','PUT',store); setSave(t('save_saved')); }catch(e){ setSave(t('save_err')); } }
function scheduleSave(){ setSave(t('save_modif')); clearTimeout(saveTimer); saveTimer=setTimeout(persist,450); }

/* ---------- Options de listes déroulantes (traduites à chaque rendu) ---------- */
const CLASSES=[['','—'],['C0','C0'],['C1','C1'],['C2','C2'],['C3','C3'],['C4','C4'],['C5','C5'],['C6','C6']];
function optTypevol(){ return [['','—'],['VLOS',t('tv_vlos')],['BVLOS',t('tv_bvlos')]]; }
function optEnv(){ return [['','—'],['hors',t('env_hors')],['peuple',t('env_peuple')],['rassemblement',t('env_rass')]]; }
function optDist(){ return [['','—'],['150m',t('dist_150')],['30m',t('dist_30')],['5m',t('dist_5')],['0',t('dist_0')]]; }
function optDensite(){ return [['','—'],['ctrl',t('den_ctrl')],['d5',t('den_d5')],['d50',t('den_d50')],
  ['d500',t('den_d500')],['d5000',t('den_d5000')],['d50000',t('den_d50000')],['dsup',t('den_dsup')]]; }
function optYN(){ return [['','—'],['yes',t('yes')],['no',t('no')]]; }
function optArcRes(){ return [['',t('arcres_default')],['a','a'],['b','b'],['c','c'],['d','d']]; }
function optMitA(){ return [['none',t('mit_absent_low')],['low',t('mit_low')],['med',t('mit_med')]]; }
function optMitB(){ return [['none',t('mit_absent')],['med',t('mit_med')],['high',t('mit_high')]]; }
function optMit2(){ return [['none',t('mit_absent_low')],['med',t('mit_med')],['high',t('mit_high')]]; }
function optSouscat(){ return [['','—'],['A1','A1'],['A2','A2'],['A3','A3']]; }
function optPdra(){ return [['','—'],['S01','S01'],['S02','S02'],['G01','G01'],['G02','G02'],['G03','G03']]; }

const MENTIONS=['A1','A2','A3','STS-01','STS-02','CATS'];
/* Check-list pré-vol : ces libellés servent AUSSI de clés de stockage et sont
   repris tels quels dans le PDF — on les garde donc en français, non traduits. */
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
  await loadStrings();
  const st=await apiGet('/api/pin/status');
  const lt=document.getElementById('lockText'), pin=document.getElementById('pin'),
        pin2=document.getElementById('pin2'), btn=document.getElementById('lockBtn'), err=document.getElementById('lockErr');
  pin.style.display='block'; btn.style.display='block'; btn.textContent=t('pin_validate');
  pin2.placeholder=t('pin_confirm_ph');
  if(!st.set){
    lt.textContent=t('pin_choose');
    pin2.style.display='block';
    btn.onclick=async()=>{ err.textContent='';
      if(pin.value.length<4){err.textContent=t('pin_min');return;}
      if(pin.value!==pin2.value){err.textContent=t('pin_mismatch');return;}
      try{ await apiSend('/api/pin/set','POST',{pin:pin.value}); unlock(); }catch(e){ err.textContent=String(e.message||e); }
    };
  } else {
    lt.textContent=t('pin_enter');
    btn.onclick=async()=>{ err.textContent='';
      const r=await apiSend('/api/pin/verify','POST',{pin:pin.value});
      if(r.ok) unlock(); else err.textContent=t('pin_wrong');
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
  renderNav(); renderView(); checkUpdate(); firstRun();
}
/* Premier lancement : propose d'ajouter les raccourcis (Bureau + menu Démarrer). */
async function firstRun(){
  let f; try{ f=await apiGet('/api/firstrun'); }catch(e){ return; }
  if(!f.first || !f.can_shortcuts) return;
  const ov=el('div','pdfmodal');
  const box=el('div','card'); box.style.cssText='max-width:440px;text-align:center;padding:26px';
  box.innerHTML='<div style="font-size:40px">🚁</div>';
  box.appendChild(el('h2',null,t('setup_title')));
  box.appendChild(el('div','desc',t('setup_msg')));
  const row=el('div','row-actions'); row.style.justifyContent='center';
  const yes=el('button','btn primary',t('setup_yes'));
  const no=el('button','btn',t('setup_no'));
  row.append(yes,no); box.appendChild(row); ov.appendChild(box); document.body.appendChild(ov);
  const close=()=>{ try{document.body.removeChild(ov);}catch(e){} };
  no.onclick=async()=>{ try{ await apiSend('/api/setup','POST',{shortcuts:false}); }catch(e){} close(); };
  yes.onclick=async()=>{ yes.disabled=true; yes.textContent='…';
    try{ const r=await apiSend('/api/setup','POST',{shortcuts:true}); close(); alert(t('setup_done',{where:(r.created||[]).join(', ')})); }
    catch(e){ close(); alert(t('setup_fail',{e:(e.message||e)})); } };
}
async function checkUpdate(){
  try{ const u=await apiGet('/api/update'); const bar=document.getElementById('updbar');
    if(!u.update_available) return;
    bar.className='updbar'; bar.innerHTML='';
    bar.appendChild(el('span',null,t('update_available',{v:u.latest})));
    if(u.can_auto){
      const btn=el('button','btn sm primary',t('update_install'));
      btn.onclick=()=>applyUpdate(btn,u.url);
      bar.appendChild(btn);
    } else {
      const a=el('a','btn sm primary',t('update_download')); a.href=u.url; a.target='_blank'; bar.appendChild(a);
    }
  }catch(e){}
}
async function applyUpdate(btn,url){
  btn.disabled=true; btn.textContent='…';
  try{
    await apiSend('/api/update/apply','POST',{});
    btn.textContent='…';
  }catch(e){
    btn.disabled=false; btn.textContent=t('update_install');
    if(url) window.open(url,'_blank');
    alert(t('update_fail',{e:(e.message||e)}));
  }
}

/* ---------- Navigation ---------- */
const NAV=[
  ['exploitant','👤','nav_exploitant'],
  ['pilotes','🧑‍✈️','nav_pilotes'],
  ['dossiers','📁','nav_dossiers'],
  ['SEP','','section_consultation'],
  ['carte','🗺','nav_carte'],
  ['checklist','✅','nav_checklist'],
  ['docs','📚','nav_docs'],
  ['liens','🔗','nav_links'],
];
function renderNav(){
  const s=document.getElementById('side'); s.innerHTML='';
  const brand=el('div','brand');
  brand.innerHTML='<img src="/static/logo.png" alt="" style="width:24px;height:24px;border-radius:6px"> PrepaFlyPy';
  s.appendChild(brand);
  const lg=el('div'); lg.style.cssText='display:flex;gap:6px;padding:2px 20px 10px';
  [['fr','FR'],['en','EN']].forEach(([code,lab])=>{ const b=el('button','langbtn'+(lang===code?' on':''),lab); b.onclick=()=>setLang(code); lg.appendChild(b); });
  s.appendChild(lg);
  NAV.forEach(([k,ic,key])=>{
    if(k==='SEP'){ s.appendChild(el('div','sep',t(key))); return; }
    const a=el('a',(current===k?'on':''),ic+' '+t(key)); a.href='#';
    a.onclick=e=>{e.preventDefault(); current=k; currentDossierId=''; renderNav(); renderView();};
    s.appendChild(a);
  });
  const ss=el('div','savestate'); ss.id='saveState'; ss.textContent=''; s.appendChild(ss);
  s.appendChild(el('div','foot','v'+(meta&&meta.version||'?')));
}
function renderView(){
  const v=document.getElementById('view'); v.innerHTML='';
  if(currentDossierId){ return viewDossier(v); }
  ({exploitant:viewExploitant,pilotes:viewPilotes,dossiers:viewDossiers,carte:viewCarte,
    checklist:viewChecklistRef,docs:viewDocs,liens:viewLiens}[current]||viewExploitant)(v);
}

/* ---------- Exploitant ---------- */
function viewExploitant(v){
  v.appendChild(el('h1','page-h',t('nav_exploitant')));
  v.appendChild(el('p','page-sub',t('exploitant_sub')));
  const e=store.exploitant;
  const {card:c,body:cb}=collCard('exp-id',t('exp_ref_kick'),t('exp_ref_title'),t('exp_ref_desc'));
  const g=el('div','grid');
  g.append(field(t('f_raison'),e,'raison',{ph:t('ph_raison')}),field(t('f_forme'),e,'forme',{ph:t('ph_forme')}),
    field(t('f_siret'),e,'siret',{ph:t('ph_siret')}),field(t('f_numuas'),e,'numUAS',{ph:t('ph_numuas')}),
    field(t('f_resp'),e,'responsable',{ph:t('ph_resp')}),field(t('f_assureur'),e,'assureur',{ph:t('ph_assureur')}),
    field(t('f_adresse'),e,'adresse',{ph:t('ph_adresse')}),field(t('f_police'),e,'police',{ph:t('ph_police')}),
    field(t('f_cp'),e,'cp',{ph:t('ph_cp')}),field(t('f_ville'),e,'ville',{ph:t('ph_ville')}),
    field(t('f_tel'),e,'tel',{ph:t('ph_tel')}),field(t('f_mail'),e,'mail',{ph:t('ph_mail')}));
  cb.appendChild(g); cb.appendChild(field(t('f_notes'),e,'notes',{type:'textarea',full:true,ph:t('ph_notes_exp')}));
  v.appendChild(c);

  const {card:lc,body:lb}=collCard('exp-logo',t('exp_logo_kick'),t('exp_logo_title'),t('exp_logo_desc'),false);
  const bar=el('div','row-actions');
  const imp=el('button','btn primary',t('btn_import_logo'));
  imp.onclick=()=>{const i=document.createElement('input');i.type='file';i.accept='image/*';i.onchange=()=>importLogo(i.files[0]);i.click();};
  bar.appendChild(imp);
  if(store.logo){const rm=el('button','btn danger',t('remove'));rm.onclick=()=>{store.logo='';scheduleSave();renderView();};bar.appendChild(rm);}
  lb.appendChild(bar);
  if(store.logo){const img=document.createElement('img');img.src=store.logo;img.style.cssText='max-height:80px;border:1px solid var(--bord);border-radius:8px;padding:6px;background:#fff';lb.appendChild(img);}
  else lb.appendChild(el('div','note',t('logo_none')));
  v.appendChild(lc);
}
function importLogo(file){
  if(!file)return; if(file.size>2097152){alert(t('logo_too_big'));return;}
  const r=new FileReader(); r.onload=()=>{store.logo=r.result;scheduleSave();renderView();}; r.readAsDataURL(file);
}

/* ---------- Télépilotes (accordéon) ---------- */
function viewPilotes(v){
  v.appendChild(el('h1','page-h',t('nav_pilotes')));
  v.appendChild(el('p','page-sub',t('pilotes_sub')));
  const add=el('button','btn primary',t('btn_add_pilot'));
  add.onclick=()=>{store.pilotes.push({id:'p'+Math.random().toString(36).slice(2,10),prenom:'',nom:'',tel:'',mail:'',numTele:'',brevets:'',mentions:[],habilitations:[],notes:''});scheduleSave();renderView();};
  v.appendChild(add); v.appendChild(el('div',null,'')).style.height='12px';
  if(!store.pilotes.length){ v.appendChild(el('div','note',t('pilots_none'))); return; }
  store.pilotes.forEach(p=>{
    if(pilotOpen[p.id]===undefined)pilotOpen[p.id]=false;
    const open=pilotOpen[p.id];
    const acc=el('div','acc'+(open?' open':''));
    const head=el('div','acc-head'); head.appendChild(el('span','chev','▶'));
    const nm=el('div','nm',((p.prenom||'')+' '+(p.nom||'')).trim()||t('pilot_noname')); head.appendChild(nm);
    if(store.referent===p.id) head.appendChild(badge('b-green',t('badge_ref')));
    const body=el('div','acc-body'); body.hidden=!open;
    head.onclick=()=>{const o=!body.hidden;body.hidden=o;acc.classList.toggle('open',!o);pilotOpen[p.id]=!o;};
    const rowb=el('div','row-actions');
    const ref=el('button','btn sm'+(store.referent===p.id?' primary':''),store.referent===p.id?t('btn_ref_isset'):t('btn_ref_set'));
    ref.onclick=()=>{store.referent=p.id;scheduleSave();renderView();};
    const del=el('button','btn danger sm',t('btn_delete'));
    del.onclick=()=>{if(!confirm(t('confirm_del_pilot')))return;store.pilotes=store.pilotes.filter(x=>x.id!==p.id);if(store.referent===p.id)store.referent='';scheduleSave();renderView();};
    rowb.append(ref,del); body.appendChild(rowb);
    const g=el('div','grid');
    const upd=()=>{nm.textContent=((p.prenom||'')+' '+(p.nom||'')).trim()||t('pilot_noname');};
    g.append(field(t('f_prenom'),p,'prenom',{after:upd,ph:t('ph_prenom')}),field(t('f_nom'),p,'nom',{after:upd,ph:t('ph_nom')}),
      field(t('f_tel'),p,'tel',{ph:t('ph_tel')}),field(t('f_mail'),p,'mail',{ph:t('ph_mail')}),
      field(t('f_numtele'),p,'numTele',{ph:t('ph_numtele')}),field(t('f_brevets'),p,'brevets',{ph:t('ph_brevets')}));
    body.appendChild(g);
    body.appendChild(el('div','note',t('pilot_mentions')));
    const chips=el('div','chips');
    MENTIONS.forEach(m=>{const on=p.mentions.includes(m);const b=el('button','chip'+(on?' on':''),m);
      b.onclick=()=>{if(p.mentions.includes(m))p.mentions=p.mentions.filter(x=>x!==m);else p.mentions.push(m);scheduleSave();renderView();};chips.appendChild(b);});
    body.appendChild(chips);
    body.appendChild(el('div','note',t('pilot_habil')));
    p.habilitations.forEach((h,i)=>{
      const row=el('div','row-actions');
      const it=el('input');it.value=h.t||'';it.placeholder=t('habil_ph');it.style.flex='1';
      it.oninput=()=>{h.t=it.value;scheduleSave();};
      const dt=el('input');dt.type='date';dt.value=h.d||'';dt.oninput=()=>{h.d=dt.value;scheduleSave();renderView();};
      const stt=habStatus(h.d); const bd=stt?badge('b-'+stt.cls,stt.txt):badge('b-grey','—');
      const rm=el('button','btn danger sm','−');rm.onclick=()=>{p.habilitations.splice(i,1);scheduleSave();renderView();};
      row.append(it,dt,bd,rm); body.appendChild(row);
    });
    const addH=el('button','btn sm',t('btn_add_habil'));addH.onclick=()=>{p.habilitations.push({t:'',d:''});scheduleSave();renderView();};
    body.appendChild(addH);
    body.appendChild(field(t('f_notes'),p,'notes',{type:'textarea',full:true,ph:t('ph_notes_pilote')}));
    acc.append(head,body); v.appendChild(acc);
  });
}
function habStatus(d){ if(!d)return null; const now=new Date();now.setHours(0,0,0,0); const dt=new Date(d+'T00:00:00'); if(isNaN(dt))return null;
  const days=Math.round((dt-now)/86400000); if(days<0)return{cls:'red',txt:t('hab_perime')}; if(days<=60)return{cls:'orange',txt:t('hab_renew',{d:days})}; return{cls:'green',txt:t('hab_valid')};}

/* ---------- Dossiers (liste) ---------- */
function viewDossiers(v){
  v.appendChild(el('h1','page-h',t('nav_dossiers')));
  v.appendChild(el('p','page-sub',t('dossiers_sub')));
  const add=el('button','btn primary',t('btn_new_dossier'));
  add.onclick=()=>{const d=emptyDossier();d.titre=t('dossier_new_title');d.date=new Date().toISOString().slice(0,10);store.dossiers.push(d);store.currentId=d.id;currentDossierId=d.id;dossierTab='mission';scheduleSave();renderView();};
  v.appendChild(add); v.appendChild(el('div',null,'')).style.height='12px';
  if(!store.dossiers.length){ v.appendChild(el('div','note',t('dossiers_none'))); return; }
  store.dossiers.forEach(d=>{
    const c=card(null,null,null); c.style.cursor='pointer';
    c.onclick=()=>{currentDossierId=d.id;store.currentId=d.id;dossierTab='mission';renderView();};
    const h=el('div',null); h.style.cssText='display:flex;justify-content:space-between;align-items:center;gap:10px';
    const left=el('div'); left.appendChild(el('h2',null,d.titre||t('dossier_notitle')));
    left.appendChild(el('div','note',[d.lieu||d.siteVille,d.date].filter(Boolean).join(' · ')||'—'));
    h.appendChild(left);
    if(d.regime) h.appendChild(badge('b-blue',(({open:'OPEN',sts:'STS',pdra:'PDRA',sora:'SORA'})[d.regime])||d.regime));
    c.appendChild(h); v.appendChild(c);
  });
}
function emptyDossier(){return {id:'d'+Math.random().toString(36).slice(2,10),titre:'',date:'',lieu:'',notes:'',client:'',
  dateDebut:'',dateFin:'',hauteurMax:'',classeC:'',typeVol:'',environnement:'',distanceTiers:'',
  siteAdresse:'',siteCp:'',siteVille:'',lat:'',lon:'',icao:'',meteo:{},regime:'',sousCategorie:'',pdra:'',
  appareil:{key:'',marque:'',modele:'',masse:'',serie:'',equipements:[],numId:'',numEnr:'',geoloc:''},
  points:[],contraintesNotes:'',
  grc:{dim:'',vit:'',densite:'',mini:false,m1a:'none',m1b:'none',m1c:'none',m2:'none'},
  arc:{atypical:'',fl600:'',airport:'',airportClass:'',above500:'',adsb:'',eac:'',urban:'',residual:'',reduceJust:'',tacJust:''},
  prevol:{},journal:[],forms:{regime:'',expType:'morale',derogType:'',aotGestionnaire:'',aotObjet:''}};}
function curDossier(){ return store.dossiers.find(d=>d.id===currentDossierId)||null; }

/* ---------- Dossier (détail à onglets) ---------- */
function viewDossier(v){
  const D=curDossier(); if(!D){currentDossierId='';return renderView();}
  const top=el('div',null); top.style.cssText='display:flex;justify-content:space-between;align-items:center';
  const back=el('button','btn sm',t('back_dossiers')); back.onclick=()=>{currentDossierId='';renderView();};
  top.appendChild(back);
  const del=el('button','btn danger sm',t('btn_del_dossier'));
  del.onclick=()=>{if(!confirm(t('confirm_del_dossier')))return;store.dossiers=store.dossiers.filter(x=>x.id!==D.id);currentDossierId='';scheduleSave();renderView();};
  top.appendChild(del); v.appendChild(top);
  v.appendChild(el('h1','page-h',D.titre||t('dossier_default_title')));
  const tabs=el('div','tabs');
  const TABS=[['mission',t('tab_mission')],['regime',t('tab_regime')],['conformite',t('tab_conformite')],['sora',t('tab_sora')],
    ['prevol',t('tab_prevol')],['journal',t('tab_journal')],['docs',t('tab_docs')]];
  TABS.forEach(([k,label])=>{const b=el('button','tab'+(dossierTab===k?' on':''),label);b.onclick=()=>{dossierTab=k;renderView();};tabs.appendChild(b);});
  v.appendChild(tabs);
  ({mission:tabMission,regime:tabRegime,conformite:tabConformite,sora:tabSora,prevol:tabPrevol,journal:tabJournal,docs:tabDocs}[dossierTab])(v,D);
}

function tabMission(v,D){
  const c=card(t('mission_kick'),t('mission_title'),t('mission_desc'));
  const g=el('div','grid');
  g.append(field(t('f_intitule'),D,'titre',{after:()=>{},ph:t('ph_titre')}),field(t('f_client'),D,'client',{ph:t('ph_client')}),
    field(t('f_datedebut'),D,'dateDebut',{type:'date'}),field(t('f_datefin'),D,'dateFin',{type:'date'}),
    field(t('f_hauteur'),D,'hauteurMax',{type:'number',ph:t('ph_hauteur')}),
    field(t('f_typevol'),D,'typeVol',{type:'select',options:optTypevol()}),
    field(t('f_env'),D,'environnement',{type:'select',options:optEnv()}),
    field(t('f_dist'),D,'distanceTiers',{type:'select',options:optDist()}));
  c.appendChild(g); c.appendChild(field(t('f_notes_mission'),D,'notes',{type:'textarea',full:true,ph:t('ph_notes_mission')})); v.appendChild(c);

  const ac=card(t('appareil_kick'),t('appareil_title'),t('appareil_desc'));
  const opts=[['',t('opt_choose_dji')]]; let lastCat='';
  dronesDB.all.forEach(d=>{opts.push([d.key,(d.cat!==lastCat?'【'+d.cat+'】 ':'')+'DJI '+d.modele]);lastCat=d.cat;});
  opts.push(['manuel',t('opt_manual')]);
  ac.appendChild(field(t('f_modele'),D.appareil,'key',{type:'select',options:opts,after:()=>applyModel(D)}));
  const isDji=!!dronesDB.all.find(d=>d.key===D.appareil.key);
  if(!Array.isArray(D.appareil.equipements))D.appareil.equipements=[];
  const g2=el('div','grid3');
  g2.append(field(t('f_marque'),D.appareil,'marque',{readonly:isDji,ph:t('ph_marque')}),field(t('f_modele'),D.appareil,'modele',{readonly:isDji,ph:t('ph_modele')}),
    field(t('f_classe'),D,'classeC',{type:'select',options:CLASSES}),
    field(t('f_dim'),D.grc,'dim',{readonly:isDji,ph:t('ph_dim')}),field(t('f_vitmax'),D.grc,'vit',{readonly:isDji,ph:t('ph_vitmax')}),
    field(t('f_masse'),D.appareil,'masse',{readonly:isDji,ph:t('ph_masse')}),
    field(t('f_geoloc'),D.appareil,'geoloc',{ph:t('ph_geoloc')}),field(t('f_serie'),D.appareil,'serie',{ph:t('ph_serie')}),
    field(t('f_numid'),D.appareil,'numId',{ph:t('ph_numid')}),field(t('f_numenr'),D.appareil,'numEnr',{ph:t('ph_numenr')}));
  ac.appendChild(g2);
  // Équipements embarqués (liste éditable).
  ac.appendChild(el('div','note',t('equip_title')));
  const eq=D.appareil.equipements;
  eq.forEach((it,i)=>{const row=el('div','row-actions');
    const inp=el('input');inp.value=it||'';inp.placeholder=t('equip_ph');inp.style.flex='1';
    inp.oninput=()=>{eq[i]=inp.value;scheduleSave();};
    const rm=el('button','btn danger sm','−');rm.onclick=()=>{eq.splice(i,1);scheduleSave();renderView();};
    row.append(inp,rm);ac.appendChild(row);});
  if(!eq.length)ac.appendChild(el('div','note',t('equip_none')));
  const addEq=el('button','btn sm',t('btn_add_equip'));addEq.onclick=()=>{eq.push('');scheduleSave();renderView();};
  ac.appendChild(addEq);
  v.appendChild(ac);

  const mc=card(t('site_kick'),t('site_title'),t('site_desc'));
  const g3=el('div','grid');
  g3.append(field(t('f_adresse'),D,'siteAdresse',{ph:t('ph_siteadresse')}),field(t('f_ville'),D,'siteVille',{ph:t('ph_siteville')}),
    field(t('f_cp'),D,'siteCp',{ph:t('ph_sitecp')}),field(t('f_icao'),D,'icao',{ph:t('ph_icao')}),
    field(t('f_lat'),D,'lat',{ph:t('ph_lat')}),field(t('f_lon'),D,'lon',{ph:t('ph_lon')}));
  mc.appendChild(g3);
  const bar=el('div','row-actions');
  const geo=el('button','btn',t('btn_geoloc'));geo.onclick=()=>geocodeSite(D);
  const map=el('button','btn',t('btn_map'));map.onclick=()=>openMap(D);
  const met=el('button','btn',t('btn_weather'));met.onclick=()=>releveMeteo(D);
  bar.append(geo,map,met); mc.appendChild(bar);
  if(D.meteo&&D.meteo.metar){mc.appendChild(el('div','note','METAR : '+D.meteo.metar));}
  v.appendChild(mc);

  // ---- Contexte : points de vol + contraintes ----
  if(!Array.isArray(D.points))D.points=[];
  const cc=card(t('context_kick'),t('context_title'),t('context_desc'));
  D.points.forEach((pt,i)=>{const row=el('div','row-actions');
    const bd=badge(pt.type==='observateur'?'b-orange':'b-blue',pt.type==='observateur'?t('pt_observer'):t('pt_takeoff'));
    const nm=el('input');nm.value=pt.intitule||'';nm.placeholder=t('pt_intitule_ph');nm.style.flex='1';
    nm.oninput=()=>{pt.intitule=nm.value;scheduleSave();};
    const la=el('input');la.value=pt.lat||'';la.placeholder=t('ph_lat');la.style.width='100px';la.oninput=()=>{pt.lat=la.value;scheduleSave();};
    const lo=el('input');lo.value=pt.lon||'';lo.placeholder=t('ph_lon');lo.style.width='100px';lo.oninput=()=>{pt.lon=lo.value;scheduleSave();};
    const rm=el('button','btn danger sm','−');rm.onclick=()=>{D.points.splice(i,1);scheduleSave();renderView();};
    row.append(bd,nm,la,lo,rm);cc.appendChild(row);});
  if(!D.points.length)cc.appendChild(el('div','note',t('pt_none')));
  const barp=el('div','row-actions');
  const addT=el('button','btn sm',t('btn_add_takeoff'));
  addT.onclick=()=>{D.points.push({type:'decollage',intitule:'',lat:D.lat||'',lon:D.lon||''});scheduleSave();renderView();};
  const addO=el('button','btn sm',t('btn_add_observer'));
  addO.onclick=()=>{D.points.push({type:'observateur',intitule:'',lat:'',lon:''});scheduleSave();renderView();};
  barp.append(addT,addO);cc.appendChild(barp);
  cc.appendChild(field(t('f_contraintes'),D,'contraintesNotes',{type:'textarea',rows:3,full:true,ph:t('contraintes_ph')}));
  v.appendChild(cc);
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
  if(!q){alert(t('addr_missing'));return;}
  try{const r=await apiGet('/api/geocode?q='+encodeURIComponent(q));D.lat=r.lat.toFixed(6);D.lon=r.lon.toFixed(6);if(!D.lieu)D.lieu=r.label;scheduleSave();renderView();}
  catch(e){alert(t('geo_fail',{e:(e.message||e)}));}
}
async function releveMeteo(D){
  if(!D.icao){alert(t('icao_missing'));return;}
  try{const r=await apiGet('/api/weather?icao='+encodeURIComponent(D.icao));D.meteo=r;scheduleSave();renderView();
    if(r.error)alert(t('weather_fail',{e:r.error}));}
  catch(e){alert(t('weather_fail',{e:(e.message||e)}));}
}
function openMap(D){
  const ov=el('div','mapmodal');const box=el('div','mapbox');
  const head=el('div','pdfhead');head.appendChild(el('b',null,t('map_title')));
  const close=el('button','btn sm primary',t('close'));head.appendChild(close);
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
  const c=card(t('regime_kick'),t('regime_title'),t('regime_desc'));
  const box=el('div','result');box.innerHTML='<div><div class="big">…</div><div class="lbl">'+t('recommended')+'</div></div>';
  c.appendChild(box); v.appendChild(c);
  apiSend('/api/regime','POST',D).then(rec=>{
    box.innerHTML='';
    const l=el('div');l.innerHTML='<div class="big">'+(rec.short||'—')+'</div><div class="lbl">'+t('recommended')+'</div>';
    const r=el('div');r.style.cssText='border-left:1px solid #cfe0f6;padding-left:14px;flex:1';
    r.appendChild(el('b',null,t('rl_'+rec.regime)+(rec.sub?' — '+rec.sub:'')));
    r.appendChild(el('div','note',rec.why));
    box.append(l,r);
    if(rec.missing)c.appendChild(el('div','warn',rec.missing));
    const choose=el('div','row-actions');
    [['open',t('regime_open')],['sts','STS'],['pdra','PDRA'],['sora','SORA']].forEach(([k,lab])=>{
      const b=el('button','btn'+(D.regime===k?' primary':''),lab+(rec.regime===k?t('advised_suffix'):''));
      b.onclick=()=>{D.regime=k;if(k==='open'&&rec.sub)D.sousCategorie=rec.sub;scheduleSave();renderView();};choose.appendChild(b);
    });
    c.appendChild(el('div','note',t('regime_kept')));c.appendChild(choose);
    if(D.regime==='open'){c.appendChild(field(t('f_souscat'),D,'sousCategorie',{type:'select',options:optSouscat()}));}
    if(D.regime==='pdra'){c.appendChild(field(t('f_pdra'),D,'pdra',{type:'select',options:optPdra()}));}
  });
}
function tabConformite(v,D){
  if(D.regime==='sora'){ v.appendChild(card('SORA',null,t('conf_sora_note'))); return; }
  if(D.regime==='open'){
    const c=card(t('conf_open_kick'),t('conf_open_title'),t('conf_open_desc'));
    v.appendChild(c);
    apiSend('/api/regime/open','POST',D).then(res=>{
      c.appendChild(badge(res.ok?'b-green':'b-orange',res.ok?t('conf_ok'):t('conf_ko')));
      res.items.forEach(it=>{const r=el('div','ck');r.appendChild(el('span',null,it.ok?'✅':'⚠️'));r.appendChild(el('span',null,it.text));c.appendChild(r);});
    });
    return;
  }
  const lbl={sts:'STS',pdra:'PDRA'}[D.regime]||'—';
  const c=card(t('conf_spec_kick',{x:lbl}),t('conf_spec_title'),t('conf_spec_desc'));
  c.appendChild(el('div','note',D.regime==='sts'
    ? 'STS-01 : VLOS, drone C5, zone au sol contrôlée. STS-02 : BVLOS avec observateurs, drone C6, zone peu peuplée. Déclaration à la DGAC.'
    : 'PDRA : scénario de risque prédéfini (méthode SORA pré-instruite). Demande d’autorisation d’exploitation.'));
  v.appendChild(c);
}
function tabSora(v,D){
  const g=card(t('sora_grc_kick'),t('sora_grc_steps'),t('sora_grc_desc'));
  const gg=el('div','grid');
  gg.append(field(t('f_dim'),D.grc,'dim',{ph:t('ph_dim')}),field(t('f_vit'),D.grc,'vit',{ph:t('ph_vitmax')}),
    field(t('f_densite'),D.grc,'densite',{type:'select',options:optDensite()}),
    field(t('f_m1a'),D.grc,'m1a',{type:'select',options:optMitA()}),
    field(t('f_m1b'),D.grc,'m1b',{type:'select',options:optMitB()}),
    field(t('f_m2'),D.grc,'m2',{type:'select',options:optMit2()}));
  g.appendChild(gg); v.appendChild(g);
  const a=card(t('sora_arc_kick'),t('sora_arc_steps'),t('sora_arc_desc'));
  const ag=el('div','grid');
  ag.append(field(t('f_atypical'),D.arc,'atypical',{type:'select',options:optYN()}),
    field('> FL600',D.arc,'fl600',{type:'select',options:optYN()}),
    field(t('f_airport'),D.arc,'airport',{type:'select',options:optYN()}),
    field(t('f_airportclass'),D.arc,'airportClass',{type:'select',options:optYN()}),
    field('> 500 ft AGL',D.arc,'above500',{type:'select',options:optYN()}),
    field(t('f_urban'),D.arc,'urban',{type:'select',options:optYN()}),
    field(t('f_arcres'),D.arc,'residual',{type:'select',options:optArcRes()}));
  a.appendChild(ag); v.appendChild(a);
  const res=card(t('sora_res_kick'),t('sora_res_title'),''); const out=el('div');res.appendChild(out);v.appendChild(res);
  const btn=el('button','btn primary',t('btn_calc_sora'));btn.onclick=()=>runSora(D,out);res.insertBefore(btn,out);
  runSora(D,out);
}
async function runSora(D,out){
  const r=await apiSend('/api/sora','POST',{grc:D.grc,arc:D.arc}); out.innerHTML='';
  if(!r.valid){out.appendChild(el('div','warn',t('sora_invalid')));}
  const box=el('div','result');
  box.innerHTML='<div><div class="big">'+(r.sail||'—')+'</div><div class="lbl">SAIL</div></div>'+
    '<div style="border-left:1px solid #cfe0f6;padding-left:14px;flex:1"><b>iGRC '+(r.igrc??'—')+' → GRC '+(r.grc??'—')+'</b>'+
    '<div class="note">ARC '+(r.arcInitial||'—').toUpperCase()+' → '+(r.arcResidual||'—').toUpperCase()+'</div></div>';
  out.appendChild(box);
  if(r.cumulConflict)out.appendChild(el('div','warn',t('sora_cumul')));
  if(r.osoReq&&r.osoReq.length){
    const tbl=el('table');tbl.style.cssText='width:100%;border-collapse:collapse;margin-top:10px;font-size:12.5px';
    const hr=el('tr');
    [['OSO',70],[t('oso_col_obj'),0],[t('oso_col_rob'),120]].forEach(([h,w])=>{const th=el('th',null,h);th.style.cssText='text-align:left;padding:4px 6px;border-bottom:1px solid var(--bord);color:var(--gris);font-weight:700'+(w?';width:'+w+'px':'');hr.appendChild(th);});
    tbl.appendChild(hr);
    const RT={'L':'oso_low','M':'oso_med','H':'oso_high','-':'oso_none'};
    const RC={'L':'b-yellow','M':'b-orange','H':'b-red','-':'b-grey'};
    r.osoReq.forEach(o=>{const tr=el('tr');
      const td1=el('td',null,'OSO '+o.id);td1.style.cssText='padding:4px 6px;border-bottom:1px solid var(--bord);width:70px';
      const td2=el('td',null,o.t);td2.style.cssText='padding:4px 6px;border-bottom:1px solid var(--bord)';
      const td3=el('td');td3.style.cssText='padding:4px 6px;border-bottom:1px solid var(--bord);width:120px';
      td3.appendChild(badge(RC[o.lvl],t(RT[o.lvl])));tr.append(td1,td2,td3);tbl.appendChild(tr);});
    out.appendChild(tbl);
  }
}
function tabPrevol(v,D){
  const c=card(t('prevol_kick'),t('prevol_title'),t('prevol_desc'));
  PREVOL.forEach(item=>{const r=el('label','ck');const cb=el('input');cb.type='checkbox';cb.checked=!!D.prevol[item];
    cb.onchange=()=>{D.prevol[item]=cb.checked;scheduleSave();};r.append(cb,el('span',null,item));c.appendChild(r);});
  v.appendChild(c);
}
function tabJournal(v,D){
  const c=card(t('journal_kick'),t('journal_title'),t('journal_desc'));
  (D.journal||[]).forEach((s,i)=>{const row=el('div','row-actions');
    const dt=el('input');dt.type='date';dt.value=s.date||'';dt.oninput=()=>{s.date=dt.value;scheduleSave();};
    const h1=el('input');h1.type='time';h1.value=s.debut||'';h1.oninput=()=>{s.debut=h1.value;scheduleSave();};
    const h2=el('input');h2.type='time';h2.value=s.fin||'';h2.oninput=()=>{s.fin=h2.value;scheduleSave();};
    const nb=el('input');nb.type='number';nb.placeholder=t('journal_ph_flights');nb.style.width='70px';nb.value=s.nb||'';nb.oninput=()=>{s.nb=nb.value;scheduleSave();};
    const inc=el('input');inc.placeholder=t('journal_ph_incidents');inc.style.flex='1';inc.value=s.incidents||'';inc.oninput=()=>{s.incidents=inc.value;scheduleSave();};
    const rm=el('button','btn danger sm','−');rm.onclick=()=>{D.journal.splice(i,1);scheduleSave();renderView();};
    row.append(dt,h1,h2,nb,inc,rm);c.appendChild(row);});
  const add=el('button','btn sm',t('btn_add_session'));add.onclick=()=>{D.journal.push({date:new Date().toISOString().slice(0,10),debut:'',fin:'',nb:'',incidents:''});scheduleSave();renderView();};
  c.appendChild(add); v.appendChild(c);
}
function tabDocs(v,D){
  const c=card(t('doc_kick'),t('doc_title'),t('doc_desc'));
  const bar=el('div','row-actions');
  bar.appendChild(pdfBtn(t('btn_dossier_pdf'),'/api/report/dossier',{dossierId:D.id}));
  bar.appendChild(pdfBtn(t('btn_rapport_pdf'),'/api/report/rapport',{dossierId:D.id}));
  c.appendChild(bar);
  const bar2=el('div','row-actions');
  bar2.appendChild(pdfBtn(t('btn_cerfa'),'/api/form/cerfa',{dossierId:D.id}));
  bar2.appendChild(pdfBtn(t('btn_derog'),'/api/form/derog',{dossierId:D.id}));
  bar2.appendChild(pdfBtn(t('btn_aot'),'/api/form/aot',{dossierId:D.id}));
  c.appendChild(el('div','note',t('forms_official')));c.appendChild(bar2);
  v.appendChild(c);
}
function pdfBtn(label,path,body){
  const b=el('button','btn primary',label);
  b.onclick=async()=>{try{const blob=await apiPdf(path,body);openPdf(blob,label);}catch(e){alert(t('gen_fail',{e:(e.message||e)}));}};
  return b;
}
function openPdf(blob,title){
  const url=URL.createObjectURL(blob);
  const ov=el('div','pdfmodal');const box=el('div','pdfbox');
  const head=el('div','pdfhead');head.appendChild(el('b',null,title));
  const dl=el('a','btn sm',t('pdf_save'));dl.href=url;dl.download=(title.replace(/[^\w]+/g,'_')||'document')+'.pdf';head.appendChild(dl);
  const close=el('button','btn sm primary',t('close'));head.appendChild(close);
  const fr=el('iframe','pdfframe');fr.src=url;box.append(head,fr);ov.appendChild(box);document.body.appendChild(ov);
  close.onclick=()=>{URL.revokeObjectURL(url);document.body.removeChild(ov);};
}

/* ---------- Carte & restrictions (consultation) ----------
   Couches officielles Géoportail (data.geopf.fr, sans clé) : restrictions drone
   (aéro), plan IGN, satellite ; plus OpenStreetMap qui affiche les noms de
   communes. La couche restrictions est un calque semi-transparent posé au-dessus,
   pour voir à la fois les zones et les villes (ce qui manque sur Flyby). */
function geopfLayer(layer, fmt){
  const url='https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0'
    +'&LAYER='+layer+'&STYLE=normal&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}'
    +'&FORMAT='+encodeURIComponent(fmt);
  return L.tileLayer(url,{maxZoom:19,attribution:'© IGN / Géoportail',crossOrigin:true});
}
function viewCarte(v){
  v.appendChild(el('h1','page-h',t('nav_carte')));
  v.appendChild(el('p','page-sub',t('carte_sub')));
  const bar=el('div','row-actions');
  const search=el('input'); search.placeholder=t('carte_search');
  search.style.cssText='flex:1;min-width:220px;padding:9px 11px;border:1px solid var(--bord);border-radius:9px;font-size:13.5px';
  const go=el('button','btn primary',t('carte_go'));
  bar.append(search,go); v.appendChild(bar);
  const md=el('div'); md.id='bigmap';
  md.style.cssText='height:70vh;min-height:420px;border:1px solid var(--bord);border-radius:12px;overflow:hidden';
  v.appendChild(md);
  const coord=el('div','note',t('carte_click')); v.appendChild(coord);
  setTimeout(()=>initCarte(search,go,coord),60);
}
function initCarte(search,go,coord){
  const osm=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'});
  const plan=geopfLayer('GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2','image/png');
  const ortho=geopfLayer('ORTHOIMAGERY.ORTHOPHOTOS','image/jpeg');
  const resto=geopfLayer('TRANSPORTS.DRONES.RESTRICTIONS','image/png'); resto.setOpacity(0.55);
  const map=L.map('bigmap',{center:[46.7,-1.42],zoom:8,layers:[osm,resto]});
  const bases={}; bases[t('layer_osm')]=osm; bases[t('layer_plan')]=plan; bases[t('layer_ortho')]=ortho;
  const overlays={}; overlays[t('layer_resto')]=resto;
  L.control.layers(bases,overlays,{collapsed:false}).addTo(map);
  let mk=null;
  map.on('click',e=>{ coord.textContent=e.latlng.lat.toFixed(5)+', '+e.latlng.lng.toFixed(5);
    if(mk)mk.setLatLng(e.latlng); else mk=L.marker(e.latlng).addTo(map); });
  async function jump(){ const q=search.value.trim(); if(!q)return;
    try{ const r=await apiGet('/api/geocode?q='+encodeURIComponent(q)); map.setView([r.lat,r.lon],14);
      if(mk)mk.setLatLng([r.lat,r.lon]); else mk=L.marker([r.lat,r.lon]).addTo(map);
    }catch(e){ alert(t('addr_notfound')); } }
  go.onclick=jump; search.addEventListener('keydown',e=>{ if(e.key==='Enter')jump(); });
  setTimeout(()=>map.invalidateSize(),150);
}

/* ---------- Check-list de référence (consultable) ---------- */
function viewChecklistRef(v){
  v.appendChild(el('h1','page-h',t('nav_checklist')));
  v.appendChild(el('p','page-sub',t('checklist_sub')));
  const c=card(t('checklistref_kick'),t('checklistref_title'),'');
  PREVOL.forEach(i=>{const r=el('div','ck');r.append(el('span',null,'☐'),el('span',null,i));c.appendChild(r);});
  v.appendChild(c);
}

/* ---------- Documents / MANEX / sauvegarde ---------- */
function viewDocs(v){
  v.appendChild(el('h1','page-h',t('nav_docs')));
  v.appendChild(el('p','page-sub',t('docs_sub')));
  const {card:c,body:cb}=collCard('docs-justif',t('docs_justif_kick'),t('docs_justif_title'),'',true);
  const imp=el('button','btn primary',t('btn_import_doc'));
  imp.onclick=()=>{const i=document.createElement('input');i.type='file';i.onchange=()=>uploadDoc(i.files[0]);i.click();};
  cb.appendChild(imp); const list=el('div');list.id='docslist';cb.appendChild(list);v.appendChild(c);loadDocs();

  const {card:mc,body:mb}=collCard('docs-manex',t('manex_kick'),t('manex_title'),t('manex_desc'),false);
  mb.appendChild(pdfBtn(t('btn_gen_manex'),'/api/report/manex',{}));v.appendChild(mc);

  const {card:sb,body:sd}=collCard('docs-save',t('save_kick'),t('save_title'),t('save_desc'),false);
  const bar=el('div','row-actions');
  const ex=el('button','btn primary',t('btn_export_data'));ex.onclick=()=>{window.location='/api/backup';};
  const im=el('button','btn',t('btn_import_data'));im.onclick=()=>{const i=document.createElement('input');i.type='file';i.accept='.json';i.onchange=()=>restoreBackup(i.files[0]);i.click();};
  bar.append(ex,im);sd.appendChild(bar);sd.appendChild(el('div','note',t('import_replace_note')));v.appendChild(sb);
}
async function loadDocs(){
  const list=document.getElementById('docslist');if(!list)return;list.innerHTML='';
  let docs=[];try{docs=await apiGet('/api/docs');}catch(e){}
  if(!docs.length){list.appendChild(el('div','note',t('docs_none')));return;}
  docs.forEach(d=>{const row=el('div','row-actions');
    const nm=el('div',null,d.name);nm.style.cssText='flex:1;font-size:13.5px';
    row.appendChild(nm);row.appendChild(badge('b-grey',fmtSize(d.size)));
    const lire=el('button','btn sm primary',t('btn_read'));lire.onclick=()=>window.open('/api/docs/'+encodeURIComponent(d.name),'_blank');
    const exp=el('a','btn sm');exp.textContent=t('btn_export');exp.href='/api/docs/'+encodeURIComponent(d.name);exp.download=d.name;
    const del=el('button','btn danger sm','🗑');del.onclick=async()=>{if(!confirm(t('confirm_del_doc',{name:d.name})))return;await fetch('/api/docs/'+encodeURIComponent(d.name),{method:'DELETE'});loadDocs();};
    row.append(lire,exp,del);list.appendChild(row);});
}
function fmtSize(n){if(n<1024)return n+' o';if(n<1048576)return(n/1024).toFixed(0)+' Ko';return(n/1048576).toFixed(1)+' Mo';}
async function uploadDoc(file){if(!file)return;const fd=new FormData();fd.append('file',file);
  try{await fetch('/api/docs',{method:'POST',body:fd});loadDocs();}catch(e){alert(t('import_fail',{e:e}));}}
async function restoreBackup(file){if(!file)return;const txt=await file.text();let data;try{data=JSON.parse(txt);}catch(e){alert(t('json_invalid'));return;}
  if(!confirm(t('confirm_restore')))return;
  await apiSend('/api/backup','POST',data);store=await apiGet('/api/store');current='exploitant';renderNav();renderView();}

/* ---------- Liens ---------- */
function viewLiens(v){
  v.appendChild(el('h1','page-h',t('nav_links')));
  v.appendChild(el('p','page-sub',t('liens_sub')));
  v.appendChild(linkCard('l-utiles',t('liens_res_kick'),t('liens_res_title'),'',LINKS,true));
  v.appendChild(linkCard('l-marches',t('liens_biz_kick'),t('liens_biz_title'),'',MARCHES,false));
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
