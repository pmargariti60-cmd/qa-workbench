const candidate = new URLSearchParams(location.search).get("build") === "candidate";
const subtotal = 5000;
const shipping = 500;
const promoDiscount = 500;
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

const build = document.querySelector("#build");
const form = document.querySelector("#promo");
const code = document.querySelector("#code");
const discount = document.querySelector("#discount");
const total = document.querySelector("#total");
const message = document.querySelector("#promo-message");
const place = document.querySelector("#place");
const confirmation = document.querySelector("#confirmation");

let savings = 0;
let orderCount = 0;

build.textContent = candidate ? "Build: candidate (seeded defects)" : "Build: reference";

function orderTotal() {
  return subtotal + shipping - savings;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const entered = code.value.trim();
  // The candidate deliberately skips normalization.
  const valid = (candidate ? entered : entered.toUpperCase()) === "SAVE10";

  if (valid) {
    savings = promoDiscount;
    message.textContent = "SAVE10 applied.";
  } else if (savings > 0) {
    message.textContent = "Code not recognized. SAVE10 is still applied.";
  } else {
    message.textContent = "Code not recognized.";
  }

  discount.value = money.format(savings / 100);
  // The candidate deliberately leaves the displayed total stale.
  if (!candidate) {
    total.value = money.format(orderTotal() / 100);
  }
});

place.addEventListener("click", () => {
  orderCount += 1;
  const reference = "FS-" + String(orderCount).padStart(4, "0");
  confirmation.textContent = `Order ${reference} confirmed · ${money.format(orderTotal() / 100)}`;

  // The candidate deliberately leaves checkout available after confirmation.
  if (!candidate) {
    place.disabled = true;
    for (const control of form.elements) {
      control.disabled = true;
    }
  }
});
