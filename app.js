// ===== Данные городов =====
const CITIES = [
  "Москва", "Санкт-Петербург", "Казань", "Нижний Новгород", "Екатеринбург",
  "Новосибирск", "Сочи", "Краснодар", "Самара", "Ростов-на-Дону",
  "Воронеж", "Пермь", "Уфа", "Челябинск", "Волгоград",
  "Калининград", "Владивосток", "Иркутск", "Тюмень", "Ярославль",
  "Владимир", "Тверь", "Тула", "Рязань", "Брянск",
  "Омск", "Томск", "Барнаул", "Хабаровск", "Мурманск"
];

// ===== Моковые маршруты (шаблоны) =====
// Для реалистичности: прямые поезда, прямые автобусы, мультимодальные с пересадкой
const ROUTE_TEMPLATES = {
  "Москва|Санкт-Петербург": [
    {
      id: "msp-sapsan",
      type: "train",
      title: "Сапсан",
      segments: [
        { mode: "train", from: "Москва (Ленинградский)", to: "Санкт-Петербург (Московский)", dep: "06:40", arr: "10:25", duration: "3ч 45м", train: "Сапсан 751А", class: "сидячий" }
      ],
      totalDuration: "3ч 45м",
      priceFrom: 4200,
      priceTo: 8900,
      lowerBerths: false, // сидячий
      sameCompartment: false,
      seatsAvailable: true,
      note: "Скоростной, места сидячие"
    },
    {
      id: "msp-night",
      type: "train",
      title: "Ночной поезд",
      segments: [
        { mode: "train", from: "Москва (Ленинградский)", to: "Санкт-Петербург (Московский)", dep: "23:40", arr: "08:15", duration: "8ч 35м", train: "016А «Арктика»", class: "купе / плацкарт" }
      ],
      totalDuration: "8ч 35м",
      priceFrom: 2100,
      priceTo: 6500,
      lowerBerths: true,
      sameCompartment: true,
      seatsAvailable: true,
      lowerCount: 12,
      coupeAvailable: true
    },
    {
      id: "msp-bus",
      type: "bus",
      title: "Прямой автобус",
      segments: [
        { mode: "bus", from: "Москва (Щёлковский АВ)", to: "Санкт-Петербург (Обводный канал)", dep: "21:30", arr: "07:45", duration: "10ч 15м", carrier: "Ecolines / ПИК" }
      ],
      totalDuration: "10ч 15м",
      priceFrom: 1800,
      priceTo: 3200,
      lowerBerths: false,
      sameCompartment: false,
      seatsAvailable: true
    },
    {
      id: "msp-multi",
      type: "multi",
      title: "Поезд + автобус через Тверь",
      segments: [
        { mode: "train", from: "Москва (Ленинградский)", to: "Тверь", dep: "14:20", arr: "16:05", duration: "1ч 45м", train: "Ласточка", class: "сидячий" },
        { mode: "bus", from: "Тверь (АВ)", to: "Санкт-Петербург", dep: "17:30", arr: "23:50", duration: "6ч 20м", carrier: "Региональный" }
      ],
      totalDuration: "9ч 30м",
      priceFrom: 2400,
      priceTo: 4100,
      lowerBerths: false,
      sameCompartment: false,
      seatsAvailable: true,
      transfer: "Тверь · 1ч 25м ожидания"
    }
  ],
  "Москва|Казань": [
    {
      id: "mk-direct",
      type: "train",
      title: "Прямой поезд",
      segments: [
        { mode: "train", from: "Москва (Казанский)", to: "Казань (Казань-Пасс)", dep: "20:08", arr: "08:15", duration: "12ч 07м", train: "002Й «Татарстан»", class: "купе / плацкарт" }
      ],
      totalDuration: "12ч 07м",
      priceFrom: 2800,
      priceTo: 7800,
      lowerBerths: true,
      sameCompartment: true,
      seatsAvailable: true,
      lowerCount: 8,
      coupeAvailable: true
    },
    {
      id: "mk-day",
      type: "train",
      title: "Дневной поезд",
      segments: [
        { mode: "train", from: "Москва (Казанский)", to: "Казань", dep: "08:15", arr: "19:40", duration: "11ч 25м", train: "022Г", class: "купе" }
      ],
      totalDuration: "11ч 25м",
      priceFrom: 3500,
      priceTo: 9200,
      lowerBerths: true,
      sameCompartment: true,
      seatsAvailable: true,
      lowerCount: 4,
      coupeAvailable: true
    },
    {
      id: "mk-bus",
      type: "bus",
      title: "Автобус по М-12",
      segments: [
        { mode: "bus", from: "Москва (Центральный АВ)", to: "Казань (Южный АВ)", dep: "07:00", arr: "15:30", duration: "8ч 30м", carrier: "Автобусные линии" }
      ],
      totalDuration: "8ч 30м",
      priceFrom: 2200,
      priceTo: 3800,
      lowerBerths: false,
      sameCompartment: false,
      seatsAvailable: true
    },
    {
      id: "mk-multi",
      type: "multi",
      title: "Поезд до Н.Новгорода + автобус",
      segments: [
        { mode: "train", from: "Москва (Ярославский)", to: "Нижний Новгород", dep: "06:45", arr: "10:20", duration: "3ч 35м", train: "Стриж / Ласточка", class: "сидячий" },
        { mode: "bus", from: "Н.Новгород (Щербинки)", to: "Казань", dep: "11:40", arr: "16:50", duration: "5ч 10м", carrier: "РегионТранс" }
      ],
      totalDuration: "10ч 05м",
      priceFrom: 2600,
      priceTo: 4500,
      lowerBerths: false,
      sameCompartment: false,
      seatsAvailable: true,
      transfer: "Нижний Новгород · 1ч 20м"
    }
  ],
  "Санкт-Петербург|Казань": [
    {
      id: "spk-train",
      type: "train",
      title: "Поезд с пересадкой в Москве",
      segments: [
        { mode: "train", from: "СПб (Московский)", to: "Москва (Ленинградский)", dep: "07:00", arr: "10:50", duration: "3ч 50м", train: "Сапсан", class: "сидячий" },
        { mode: "train", from: "Москва (Казанский)", to: "Казань", dep: "13:40", arr: "01:15+1", duration: "11ч 35м", train: "002Й", class: "купе / плацкарт" }
      ],
      totalDuration: "18ч 15м",
      priceFrom: 6200,
      priceTo: 14500,
      lowerBerths: true,
      sameCompartment: true,
      seatsAvailable: true,
      lowerCount: 6,
      coupeAvailable: true,
      transfer: "Москва · ~2ч 50м (переезд между вокзалами)"
    },
    {
      id: "spk-bus",
      type: "bus",
      title: "Прямой автобус",
      segments: [
        { mode: "bus", from: "СПб (Обводный)", to: "Казань", dep: "18:00", arr: "12:30+1", duration: "18ч 30м", carrier: "Междугородние линии" }
      ],
      totalDuration: "18ч 30м",
      priceFrom: 3500,
      priceTo: 5200,
      lowerBerths: false,
      sameCompartment: false,
      seatsAvailable: true
    },
    {
      id: "spk-multi",
      type: "multi",
      title: "Поезд до Москвы + автобус",
      segments: [
        { mode: "train", from: "СПб", to: "Москва", dep: "22:30", arr: "06:40", duration: "8ч 10м", train: "Ночной", class: "плацкарт" },
        { mode: "bus", from: "Москва", to: "Казань", dep: "09:00", arr: "17:30", duration: "8ч 30м", carrier: "Авто" }
      ],
      totalDuration: "19ч 00м",
      priceFrom: 4100,
      priceTo: 6800,
      lowerBerths: true,
      sameCompartment: false,
      seatsAvailable: true,
      lowerCount: 9,
      transfer: "Москва · 2ч 20м"
    }
  ],
  "Москва|Сочи": [
    {
      id: "ms-train",
      type: "train",
      title: "Прямой поезд",
      segments: [
        { mode: "train", from: "Москва (Казанский)", to: "Сочи", dep: "10:20", arr: "16:45+1", duration: "30ч 25м", train: "102С", class: "купе / плацкарт / СВ" }
      ],
      totalDuration: "30ч 25м",
      priceFrom: 4500,
      priceTo: 18000,
      lowerBerths: true,
      sameCompartment: true,
      seatsAvailable: true,
      lowerCount: 15,
      coupeAvailable: true
    },
    {
      id: "ms-bus",
      type: "bus",
      title: "Автобус",
      segments: [
        { mode: "bus", from: "Москва", to: "Сочи", dep: "12:00", arr: "10:00+1", duration: "22ч", carrier: "ЮгТранс" }
      ],
      totalDuration: "22ч",
      priceFrom: 3800,
      priceTo: 5500,
      lowerBerths: false,
      sameCompartment: false,
      seatsAvailable: true
    },
    {
      id: "ms-multi",
      type: "multi",
      title: "Поезд до Краснодара + автобус",
      segments: [
        { mode: "train", from: "Москва", to: "Краснодар", dep: "18:40", arr: "14:20+1", duration: "19ч 40м", train: "Поезд дальнего следования", class: "купе" },
        { mode: "bus", from: "Краснодар", to: "Сочи", dep: "16:00", arr: "21:30", duration: "5ч 30м", carrier: "Кубань" }
      ],
      totalDuration: "26ч 50м",
      priceFrom: 4200,
      priceTo: 9500,
      lowerBerths: true,
      sameCompartment: true,
      seatsAvailable: true,
      lowerCount: 7,
      coupeAvailable: true,
      transfer: "Краснодар · 1ч 40м"
    }
  ]
};

// Fallback генератор для неизвестных пар
function generateGenericRoutes(from, to) {
  return [
    {
      id: "gen-train",
      type: "train",
      title: "Прямой поезд (расписание)",
      segments: [
        { mode: "train", from, to, dep: "19:30", arr: "08:45+1", duration: "~13ч", train: "Поезд дальнего следования", class: "купе / плацкарт" }
      ],
      totalDuration: "~13ч",
      priceFrom: 2500,
      priceTo: 7000,
      lowerBerths: true,
      sameCompartment: true,
      seatsAvailable: true,
      lowerCount: 5,
      coupeAvailable: true
    },
    {
      id: "gen-bus",
      type: "bus",
      title: "Прямой автобус",
      segments: [
        { mode: "bus", from, to, dep: "08:00", arr: "20:00", duration: "~12ч", carrier: "Междугородний" }
      ],
      totalDuration: "~12ч",
      priceFrom: 1800,
      priceTo: 3500,
      lowerBerths: false,
      sameCompartment: false,
      seatsAvailable: true
    },
    {
      id: "gen-multi",
      type: "multi",
      title: "Мультимодальный (через крупный хаб)",
      segments: [
        { mode: "train", from, to: "Москва / СПб (хаб)", dep: "10:00", arr: "16:00", duration: "~6ч", train: "Региональный", class: "сидячий / плацкарт" },
        { mode: "bus", from: "Хаб", to, dep: "18:00", arr: "02:00+1", duration: "~8ч", carrier: "Автобус" }
      ],
      totalDuration: "~16ч",
      priceFrom: 2800,
      priceTo: 5200,
      lowerBerths: true,
      sameCompartment: false,
      seatsAvailable: true,
      lowerCount: 3,
      transfer: "Пересадка в хабе · 2ч"
    }
  ];
}

// ===== UI helpers =====
const fromInput = document.getElementById("fromCity");
const toInput = document.getElementById("toCity");
const fromSug = document.getElementById("fromSuggestions");
const toSug = document.getElementById("toSuggestions");
const form = document.getElementById("searchForm");
const loading = document.getElementById("loading");
const results = document.getElementById("results");
const routesList = document.getElementById("routesList");
const resultsCount = document.getElementById("resultsCount");
const emptyState = document.getElementById("emptyState");

function setupAutocomplete(input, sugBox) {
  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    if (q.length < 1) {
      sugBox.classList.add("hidden");
      return;
    }
    const matches = CITIES.filter(c => c.toLowerCase().includes(q)).slice(0, 8);
    if (matches.length === 0) {
      sugBox.classList.add("hidden");
      return;
    }
    sugBox.innerHTML = matches.map(c =>
      `<div class="autocomplete-item px-4 py-2.5 cursor-pointer text-sm" data-city="${c}">${c}</div>`
    ).join("");
    sugBox.classList.remove("hidden");
  });

  sugBox.addEventListener("click", (e) => {
    const item = e.target.closest("[data-city]");
    if (item) {
      input.value = item.dataset.city;
      sugBox.classList.add("hidden");
    }
  });

  document.addEventListener("click", (e) => {
    if (!input.contains(e.target) && !sugBox.contains(e.target)) {
      sugBox.classList.add("hidden");
    }
  });
}

setupAutocomplete(fromInput, fromSug);
setupAutocomplete(toInput, toSug);

// Дата по умолчанию — завтра
const tomorrow = new Date();
tomorrow.setDate(tomorrow.getDate() + 1);
document.getElementById("departDate").valueAsDate = tomorrow;

// Быстрые маршруты
document.querySelectorAll(".quick-route").forEach(btn => {
  btn.addEventListener("click", () => {
    fromInput.value = btn.dataset.from;
    toInput.value = btn.dataset.to;
    form.dispatchEvent(new Event("submit"));
  });
});

// ===== Поиск =====
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

  // Имитация задержки сети
  await new Promise(r => setTimeout(r, 900 + Math.random() * 600));

  // Нормализация названий городов
  const normalize = (s) => {
    const base = s.split(",")[0].trim().toLowerCase();
    if (base.includes("санкт") || base.includes("петербург") || base === "спб") return "Санкт-Петербург";
    if (base.includes("москв")) return "Москва";
    if (base.includes("казан")) return "Казань";
    if (base.includes("сочи")) return "Сочи";
    // Возвращаем оригинальное с заглавной
    return s.split(",")[0].trim();
  };
  const fromN = normalize(from);
  const toN = normalize(to);
  const key = `${fromN}|${toN}`;
  const reverseKey = `${toN}|${fromN}`;
  let routes = ROUTE_TEMPLATES[key] || ROUTE_TEMPLATES[reverseKey] || generateGenericRoutes(fromN, toN);

  // Фильтр по режиму
  if (mode === "train") routes = routes.filter(r => r.type === "train");
  else if (mode === "bus") routes = routes.filter(r => r.type === "bus");
  else if (mode === "multi") routes = routes.filter(r => r.type === "multi");

  // Опциональные фильтры мест
  if (lowerBerths) {
    routes = routes.filter(r => r.lowerBerths === true);
  }
  if (sameCompartment && pax >= 2) {
    routes = routes.filter(r => r.sameCompartment === true && r.coupeAvailable);
  }

  // Небольшая вариация цен от даты и пассажиров
  routes = routes.map(r => {
    const dayFactor = 1 + (new Date(date).getDay() % 3) * 0.08;
    const paxFactor = 1 + (pax - 1) * 0.02;
    return {
      ...r,
      priceFrom: Math.round(r.priceFrom * dayFactor * paxFactor),
      priceTo: Math.round(r.priceTo * dayFactor * paxFactor),
      pax
    };
  });

  loading.classList.add("hidden");
  renderResults(routes, from, to, date, sameCompartment, lowerBerths);
});

function renderResults(routes, from, to, date, sameComp, lowerOnly) {
  if (routes.length === 0) {
    results.classList.remove("hidden");
    routesList.innerHTML = `
      <div class="bg-yellow-50 border border-yellow-200 rounded-xl p-6 text-center">
        <i class="fas fa-exclamation-triangle text-yellow-500 text-2xl mb-2"></i>
        <p class="font-medium text-gray-800">По выбранным фильтрам маршрутов не найдено</p>
        <p class="text-sm text-gray-600 mt-1">Попробуйте отключить «места в одном купе» или «только нижние полки», либо выбрать другие даты / города.</p>
      </div>`;
    resultsCount.textContent = "0 вариантов";
    return;
  }

  results.classList.remove("hidden");
  resultsCount.textContent = `${routes.length} вариант${routes.length === 1 ? "" : routes.length < 5 ? "а" : "ов"}`;

  routesList.innerHTML = routes.map(route => {
    const typeIcon = route.type === "train" ? "fa-train" : route.type === "bus" ? "fa-bus" : "fa-exchange-alt";
    const typeColor = route.type === "train" ? "text-rzd-red" : route.type === "bus" ? "text-blue-600" : "text-purple-600";
    const typeBg = route.type === "train" ? "bg-red-50" : route.type === "bus" ? "bg-blue-50" : "bg-purple-50";
    const typeLabel = route.type === "train" ? "Поезд" : route.type === "bus" ? "Автобус" : "Мультимодальный";

    const badges = [];
    if (route.lowerBerths) {
      badges.push(`<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
        <i class="fas fa-bed"></i> Нижние полки${route.lowerCount ? ` (${route.lowerCount}+)` : ""}
      </span>`);
    }
    if (route.sameCompartment && route.coupeAvailable) {
      badges.push(`<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
        <i class="fas fa-door-closed"></i> Можно в одном купе
      </span>`);
    }
    if (route.seatsAvailable) {
      badges.push(`<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
        <i class="fas fa-check"></i> Места есть
      </span>`);
    }

    const segmentsHtml = route.segments.map((seg, idx) => {
      const icon = seg.mode === "train" ? "fa-train text-rzd-red" : "fa-bus text-blue-600";
      const isLast = idx === route.segments.length - 1;
      return `
        <div class="flex gap-3">
          <div class="flex flex-col items-center">
            <div class="w-8 h-8 rounded-full ${seg.mode === "train" ? "bg-red-100" : "bg-blue-100"} flex items-center justify-center">
              <i class="fas ${icon} text-sm"></i>
            </div>
            ${!isLast ? '<div class="w-0.5 flex-1 timeline-line my-1 min-h-[24px]"></div>' : ""}
          </div>
          <div class="pb-4 flex-1">
            <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span class="font-semibold text-gray-900">${seg.dep}</span>
              <span class="text-sm text-gray-600">${seg.from}</span>
            </div>
            <div class="text-xs text-gray-500 mt-0.5">
              ${seg.mode === "train" ? `${seg.train} · ${seg.class}` : seg.carrier} · ${seg.duration}
            </div>
            <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1 mt-1">
              <span class="font-semibold text-gray-900">${seg.arr}</span>
              <span class="text-sm text-gray-600">${seg.to}</span>
            </div>
          </div>
        </div>
      `;
    }).join("");

    return `
      <article class="bg-white rounded-2xl border border-gray-200 shadow-sm card-hover transition-all duration-300 overflow-hidden">
        <div class="p-5 md:p-6">
          <div class="flex flex-wrap items-start justify-between gap-3 mb-4">
            <div class="flex items-center gap-3">
              <div class="w-11 h-11 ${typeBg} rounded-xl flex items-center justify-center">
                <i class="fas ${typeIcon} ${typeColor} text-lg"></i>
              </div>
              <div>
                <h3 class="font-bold text-lg text-gray-900">${route.title}</h3>
                <p class="text-sm text-gray-500">${typeLabel} · ${route.totalDuration}</p>
              </div>
            </div>
            <div class="text-right">
              <div class="text-xl font-bold text-gray-900">${route.priceFrom.toLocaleString("ru-RU")} – ${route.priceTo.toLocaleString("ru-RU")} ₽</div>
              <div class="text-xs text-gray-500">на ${route.pax} пасс.</div>
            </div>
          </div>

          ${badges.length ? `<div class="flex flex-wrap gap-2 mb-4">${badges.join("")}</div>` : ""}

          <div class="border-t border-gray-100 pt-4">
            ${segmentsHtml}
          </div>

          ${route.transfer ? `
            <div class="mt-2 flex items-center gap-2 text-sm text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
              <i class="fas fa-clock"></i>
              Пересадка: ${route.transfer}
            </div>
          ` : ""}

          <div class="mt-4 flex flex-wrap gap-2">
            <button class="px-4 py-2 bg-rzd-red text-white text-sm font-medium rounded-lg hover:bg-red-700 transition">
              Выбрать
            </button>
            <button class="px-4 py-2 border border-gray-300 text-sm font-medium rounded-lg hover:bg-gray-50 transition">
              Подробнее
            </button>
          </div>
        </div>
      </article>
    `;
  }).join("");
}

// Небольшая подсказка в консоль
console.log("%cМультиМаршрут demo", "color:#E31E24;font-weight:bold;font-size:14px");
console.log("Фильтры «одно купе» и «нижние полки» работают на демо-данных. В продакшене — через API вагонов РЖД.");
