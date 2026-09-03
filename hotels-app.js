var KEY="mm_user", HKEY="mm_hotels", editI=-1, HERE_API="https://functions.yandexcloud.net/d4e5aa975qllld89nvh0", hereHotel="";
var PHOTOS=["https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=900&q=60"];
var KNOWN=[["екатеринбург","Екатеринбург"],["новосибирск","Новосибирск"],["барнаул","Барнаул"],["бийск","Бийск"],["новоалтайск","Новоалтайск"],["омск","Омск"],["перм","Пермь"],["кунгур","Кунгур"],["москв","Москва"],["петербург","Санкт-Петербург"],["с-петербург","Санкт-Петербург"],["волгоград","Волгоград"],["саратов","Саратов"],["владимир","Владимир"],["муром","Муром"],["коломн","Коломна"],["мурманск","Мурманск"],["северодвинск","Северодвинск"],["йошкар","Йошкар-Ола"],["мамадыш","Мамадыш"],["сызрань","Сызрань"],["барабинск","Барабинск"],["тюкалинск","Тюкалинск"],["очер","Очер"],["тейково","Тейково"],["шахты","Шахты"],["дивеево","Дивеево"],["посад","Сергиев Посад"],["плесецк","Плесецк"],["мирный","Мирный"],["знаменск","Знаменск"],["нижняя тура","Нижняя Тура"],["вязники","Вязники"],["кугеси","Кугеси"],["ярослав","Ярославль"],["исаково","Исаково"],["воротынец","Воротынец"],["дзержин","Дзержинск"],["дружинино","Дружинино"],["менделеев","Менделеевск"],["татарстан","Татарстан"]];
function norm(s){return String(s||"").trim().toLowerCase().replace(/ё/g,"е");}
function cityOf(h){
if(h.c) return h.c;
var t=norm(h.n+" "+(h.a||""));
for(var i=0;i<KNOWN.length;i++) if(t.indexOf(KNOWN[i][0])>=0) return KNOWN[i][1];
var m=String(h.n||"").match(/\(([^)]+)\)/);
if(m) return m[1].replace(/обл\.?/i,"").trim();
return "Другие";
}
function hotels(){
try{var s=localStorage.getItem(HKEY); if(s) return JSON.parse(s);}catch(e){}
return (window.HOTELS||[]).slice();
}
function setHotels(arr){ window.HOTELS=arr; try{localStorage.setItem(HKEY, JSON.stringify(arr));}catch(e){} }
function user(){ try{return JSON.parse(localStorage.getItem(KEY)||"null");}catch(e){return null;} }
function enter(){
var l=norm(document.getElementById("login").value), p=String(document.getElementById("pass").value||"").trim();
var u=(window.HOTEL_USERS||[]).find(function(x){return norm(x.login)===l && String(x.pass)===p;});
if(!u){document.getElementById("err").textContent="Неверный логин или пароль"; return;}
localStorage.setItem(KEY, JSON.stringify({login:u.login, admin:!!u.admin, name:u.name||u.login}));
showApp();
}
function out(){ localStorage.removeItem(KEY); location.reload(); }
function fillCities(){
var sel=document.getElementById("city"), cur=sel.value, set={};
hotels().forEach(function(h){ set[cityOf(h)]=1; });
var names=Object.keys(set).sort(function(a,b){return a.localeCompare(b,"ru");});
sel.innerHTML="<option value=''>Все города</option>"+names.map(function(n){return "<option>"+n+"</option>";}).join("");
if(cur) sel.value=cur;
}
function hereUrl(extra){return HERE_API+"?path=/here"+(extra||"");}
async function loadHere(){
  var el=document.getElementById("hereLine"); if(!el) return;
  try{
    var j=await (await fetch(hereUrl())).json();
    el.innerHTML="<a href='where.html' style='color:#f3e0b8'>Кто где сегодня</a> · на местах "+((j.people||[]).length);
  }catch(e){}
}
async function imHere(){
  var u=user(); if(!u) return;
  var h=hereHotel; if(!h) return;
  try{
    await fetch(hereUrl("&action=set&login="+encodeURIComponent(u.login)+"&name="+encodeURIComponent(u.name)+"&hotel="+encodeURIComponent(h.n)+"&city="+encodeURIComponent(cityOf(h))));
    loadHere();
    fillHereIn(h);
  }catch(e){alert("Не удалось отметить");}
}
function showApp(){
var u=user(); if(!u) return;
document.getElementById("gate").style.display="none";
document.getElementById("app").style.display="block";
document.getElementById("who").textContent=u.name+(u.admin?" · админ":"");
document.getElementById("addBtn").style.display=u.admin?"inline-block":"none";
fillCities(); draw();
}
function rub(n){return Number(n||0).toLocaleString("ru-RU")+" ₽";}
function openHotel(i){
var h=hotels()[i]; if(!h) return;
document.getElementById("hn").textContent=h.n;
document.getElementById("hc").textContent="Город: "+cityOf(h);
document.getElementById("ha").textContent="Адрес: "+(h.a||"не указан");
document.getElementById("ht").innerHTML=h.t?("Телефон: <a href='tel:"+h.t+"' style='color:#f3e0b8'>"+h.t+"</a>"):"Телефон: уточнить";
document.getElementById("hrep").textContent=rub(h.p);
document.getElementById("hstay").textContent=rub(h.s||h.p);
document.getElementById("hp").src=h.img||PHOTOS[0];
var eo=document.getElementById("editOpen");
var adm=user()&&user().admin;
eo.style.display=adm?"inline-block":"none";
eo.onclick=function(){ document.getElementById("m").classList.remove("show"); editHotel(i); };
hereHotel=h;
document.getElementById("hereIn").textContent="Кто здесь: загрузка…";
document.getElementById("m").classList.add("show");
fillHereIn(h);
}
async function fillHereIn(h){
  var el=document.getElementById("hereIn"); if(!el||!h) return;
  try{
    var j=await (await fetch(hereUrl())).json();
    var want=norm(h.n);
    var names=(j.people||[]).filter(function(p){return norm(p.hotel)===want || norm(p.hotel).indexOf(want)>=0 || want.indexOf(norm(p.hotel))>=0;}).map(function(p){return p.name||p.login;});
    el.textContent=names.length?("Сегодня здесь: "+names.join(", ")): "Сегодня здесь никто не отметился";
  }catch(e){el.textContent="";}
}
function editHotel(i){
if(!(user()&&user().admin)) return;
editI=i; var h=i>=0?hotels()[i]:{n:"",a:"",t:"",p:"",s:"",img:"",c:""};
document.getElementById("edTitle").textContent=i>=0?"Правка":"Новая гостиница";
document.getElementById("en").value=h.n||""; document.getElementById("ec").value=h.c||cityOf(h);
document.getElementById("ea").value=h.a||""; document.getElementById("et").value=h.t||"";
document.getElementById("ep").value=h.p||""; document.getElementById("es").value=h.s||h.p||""; document.getElementById("ei").value=h.img||"";
document.getElementById("ed").classList.add("show");
}
function saveHotel(){
var arr=hotels();
var row={n:document.getElementById("en").value.trim(), c:document.getElementById("ec").value.trim(), a:document.getElementById("ea").value.trim(), t:document.getElementById("et").value.trim(), p:+document.getElementById("ep").value||0, s:+document.getElementById("es").value||0, img:document.getElementById("ei").value.trim()};
if(editI>=0) arr[editI]=Object.assign({}, arr[editI], row); else arr.push(row);
setHotels(arr); document.getElementById("ed").classList.remove("show"); fillCities(); draw();
}
function draw(){
var q=norm(document.getElementById("q").value), city=document.getElementById("city").value;
var adm=user()&&user().admin, html="", rows=hotels();
rows.forEach(function(h,i){
var c=cityOf(h);
if(city && c!==city) return;
if(q && norm(h.n+" "+(h.a||"")+" "+c).indexOf(q)<0) return;
html+="<tr><td><button class='name' type='button' onclick='openHotel("+i+")'>"+h.n+"</button></td><td>"+c+"</td><td>"+(h.a||"—")+"</td><td class='price'>"+Number(h.p||0).toLocaleString("ru-RU")+"</td><td>"+(adm?"<button class='btn' type='button' onclick='editHotel("+i+")'>Изменить</button>":"")+"</td></tr>";
});
document.getElementById("tb").innerHTML=html||"<tr><td colspan='5'>Нет совпадений</td></tr>";
}
document.getElementById("q").oninput=draw;
document.getElementById("city").onchange=draw;
if(user()) showApp();
loadHere();
setInterval(loadHere, 30000);
