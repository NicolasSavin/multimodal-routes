(function(){
var API="https://functions.yandexcloud.net/d4e5aa975qllld89nvh0";
var sirenCtx=null, sirenNodes=[], sosOn=false, lastSosTs=0, localMute=false, sirenLoop=null;
function user(){ try{return JSON.parse(localStorage.getItem("mm_user")||"null");}catch(e){return null;} }
function api(path){ return API+"?path="+path; }
function stopSiren(){
  if(sirenLoop){ clearInterval(sirenLoop); sirenLoop=null; }
  sirenNodes.forEach(function(n){ try{n.stop();}catch(e){} });
  sirenNodes=[];
  if(sirenCtx){ try{sirenCtx.close();}catch(e){} sirenCtx=null; }
}
function burst(){
  var Ctx=window.AudioContext||window.webkitAudioContext; if(!Ctx) return;
  if(!sirenCtx || sirenCtx.state==="closed") sirenCtx=new Ctx();
  if(sirenCtx.state==="suspended") sirenCtx.resume();
  var t=sirenCtx.currentTime;
  for(var i=0;i<24;i++){
    var o=sirenCtx.createOscillator(), g=sirenCtx.createGain();
    o.type="sawtooth";
    o.frequency.setValueAtTime(i%2?920:480, t+i*0.28);
    g.gain.setValueAtTime(0.0001, t+i*0.28);
    g.gain.exponentialRampToValueAtTime(0.2, t+i*0.28+0.04);
    g.gain.exponentialRampToValueAtTime(0.0001, t+i*0.28+0.26);
    o.connect(g); g.connect(sirenCtx.destination);
    o.start(t+i*0.28); o.stop(t+i*0.28+0.27);
    sirenNodes.push(o);
  }
}
function playSiren(){
  stopSiren();
  burst();
  sirenLoop=setInterval(function(){
    if(!sosOn || localMute){ stopSiren(); return; }
    burst();
  }, 7000);
}
function ensureUi(){
  if(!user()) return;
  if(document.getElementById("sosBtn")) return;
  var st=document.createElement("style");
  st.textContent="#sosBtn{position:fixed;right:16px;bottom:16px;z-index:80;border:0;border-radius:999px;padding:14px 18px;font:700 14px Manrope,system-ui;color:#fff;background:linear-gradient(180deg,#ff4d4d,#9b1010);box-shadow:0 10px 30px rgba(180,0,0,.45);cursor:pointer}#sosMask{display:none;position:fixed;inset:0;z-index:90;background:rgba(120,0,0,.88);color:#fff;align-items:center;justify-content:center;text-align:center;padding:24px}#sosMask.show{display:flex;animation:sosPulse 1s infinite}#sosMask .box{max-width:520px}#sosMask h2{font-size:42px;margin:0 0 8px;letter-spacing:.08em}#sosMask button{margin:8px;padding:12px 16px;border-radius:999px;border:0;font:700 14px Manrope,system-ui;cursor:pointer}@keyframes sosPulse{0%,100%{background:rgba(140,0,0,.92)}50%{background:rgba(220,20,20,.92)}}";
  document.head.appendChild(st);
  var b=document.createElement("button");
  b.id="sosBtn"; b.type="button"; b.textContent="SOS \u00b7 Тревога";
  b.onclick=function(){ sendSos(); };
  document.body.appendChild(b);
  var m=document.createElement("div");
  m.id="sosMask";
  m.innerHTML="<div class='box'><h2>ТРЕВОГА</h2><p id='sosWho'></p><p>Сигнал идёт, пока его не снимут.</p><button type='button' id='sosMute'>Выключить звук у себя</button><button type='button' id='sosOff'>Снять тревогу у всех</button></div>";
  document.body.appendChild(m);
  document.getElementById("sosMute").onclick=function(){ localMute=true; stopSiren(); };
  document.getElementById("sosOff").onclick=function(){ clearSos(); };
}
function showSos(row){
  ensureUi();
  var mask=document.getElementById("sosMask");
  if(!mask) return;
  document.getElementById("sosWho").textContent=(row.name||row.login||"Сотрудник")+" \u00b7 "+(row.note||"нажал SOS");
  mask.classList.add("show");
  if(!localMute) playSiren();
}
function hideSos(){
  var mask=document.getElementById("sosMask");
  if(mask) mask.classList.remove("show");
  stopSiren();
  sosOn=false;
}
async function pollSos(){
  if(!user()) return;
  ensureUi();
  try{
    var j=await (await fetch(api("/sos"))).json();
    var row=j.sos;
    if(row && row.on){
      if(!sosOn || row.ts!==lastSosTs){ lastSosTs=row.ts; localMute=false; showSos(row); }
      sosOn=true;
    } else if(sosOn){ hideSos(); }
  }catch(e){}
}
async function sendSos(){
  var u=user();
  if(!u){ location.href="team.html"; return; }
  var note=prompt("Тревога. Коротко что случилось (можно пусто):","")||"";
  try{
    await fetch(api("/sos")+"&action=set&login="+encodeURIComponent(u.login)+"&name="+encodeURIComponent(u.name||u.login)+"&note="+encodeURIComponent(note));
    pollSos();
  }catch(e){ alert("Не удалось отправить SOS."); }
}
async function clearSos(){
  var u=user()||{login:"guest"};
  try{ await fetch(api("/sos")+"&action=clear&login="+encodeURIComponent(u.login)); }catch(e){}
  hideSos();
}
ensureUi();
pollSos();
setInterval(function(){ if(user()){ ensureUi(); pollSos(); } }, 4000);
window.NTC_SOS={pollSos:pollSos,sendSos:sendSos,clearSos:clearSos,api:api,user:user};
})();
