(function(){
var st=document.createElement("style");
st.textContent=".nav-lab{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#8ea0b3;padding:8px 4px 8px 12px;margin-left:2px;border-left:1px solid rgba(243,224,184,.28);white-space:nowrap}";
document.head.appendChild(st);
var nav=document.querySelector("#app .nav") || document.querySelector(".nav");
if(!nav) return;
var keep=[];
[].slice.call(nav.querySelectorAll("#who, #addBtn, button")).forEach(function(el){
  keep.push(el);
});
nav.innerHTML='<a href="index.html">Маршруты</a><a href="hotels.html">Гостиницы</a><span class="nav-lab">Для работников</span><a href="where.html">Кто где</a><a href="team.html">Чат работников</a><a href="radio.html">Рация</a><a href="naryad.html">Наряд</a>';
keep.forEach(function(el){ nav.appendChild(el); });
})();
