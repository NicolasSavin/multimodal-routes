const CITIES = (window.CITIES && window.CITIES.length) ? window.CITIES : [
  "Москва","Санкт-Петербург","Казань","Агрыз","Ижевск","Барнаул","Бийск","Екатеринбург","Новосибирск"
];

function setupAutocomplete(input, box) {
  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    if (q.length < 1) { box.classList.add("hidden"); return; }
    const matches = [...new Set(CITIES)].filter(c => c.toLowerCase().includes(q)).slice(0, 15);
    if (!matches.length) { box.classList.add("hidden"); return; }
    box.innerHTML = matches.map(c => `<div class="autocomplete-item px-3 py-2 cursor-pointer text-sm" data-city="${c}">${c}</div>`).join("");
    box.classList.remove("hidden");
  });
  box.addEventListener("click", e => {
    const item = e.target.closest("[data-city]");
    if (item) { input.value = item.dataset.city; box.classList.add("hidden"); }
  });
  document.addEventListener("click", e => {
    if (!input.contains(e.target) && !box.contains(e.target)) box.classList.add("hidden");
  });
}

const fromInput = document.getElementById("fromCity");
const toInput = document.getElementById("toCity");
setupAutocomplete(fromInput, document.getElementById("fromSuggestions"));
setupAutocomplete(toInput, document.getElementById("toSuggestions"));

const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1);
document.getElementById("departDate").valueAsDate = tomorrow;

function generateRoutes(from, to, pax) {
  return [
    {
      id: "train", type: "train", title: "Поезд дальнего следования",
      segments: [{ mode: "train", from, to, dep: "19:30", arr: "08:45+1", duration: "~13ч", train: "Пассажирский", class: "купе / плацкарт" }],
      totalDuration: "~13ч", priceFrom: 2500, priceTo: 7200,
      lowerBerths: true, sameCompartment: true, coupeAvailable: true, seatsAvailable: true, lowerCount: 8, pax
    },
    {
      id: "bus", type: "bus", title: "Прямой автобус",
      segments: [{ mode: "bus", from, to, dep: "08:00", arr: "20:00", duration: "~12ч", carrier: "Междугородний" }],
      totalDuration: "~12ч", priceFrom: 1800, priceTo: 3600,
      lowerBerths: false, sameCompartment: false, coupeAvailable: false, seatsAvailable: true, pax
    },
    {
      id: "multi", type: "multi", title: "Поезд + автобус (пересадка)",
      segments: [
        { mode: "train", from, to: "хаб", dep: "10:00", arr: "16:00", duration: "~6ч", train: "Региональный", class: "плацкарт" },
        { mode: "bus", from: "хаб", to, dep: "18:00", arr: "02:00+1", duration: "~8ч", carrier: "Автобус" }
      ],
      totalDuration: "~16ч", priceFrom: 2800, priceTo: 5200,
      lowerBerths: true, sameCompartment: false, coupeAvailable: false, seatsAvailable: true, lowerCount: 4, transfer: "Пересадка ~2ч", pax
    }
  ];
}

const form = document.getElementById("searchForm");
const loading = document.getElementById("loading");
const results = document.getElementById("results");
const routesList = document.getElementById("routesList");
const emptyState = document.getElementById("emptyState");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const from = fromInput.value.trim();
  const to = toInput.value.trim();
  const date = document.getElementById("departDate").value;
  const pax = parseInt(document.getElementById("passengers").value, 10);
  const mode = document.getElementById("transportMode").value;
  const sameCompartment = document.getElementById("sameCompartment").checked;
  const lowerBerths = document.getElementById("lowerBerths").checked;
  if (!from || !to || !date) return;
  emptyState.classList.add("hidden");
  results.classList.add("hidden");
  loading.classList.remove("hidden");
  await new Promise(r => setTimeout(r, 400));
  let routes = generateRoutes(from, to, pax);
  if (mode === "train") routes = routes.filter(r => r.type === "train");
  if (mode === "bus") routes = routes.filter(r => r.type === "bus");
  if (mode === "multi") routes = routes.filter(r => r.type === "multi");
  if (lowerBerths) routes = routes.filter(r => r.lowerBerths);
  if (sameCompartment && pax >= 2) routes = routes.filter(r => r.sameCompartment && r.coupeAvailable);
  window.__lastRoutes = routes;
  loading.classList.add("hidden");
  renderResults(routes);
});

function renderResults(routes) {
  results.classList.remove("hidden");
  document.getElementById("resultsCount").textContent = routes.length + " вар.";
  if (!routes.length) {
    routesList.innerHTML = '<div class="bg-yellow-50 border border-yellow-200 rounded-xl p-4">По фильтрам ничего нет.</div>';
    return;
  }
  routesList.innerHTML = routes.map(route => {
    const icon = route.type === "train" ? "fa-train" : route.type === "bus" ? "fa-bus" : "fa-exchange-alt";
    const badges = [];
    if (route.lowerBerths) badges.push('<span class="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">Нижние</span>');
    if (route.coupeAvailable) badges.push('<span class="text-xs bg-indigo-100 text-indigo-800 px-2 py-1 rounded-full">Можно одно купе</span>');
    const segs = route.segments.map(s =>
      `<div class="text-sm py-1"><b>${s.dep}</b> ${s.from} → <b>${s.arr}</b> ${s.to}<div class="text-xs text-gray-500">${s.train || s.carrier || ""} · ${s.duration}</div></div>`
    ).join("");
    return `<article class="bg-white border rounded-2xl p-5">
      <div class="flex justify-between gap-3 mb-2">
        <div class="flex gap-3 items-center"><i class="fas ${icon} text-rzd-red"></i>
          <div><h3 class="font-bold">${route.title}</h3><p class="text-sm text-gray-500">${route.totalDuration}</p></div>
        </div>
        <div class="font-bold">${route.priceFrom.toLocaleString("ru-RU")}–${route.priceTo.toLocaleString("ru-RU")} ₽</div>
      </div>
      <div class="flex gap-2 mb-3">${badges.join("")}</div>
      ${segs}
      ${route.transfer ? `<div class="text-sm text-amber-700 bg-amber-50 rounded p-2 mt-2">${route.transfer}</div>` : ""}
      <div class="mt-4 flex gap-2">
        <button type="button" data-action="select" data-id="${route.id}" class="px-4 py-2 bg-rzd-red text-white rounded-lg text-sm">Выбрать</button>
        <button type="button" data-action="details" data-id="${route.id}" class="px-4 py-2 border rounded-lg text-sm">Подробнее / схема мест</button>
      </div>
    </article>`;
  }).join("");
}

function isLower(n) { return n % 2 === 1; }

function buildScheme(route) {
  const pax = route.pax || 1;
  const wantLower = document.getElementById("lowerBerths").checked;
  const wantSame = document.getElementById("sameCompartment").checked && pax >= 2;
  const assigned = [];
  if (route.coupeAvailable) {
    for (let c = 1; c <= 9 && assigned.length < pax; c++) {
      const seats = wantLower ? [c*4-3, c*4-1] : [c*4-3, c*4-1, c*4-2, c*4];
      for (const s of seats) if (assigned.length < pax) assigned.push({ n:s, coupe:c, lower:isLower(s) });
      if (wantSame) break;
    }
  } else if (route.lowerBerths) {
    for (let b = 0; b < 9 && assigned.length < pax; b++) {
      const pool = [b*4+1, b*4+3, b*4+2, b*4+4, 37+b*2, 38+b*2];
      const pick = wantLower ? pool.filter(isLower) : pool;
      for (const s of pick) if (assigned.length < pax) assigned.push({ n:s, coupe:b+1, lower:isLower(s), side:s>=37 });
    }
  }
  let html = "";
  if (assigned.length) {
    html += `<div class="bg-green-50 border border-green-200 rounded-xl p-3 text-sm mb-3"><b>Предложенные места</b><br>` +
      assigned.map(a => `№${a.n} — ${a.lower?"нижняя":"верхняя"}${a.side?" боковая":""} · купе/отсек ${a.coupe}`).join("<br>") + "</div>";
  }
  if (route.coupeAvailable) {
    html += `<p class="text-sm font-medium mb-2">Купейный вагон</p><div class="grid grid-cols-3 gap-2">`;
    for (let c = 1; c <= 9; c++) {
      const seats = [c*4-3, c*4-2, c*4-1, c*4];
      html += `<div class="border rounded-xl p-2 ${assigned.some(a=>a.coupe===c)?"border-red-500 bg-red-50":""}"><div class="text-xs text-gray-500">Купе ${c}</div><div class="grid grid-cols-2 gap-1 text-xs mt-1">`;
      seats.forEach(n => {
        const on = assigned.some(a=>a.n===n);
        html += `<div class="px-1 py-1 rounded text-center ${on?"bg-red-600 text-white":isLower(n)?"bg-green-100":"bg-gray-100"}">${n}${isLower(n)?"↓":"↑"}</div>`;
      });
      html += `</div></div>`;
    }
    html += `</div>`;
  } else if (route.lowerBerths) {
    html += `<p class="text-sm font-medium mb-2">Плацкарт · нечёт = низ</p><div class="overflow-x-auto text-xs"><table class="w-full"><tr class="text-gray-500"><th>Отс.</th><th>Н</th><th>В</th><th>Н</th><th>В</th><th>Бок↓</th><th>Бок↑</th></tr>`;
    for (let b = 0; b < 9; b++) {
      const nums = [b*4+1,b*4+2,b*4+3,b*4+4,37+b*2,38+b*2];
      html += `<tr class="border-t"><td class="p-1">${b+1}</td>` + nums.map(n => {
        const on = assigned.some(a=>a.n===n);
        return `<td class="p-1"><span class="px-1 rounded ${on?"bg-red-600 text-white":n%2?"bg-green-100":"bg-gray-100"}">${n}</span></td>`;
      }).join("") + "</tr>";
    }
    html += `</table></div>`;
  } else {
    html += `<p class="text-sm mb-2">Сидячие места</p><div class="grid grid-cols-4 gap-2 text-xs">`;
    for (let n = 1; n <= 16; n++) html += `<div class="p-2 rounded text-center ${n<=pax?"bg-red-600 text-white":"bg-gray-100"}">${n}</div>`;
    html += `</div>`;
  }
  return html;
}

function openModal(route, mode) {
  document.getElementById("modalTitle").textContent = mode === "select" ? "Выбранный вариант" : "Схема мест";
  document.getElementById("modalSub").textContent = route.title + " · " + route.totalDuration;
  const info = [];
  if (route.lowerBerths) info.push("Нижние полки: нечётные номера.");
  if (route.coupeAvailable) info.push("Можно посадить компанию в одно купе.");
  if (route.type === "bus") info.push("Автобус: купе нет.");
  if (route.transfer) info.push(route.transfer);
  document.getElementById("modalInfo").innerHTML = info.join("<br>") || "Обычный рейс.";
  document.getElementById("modalScheme").innerHTML = buildScheme(route);
  document.getElementById("seatModal").classList.remove("hidden");
}

document.getElementById("routesList").addEventListener("click", e => {
  const btn = e.target.closest("[data-action]");
  if (!btn) return;
  const route = (window.__lastRoutes || []).find(r => r.id === btn.dataset.id);
  if (!route) return;
  openModal(route, btn.dataset.action);
});
document.getElementById("modalClose").addEventListener("click", () => document.getElementById("seatModal").classList.add("hidden"));
document.getElementById("seatModal").addEventListener("click", e => { if (e.target.id === "seatModal") e.target.classList.add("hidden"); });
