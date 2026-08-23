function slugCity(s){
var t=String(s||"").toLowerCase().replace(/ё/g,"е");
var m=[["новосибирск","Novosibirsk"],["барнаул","Barnaul"],["ижевск","Izhevsk"],["агрыз","Agryz"],["екатеринбург","Ekaterinburg"],["казань","Kazan"],["омск","Omsk"],["перм","Perm"],["москв","Moscow"],["санкт","Sankt-Peterburg"],["петербург","Sankt-Peterburg"],["бийск","Biysk"]];
for(var i=0;i<m.length;i++) if(t.indexOf(m[i][0])>=0) return m[i][1];
return encodeURIComponent(String(s||"").split(",")[0].trim());
}
function cityOnly(s){return String(s||"").split(",")[0].replace(/автовокзал.*|ж\/\u0434.*|станция.*/i,"").trim();}
function busBtns(x){
var legs=(x.details||[]).filter(function(p){return /bus|авто/.test(String(p.type||""));});
if(!legs.length && (x.type==="bus" || (typeof isBus==="function" && isBus(x)))) legs=[{from:x.from,to:x.to}];
if(!legs.length) legs=[{from:(x.hub||"Новосибирск"), to:x.to}];
var p=legs[0];
var a=slugCity(p.from||x.from), b=slugCity(p.to||x.to);
var tutu="https://bus.tutu.ru/bilety_na_avtobus/"+a+"/"+b+"/";
return "<div class='row' style='margin-top:8px'><a class='mapbtn' style='text-decoration:none' target='_blank' rel='noopener' href='"+tutu+"'>Места Туту</a><a class='mapbtn' style='text-decoration:none' target='_blank' rel='noopener' href='https://busfor.ru/'>Места Busfor</a></div>";
}
function rzdUrl(x){
var fr=cityOnly((typeof lastQ!=="undefined" && lastQ.fr) || x.from || "");
var to=cityOnly((typeof lastQ!=="undefined" && lastQ.to) || x.to || "");
var d=(typeof lastQ!=="undefined" && lastQ.date) || "";
var dt=d && d.indexOf("-")>=0 ? d.split("-").reverse().join(".") : d;
var num=encodeURIComponent(x.number||"");
return "https://pass.rzd.ru/tickets/public/ru?STRUCTURE_ID=735&layer_id=5371&dir=0&tfl=3&checkSeats=1&st0="+encodeURIComponent(fr)+"&st1="+encodeURIComponent(to)+"&dt0="+encodeURIComponent(dt)+(num?("&tn="+num):"");
}
function rzdBtn(x){
return "<a class='mapbtn' style='text-decoration:none;margin-left:8px' target='_blank' rel='noopener' href='"+rzdUrl(x)+"'>Открыть в РЖД</a>";
}
(function(){
if(typeof card!=="function") return;
var orig=card;
card=function(x,i){
var html=orig(x,i);
var bus=typeof isBus==="function" && isBus(x);
var mix=typeof isMix==="function" && isMix(x);
var sap=typeof isSap==="function" && isSap(x);
if((bus||mix) && html.indexOf("Места Туту")<0) html=html.replace("</article>", busBtns(x)+"</article>");
if(!bus || mix || sap || x.type==="train") html=html.replace("</article>", rzdBtn(x)+"</article>");
return html;
};
})();
