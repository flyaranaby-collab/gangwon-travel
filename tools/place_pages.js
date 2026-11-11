// 장소별 홈페이지 페이지를 만든다.  사용: node tools/place_pages.js _site
// - 수첩 데이터(web/index.html 의 PLACES·REGIONS·사진, web/owner.json 의 수정·삭제, web/kto.json 의 사진)를 읽어
//   /place/<id>/ 페이지, /place/ 전체 목록, /region/<지역>/ 목록, sitemap.xml, robots.txt 를 만든다.
// - 사이트 주소는 환경변수 SITE_URL (기본: GitHub Pages 주소). 페이지 안 링크는 상대경로라 주소가 바뀌어도 깨지지 않는다.
const fs = require("fs"), path = require("path");
const OUT = path.resolve(process.argv[2] || "_site");
const SITE = (process.env.SITE_URL || "https://flyaranaby-collab.github.io/gangwon-travel").replace(/\/+$/, "");
const read = f => fs.readFileSync(f, "utf8");
const html = read("web/index.html");

// ── 수첩 파일에서 데이터 꺼내기 ──
const between = (s, a, b, from = 0) => { const i = s.indexOf(a, from); if (i < 0) throw new Error("없음: " + a); const j = s.indexOf(b, i + a.length); if (j < 0) throw new Error("끝 없음: " + b); return s.slice(i + a.length, j); };
const arr = name => new Function("return [" + between(html, `const ${name} = [`, "\n];") + "\n]")();
const REGIONS = arr("REGIONS"), PLACES = arr("PLACES");
const REG = Object.fromEntries(REGIONS.map(r => [r.id, r]));
const PHOTOS = JSON.parse(between(html, "/*PHOTOS*/", "/*END_PHOTOS*/"));
const KTO_PHOTOS = JSON.parse(between(html, "/*KTO_PHOTOS*/", "/*END_KTO_PHOTOS*/"));
const PHOTO_KIND = { menu: "메뉴 예시 사진", area: "주변 풍경 사진", item: "분위기 예시 사진" };
let kto = {}; try { kto = JSON.parse(read("web/kto.json")); } catch (_) {}
Object.assign(KTO_PHOTOS, kto.photos || {});
let owner = {}; try { owner = JSON.parse(read("web/owner.json")); } catch (_) { try { owner = JSON.parse(between(html, 'id="ownerData" type="application/json">', "</script>")); } catch (_) {} }
const O = { places: owner.places || [], hidden: owner.hidden || [], deleted: owner.deleted || [], edits: owner.edits || {}, photos: owner.photos || {} };
const gone = new Set([...O.hidden, ...O.deleted.map(d => d.id || d)]);

// 운영자 수정·추가·삭제를 반영한 최종 장소 목록
const places = [...PLACES, ...O.places].map(p => ({ ...p, region: p.region || "gangneung" })).filter(p => !gone.has(p.id) && REG[p.region]).map(p => ({ closed: [], tags: [], who: {}, ...p, ...(O.edits[p.id] || {}) }));

// ── 도우미 ──
const WD = ["일", "월", "화", "수", "목", "금", "토"];
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clip = (s, n) => { s = String(s || "").replace(/\s+/g, " ").trim(); return s.length > n ? s.slice(0, n - 1) + "…" : s; };
const httpsUrl = u => String(u || "").replace(/^http:\/\//, "https://");
const sub = u => String(u).replace("https://appassets.androidplatform.net/assets/photos/", "__ROOT__photos/"); // 홈페이지 안 사진은 상대경로
const mapQuery = p => { if (p.mapq) return p.mapq; const nm = String(p.name).split(" · ")[0].replace(/\s*\((본점|.*점)\)/, " $1").trim(); const city = REG[p.region].name.split("·")[0]; return (nm.includes(city) || nm.includes(city.replace(/(시|군)$/, ""))) ? nm : city + " " + nm; };
const slug = id => encodeURIComponent(id);
function photoFor(p) {
  const op = O.photos[p.id]; if (op && op.url) return { url: op.url, credit: op.credit || "사진: 운영자 등록" };
  const c = PHOTOS[p.id];
  if (c) { const tag = PHOTO_KIND[c.kind] || ""; return { url: c.url, credit: `${tag ? tag + " · " : ""}사진: ${c.artist || "작가 미상"} · ${c.license || ""}`.trim(), link: c.page }; }
  const k = KTO_PHOTOS[p.id] || (p.img ? { url: p.img } : null);
  if (k) { const tag = PHOTO_KIND[k.kind] || ""; return { url: httpsUrl(k.url), credit: (tag ? tag + " · " : "") + (k.credit || "사진: 한국관광공사 · 공공누리 제1유형(출처 표시)") }; }
  return null;
}
const km = (a, b) => { const R = 6371, r = Math.PI / 180, dLa = (b.lat - a.lat) * r, dLo = (b.lng - a.lng) * r; const x = Math.sin(dLa / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLo / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(x)); };
const bestWho = p => { const e = Object.entries(p.who || {}).filter(([, v]) => v >= 3).map(([k]) => k); return e.length ? e.join(" · ") + "와 가기 좋아요" : ""; };
const ldType = c => ({ 맛집: "Restaurant", 카페: "CafeOrCoffeeShop", 숙소: "LodgingBusiness" })[c] || "TouristAttraction";

// ── 공통 틀 ──
const CSS = `:root{--bg:#f6f1e7;--surface:#fffdf8;--ink:#2b2620;--muted:#6f675c;--line:#e2d9c8;--accent:#9a5b2a;--link:#1d5fa6}
@media(prefers-color-scheme:dark){:root{--bg:#1b1814;--surface:#25211b;--ink:#efe8da;--muted:#a79d8d;--line:#3a342b;--accent:#d99a5f;--link:#7fb4ec}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 -apple-system,"Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",sans-serif}
a{color:var(--link)}.wrap{max-width:760px;margin:0 auto;padding:16px}
.crumb{font-size:13px;color:var(--muted);margin:4px 0 12px}.crumb a{color:var(--muted)}
h1{font-size:26px;line-height:1.3;margin:6px 0 4px}.eyebrow{color:var(--accent);font-size:14px;font-weight:700;letter-spacing:.02em}
.lead{font-size:17px;margin:6px 0 14px}.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:14px 0}
.photo{margin:12px 0}.photo img{width:100%;max-height:420px;object-fit:cover;border-radius:14px;display:block;background:var(--line)}.photo small{display:block;color:var(--muted);font-size:12px;margin-top:4px}
dl{margin:0;display:grid;grid-template-columns:7em 1fr;gap:8px 12px}dt{color:var(--muted);font-size:14px}dd{margin:0}
.btns{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.btn{display:inline-block;padding:10px 14px;border-radius:10px;border:1px solid var(--line);background:var(--surface);color:var(--ink);text-decoration:none;font-size:15px}.btn.pri{background:var(--accent);border-color:var(--accent);color:#fff}
h2{font-size:18px;margin:22px 0 8px}ul.list{list-style:none;margin:0;padding:0;display:grid;gap:8px}ul.list li{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:10px 14px}ul.list small{color:var(--muted);display:block}
.tags span{display:inline-block;margin:2px 6px 2px 0;padding:2px 10px;border-radius:99px;background:var(--line);font-size:13px}
footer{color:var(--muted);font-size:13px;margin:28px 0 8px}`;
function shell({ title, desc, canon, body, ld, og, root }) {
  return `<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(title)}</title><meta name="description" content="${esc(desc)}"><link rel="canonical" href="${esc(canon)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="강원 여행 수첩"><meta property="og:title" content="${esc(title)}"><meta property="og:description" content="${esc(desc)}"><meta property="og:url" content="${esc(canon)}">${og ? `<meta property="og:image" content="${esc(og)}">` : ""}
<meta name="theme-color" content="#f6f1e7"><style>${CSS}</style>${ld ? `<script type="application/ld+json">${JSON.stringify(ld).replace(/</g, "\\u003c")}</script>` : ""}</head><body><div class="wrap">${body.replace(/__ROOT__/g, root)}</div></body></html>`;
}
const footer = root => `<footer>정보는 바뀔 수 있어요. 방문 전에 운영 시간·휴무를 확인하세요. · <a href="${root}">강원 여행 수첩</a> · <a href="${root}place/">전체 장소</a></footer>`;

// ── 장소 페이지 ──
const write = (rel, s) => { const f = path.join(OUT, rel); fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, s); };
const urls = [];
const byRegion = {};
places.forEach(p => (byRegion[p.region] ||= []).push(p));

for (const p of places) {
  const R = REG[p.region], root = "../../", canon = `${SITE}/place/${slug(p.id)}/`, ph = photoFor(p);
  const near = places.filter(x => x.id !== p.id && x.region === p.region).map(x => [km(p, x), x]).sort((a, b) => a[0] - b[0]).slice(0, 6);
  const closedTxt = [p.closed.length ? p.closed.map(d => WD[d] + "요일").join("·") + " 휴무" : "", p.closedNote || ""].filter(Boolean).join(" · ") || "정기 휴무 정보 없음";
  const q = mapQuery(p), name1 = String(p.name).split(" · ")[0];
  const desc = clip(`${R.name} ${p.area ? p.area + " " : ""}${p.cat} · ${p.sig || ""}${p.tip ? " " + p.tip : ""}`, 150);
  const photoUrl = ph ? sub(ph.url) : "";
  const absPhoto = ph ? (/^https?:/.test(ph.url) ? ph.url : `${SITE}/${String(ph.url).replace(/^\/+/, "")}`) : "";
  const absPhoto2 = photoUrl.startsWith("__ROOT__") ? `${SITE}/${photoUrl.replace("__ROOT__", "")}` : absPhoto;
  const ld = { "@context": "https://schema.org", "@type": ldType(p.cat), name: p.name, description: clip(`${p.sig || ""} ${p.tip || ""}`, 200), url: canon,
    geo: { "@type": "GeoCoordinates", latitude: p.lat, longitude: p.lng }, address: { "@type": "PostalAddress", addressRegion: "강원특별자치도", addressLocality: R.name, addressCountry: "KR" }, ...(absPhoto2 ? { image: absPhoto2 } : {}) };
  const body = `<nav class="crumb"><a href="${root}">강원 여행 수첩</a> › <a href="${root}region/${R.id}/">${esc(R.name)}</a> › ${esc(p.name)}</nav>
<div class="eyebrow">${esc(p.cat)} · ${esc(R.name)}${p.area ? " " + esc(p.area) : ""}</div><h1>${esc(p.name)}</h1>
${p.sig ? `<p class="lead">${esc(p.sig)}</p>` : ""}
${ph ? `<div class="photo"><img src="${esc(photoUrl)}" alt="${esc(p.name)}" loading="eager" referrerpolicy="no-referrer"><small>${esc(ph.credit || "")}${ph.link ? ` · <a href="${esc(ph.link)}" rel="noopener nofollow">원본</a>` : ""}</small></div>` : ""}
<div class="btns"><a class="btn pri" href="${root}#d-p-${slug(p.id)}">수첩에서 코스에 담기</a>
<a class="btn" href="https://map.kakao.com/link/to/${encodeURIComponent(name1)},${p.lat},${p.lng}" target="_blank" rel="noopener">카카오맵 길찾기</a>
<a class="btn" href="https://map.naver.com/p/search/${encodeURIComponent(q)}" target="_blank" rel="noopener">네이버지도</a></div>
<div class="card"><dl>
${p.hours ? `<dt>운영 시간</dt><dd>${esc(p.hours)}</dd>` : ""}${p.fee ? `<dt>요금</dt><dd>${esc(p.fee)}</dd>` : ""}<dt>휴무</dt><dd>${esc(closedTxt)}</dd>
${bestWho(p) ? `<dt>추천</dt><dd>${esc(bestWho(p))}</dd>` : ""}${p.tags.length ? `<dt>태그</dt><dd class="tags">${p.tags.map(t => `<span>${esc(t)}</span>`).join("")}</dd>` : ""}</dl></div>
${p.tip ? `<h2>여행 팁</h2><div class="card">${esc(p.tip)}</div>` : ""}
${near.length ? `<h2>가까운 곳</h2><ul class="list">${near.map(([d, x]) => `<li><a href="${root}place/${slug(x.id)}/">${esc(x.name)}</a><small>${esc(x.cat)} · 약 ${d < 1 ? Math.round(d * 10) / 10 : Math.round(d)}km</small></li>`).join("")}</ul>` : ""}
${footer(root)}`;
  write(`place/${p.id}/index.html`, shell({ title: `${p.name} | ${R.name} ${p.cat} - 강원 여행 수첩`, desc, canon, body, ld, og: absPhoto2, root }));
  urls.push(canon);
}

// ── 전체 목록과 지역 목록 ──
const listLi = (root, ps) => ps.map(p => `<li><a href="${root}place/${slug(p.id)}/">${esc(p.name)}</a><small>${esc(p.cat)}${p.area ? " · " + esc(p.area) : ""}${p.sig ? " · " + esc(clip(p.sig, 40)) : ""}</small></li>`).join("");
for (const R of REGIONS) {
  const ps = byRegion[R.id] || []; if (!ps.length) continue; const root = "../../", canon = `${SITE}/region/${R.id}/`;
  const cats = [...new Set(ps.map(p => p.cat))];
  const body = `<nav class="crumb"><a href="${root}">강원 여행 수첩</a> › ${esc(R.name)}</nav><h1>${esc(R.name)} 여행 장소 ${ps.length}곳</h1>
<p class="lead">${esc(R.name)}에서 가볼 만한 ${cats.join("·")}를 모았어요. 운영 시간과 휴무, 여행 팁을 확인하고 수첩에서 코스에 담아 보세요.</p>
${cats.map(c => `<h2>${esc(c)}</h2><ul class="list">${listLi(root, ps.filter(p => p.cat === c))}</ul>`).join("")}${footer(root)}`;
  write(`region/${R.id}/index.html`, shell({ title: `${R.name} 가볼 만한 곳 ${ps.length}곳 - 강원 여행 수첩`, desc: `${R.name} 맛집·카페·바다·관광지 ${ps.length}곳. 운영 시간과 휴무, 여행 팁을 한곳에서 확인하세요.`, canon, body, root }));
  urls.push(canon);
}
{
  const root = "../", canon = `${SITE}/place/`;
  const body = `<nav class="crumb"><a href="${root}">강원 여행 수첩</a> › 전체 장소</nav><h1>강원 여행 장소 ${places.length}곳</h1><p class="lead">지역별로 모아 둔 장소 목록이에요.</p>
${REGIONS.filter(R => byRegion[R.id]).map(R => `<h2><a href="${root}region/${R.id}/">${esc(R.name)}</a> (${byRegion[R.id].length})</h2><ul class="list">${listLi(root, byRegion[R.id])}</ul>`).join("")}${footer(root)}`;
  write("place/index.html", shell({ title: `강원 여행 장소 ${places.length}곳 전체 목록 - 강원 여행 수첩`, desc: "강릉·속초·양양·평창 등 강원도 여행 장소를 지역별로 모아 둔 목록입니다.", canon, body, root }));
  urls.unshift(canon);
}
urls.unshift(`${SITE}/`);

// ── 사이트맵·robots ──
const today = new Date().toISOString().slice(0, 10);
write("sitemap.xml", `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.map(u => `<url><loc>${esc(u)}</loc><lastmod>${today}</lastmod></url>`).join("\n")}\n</urlset>\n`);
write("robots.txt", `User-agent: *\nAllow: /\nSitemap: ${SITE}/sitemap.xml\n`);
console.log(`장소 페이지 ${places.length}개, 지역 목록 ${Object.keys(byRegion).length}개, 사이트맵 ${urls.length}건 → ${OUT}`);
