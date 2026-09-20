(function(){
var nav=document.querySelector(".nav");
if(!nav) return;
var hotels=nav.querySelector('a[href="hotels.html"]');
if(!hotels) return;
if(!nav.querySelector('a[href="chat.html"]')){
  var a=document.createElement("a");
  a.href="chat.html";
  a.textContent="ИИ помощник";
  a.className="ai";
  hotels.parentNode.insertBefore(a, hotels);
}
var staff=nav.querySelector('a[href="team.html"]');
if(staff && staff.textContent.indexOf("работник")<0) staff.textContent="Чат работников";
if(staff && !nav.querySelector('a[href="radio.html"]')){
  var r=document.createElement("a");
  r.href="radio.html";
  r.textContent="Рация";
  staff.parentNode.insertBefore(r, staff.nextSibling);
}
if(!nav.querySelector('a[href="naryad.html"]') && nav.querySelector('a[href="radio.html"], a[href="team.html"]')){
  var n=document.createElement("a");
  n.href="naryad.html";
  n.textContent="Наряд";
  var after=nav.querySelector('a[href="radio.html"]')||staff;
  after.parentNode.insertBefore(n, after.nextSibling);
}
})();
