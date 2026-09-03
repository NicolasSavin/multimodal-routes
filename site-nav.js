(function(){
var nav=document.querySelector(".nav");
if(!nav) return;
var hotels=nav.querySelector('a[href="hotels.html"]');
if(!hotels || nav.querySelector('a[href="chat.html"]')) return;
var box=document.createElement("div");
box.style.cssText="display:flex;gap:8px;flex-wrap:wrap;align-items:center";
var a=document.createElement("a");
a.href="chat.html";
a.textContent="Помощник";
a.style.cssText=hotels.getAttribute("style")||"";
hotels.parentNode.insertBefore(box, hotels);
box.appendChild(a);
box.appendChild(hotels);
})();
