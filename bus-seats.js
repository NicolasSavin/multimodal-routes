function slugCity(s){
var t=String(s||"").toLowerCase().replace(/ё/g,"е");
var m=[["новосибирск","Novosibirsk"],["барнаул","Barnaul"],["ижевск","Izhevsk"],["агрыз","Agryz"],["екатеринбург","Ekaterinburg"],["казань","Kazan"],["омск","Omsk"],["перм","Perm"],["москв","Moscow"],["бийск","Biysk"]];
for(var i=0;i<m.length;i++) if(t.indexOf(m[i][0])>=0) return m[i][1];
return encodeURIComponent(String(s||"").split(",")[0].trim());
}
function busBtns(x){
var legs=(x.details||[]).filter(function(p){return /bus|авто/.test(String(p.type||""));});
if(!legs.length && (x.type==="bus" || (typeof isBus==="function" && isBus(x)))) legs=[{from:x.from,to:x.to}];
if(!legs.length){
legs=[{from:(x.hub||"Новосибирск"), to:x.to}];
}
var p=legs[0];
var a=slugCity(p.from||x.from), b=slugCity(p.to||x.to);
var tutu="https://bus.tutu.ru/bilety_na_avtobus/"+a+"/"+b+"/";
return "<div class='row' style='margin-top:8px'><a class='mapbtn' style='text-decoration:none' target='_blank' rel='noopener' href='"+tutu+"'>Места Туту</a><a class='mapbtn' style='text-decoration:none' target='_blank' rel='noopener' href='https://busfor.ru/'>Места Busfor</a></div>";
}
(function(){
if(typeof card!=="function") return;
var orig=card;
card=function(x,i){
var html=orig(x,i);
if(typeof isBus==="function" && typeof isMix==="function" && (isBus(x)||isMix(x))){
if(html.indexOf("Места Туту")<0) html=html.replace("</article>", busBtns(x)+"</article>");
}
return html;
};
})();
