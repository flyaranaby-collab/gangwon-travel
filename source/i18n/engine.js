// ───────── 다국어(영어·중국어·일본어) ─────────
// 화면을 그린 뒤 글자(텍스트 노드)를 사전으로 바꾼다. 한국어로 돌아갈 땐 원문을 되돌린다.
const LANGS = { ko:"한국어", en:"English", zh:"中文", ja:"日本語" };
const LANG_IDX = { en:0, zh:1, ja:2 };
let LANG = "ko";
try { const qs = new URLSearchParams(location.search).get("lang"); LANG = LANGS[qs] ? qs : (localStorage.getItem("gw_lang") || "ko"); if (!LANGS[LANG]) LANG = "ko"; } catch(_) {}
const I18N_RE = {};
function i18nRegex(){
  if (I18N_RE.all) return I18N_RE.all;
  const esc = k => k.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");
  const keys = Object.keys(I18N_DICT).sort((a,b)=>b.length-a.length)
    .map(k => k.length<=2 ? "(?<![가-힣])"+esc(k)+"(?![가-힣])" : esc(k));
  return I18N_RE.all = new RegExp(keys.join("|"), "g");
}
const WD_T = { en:{일:"Sun",월:"Mon",화:"Tue",수:"Wed",목:"Thu",금:"Fri",토:"Sat"}, zh:{일:"日",월:"一",화:"二",수:"三",목:"四",금:"五",토:"六"}, ja:{일:"日",월:"月",화:"火",수:"水",목:"木",금:"金",토:"土"} };
const MON_EN = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const wdList = (s,l) => s.split("·").map(c=>WD_T[l][c]).join(l==="en"?"/":"、");
const wonFmt = n => "₩" + Math.round(n).toLocaleString("en-US");
function i18nPre(t, l){
  const W = WD_T[l];
  return t
    .replace(/매주 ([일월화수목금토](?:·[일월화수목금토])*)요일 (휴무|휴원)/g, (_,d)=> l==="en" ? `Closed every ${wdList(d,l)}` : l==="zh" ? `每周${wdList(d,l).split("、").map(x=>"星期"+x).join("、")}休息` : `毎週${wdList(d,l)}曜定休`)
    .replace(/([일월화수목금토](?:·[일월화수목금토])*)요일 (휴무|휴원)/g, (_,d)=> l==="en" ? `Closed ${wdList(d,l)}` : l==="zh" ? `${wdList(d,l).split("、").map(x=>"星期"+x).join("、")}休息` : `${wdList(d,l)}曜定休`)
    .replace(/([일월화수목금토])요일/g, (_,d)=> l==="en" ? ({일:"Sunday",월:"Monday",화:"Tuesday",수:"Wednesday",목:"Thursday",금:"Friday",토:"Saturday"})[d] : l==="zh" ? "星期"+W[d] : W[d]+"曜日")
    .replace(/([일월화수목금토])~([일월화수목금토])/g, (_,a,b)=> `${W[a]}${l==="en"?"–":"～"}${W[b]}`)
    .replace(/(\d+)인(?![가-힣])/g, (_,n)=> l==="en" ? (n==="1" ? "per person" : `${n} people`) : `${n}人`)
    .replace(/약 (?=[\d₩])/g, l==="en" ? "approx. " : l==="zh" ? "约" : "約");
}
function i18nRules(t, l){
  const U = { en:["places","min","people"], zh:["个地点","分钟","人"], ja:["か所","分","人"] }[l];
  const W = WD_T[l];
  return t
    .replace(/(\d+)월 (\d+)일/g, (_,m,d)=> l==="en" ? `${MON_EN[m-1]} ${d}` : `${m}月${d}日`)
    .replace(/(\d+)일차/g, (_,n)=> l==="en" ? `Day ${n}` : l==="zh" ? `第${n}天` : `${n}日目`)
    .replace(/(\d+(?:\.\d+)?)\s?~\s?(\d+(?:\.\d+)?)만\s?원(대)?/g, (_,a,b)=> `${wonFmt(a*1e4)}–${wonFmt(b*1e4)}`)
    .replace(/(\d+(?:\.\d+)?)만\s?원대(?:\s?(초반|중반|후반))?/g, (_,a)=> l==="en" ? `${wonFmt(a*1e4)}+` : `${wonFmt(a*1e4)}起`)
    .replace(/(\d+(?:\.\d+)?)만\s?원/g, (_,a)=> wonFmt(a*1e4))
    .replace(/(\d+)\s?~\s?(\d+)천\s?원(대)?/g, (_,a,b)=> `${wonFmt(a*1e3)}–${wonFmt(b*1e3)}`)
    .replace(/(\d+)천\s?원(대)?/g, (_,a,c)=> wonFmt(a*1e3) + (c ? (l==="en"?"+":"起") : ""))
    .replace(/(\d[\d,]*)\s?원(대)?/g, (_,a,c)=> wonFmt(+a.replace(/,/g,"")) + (c ? (l==="en"?"+":"起") : ""))
    .replace(/(\d+)\s?곳/g, (_,n)=> l==="en" ? `${n} ${U[0]}` : n+U[0])
    .replace(/(\d+)\s?분/g, (_,n)=> l==="en" ? `${n} ${U[1]}` : n+U[1])
    .replace(/(\d+)\s?명/g, (_,n)=> l==="en" ? `${n} ${U[2]}` : n+U[2])
    .replace(/(\d+)\s?박/g, (_,n)=> l==="en" ? `${n} night${n>1?"s":""}` : l==="zh" ? `${n}晚` : `${n}泊`)
    .replace(/(\d+)\s?시간/g, (_,n)=> l==="en" ? `${n} hr` : l==="zh" ? `${n}小时` : `${n}時間`)
    .replace(/(\d+)월/g, (_,m)=> l==="en" ? MON_EN[m-1] || m : `${m}月`)
    .replace(/(\d+)\s?시/g, (_,n)=> `${n}:00`)
    .replace(/(\d+)\s?일/g, (_,n)=> l==="en" ? `${n} days` : l==="zh" ? `${n}天` : `${n}日`);
}
function trStr(s){
  if (LANG==="ko" || !s || !/[가-힣]/.test(s)) return s;
  const i = LANG_IDX[LANG];
  const tk = s.trim(); if (I18N_DICT[tk]) return s.replace(tk, I18N_DICT[tk][i]);
  let out = i18nPre(s, LANG).replace(i18nRegex(), m => (I18N_DICT[m] && I18N_DICT[m][i]) || m);
  out = i18nRules(out, LANG);
  return out;
}
const I18N_ATTRS = ["placeholder","aria-label","title","alt"];
function i18nApply(root){
  root = root || document.body;
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, { acceptNode: n => {
    const p = n.parentNode; if (!p) return NodeFilter.FILTER_REJECT;
    const tg = p.nodeName; if (tg==="SCRIPT"||tg==="STYLE"||tg==="TEXTAREA") return NodeFilter.FILTER_REJECT;
    if (p.closest && p.closest("[data-noi18n]")) return NodeFilter.FILTER_REJECT;
    return NodeFilter.FILTER_ACCEPT; } });
  const nodes = []; while (w.nextNode()) nodes.push(w.currentNode);
  for (const n of nodes){
    if (n.__tr !== undefined && n.nodeValue === n.__tr) { if (LANG==="ko") { n.nodeValue = n.__ko; n.__tr = undefined; } else if (n.__lang!==LANG){ n.__tr = trStr(n.__ko); n.__lang=LANG; n.nodeValue = n.__tr; } continue; }
    if (LANG==="ko") continue;
    if (!/[가-힣]/.test(n.nodeValue)) continue;
    n.__ko = n.nodeValue; n.__tr = trStr(n.__ko); n.__lang = LANG; n.nodeValue = n.__tr;
  }
  (root.querySelectorAll ? [root, ...root.querySelectorAll("*")] : []).forEach(el=>{
    if (!el.getAttribute) return;
    I18N_ATTRS.forEach(a=>{
      const v = el.getAttribute(a); if (v==null) return;
      const key = "__ko_"+a;
      if (el[key]!==undefined && (v===el["__tr_"+a])) { const nv = LANG==="ko" ? el[key] : trStr(el[key]); el["__tr_"+a]=nv; el.setAttribute(a,nv); return; }
      if (!/[가-힣]/.test(v) || LANG==="ko") return;
      el[key]=v; const nv=trStr(v); el["__tr_"+a]=nv; el.setAttribute(a,nv);
    });
  });
}
let i18nQueued = false;
const i18nObs = new MutationObserver(()=>{ if (LANG==="ko" || i18nQueued) return; i18nQueued = true; requestAnimationFrame(()=>{ i18nQueued=false; i18nObs.disconnect(); i18nApply(); i18nObs.observe(document.body, {childList:true, subtree:true, characterData:true}); }); });
function setLang(l){
  LANG = LANGS[l] ? l : "ko";
  try { localStorage.setItem("gw_lang", LANG); } catch(_) {}
  document.documentElement.lang = LANG==="zh" ? "zh-CN" : LANG;
  document.title = LANG==="ko" ? "강원 여행 수첩" : trStr("강원 여행 수첩");
  document.querySelectorAll("#langSeg button").forEach(b=>b.setAttribute("aria-pressed", b.dataset.lang===LANG));
  i18nObs.disconnect(); i18nApply(); i18nObs.observe(document.body, {childList:true, subtree:true, characterData:true});
  if (typeof wxRefresh==="function") wxRefresh();
}
document.addEventListener("click", e=>{ const b = e.target.closest("[data-lang]"); if (b) setLang(b.dataset.lang); });
