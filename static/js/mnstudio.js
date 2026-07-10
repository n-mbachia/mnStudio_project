/**
 * MN Studio — Progressive enhancement JS
 * Lightweight vanilla JS; Alpine.js handles reactivity.
 */

document.addEventListener("DOMContentLoaded", function () {

  // ── Auto-dismiss flash messages after 5s ─────────────────────────────
  const messages = document.querySelectorAll("[data-auto-dismiss]");
  messages.forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity 0.4s";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 400);
    }, 5000);
  });

  // ── Auction live countdown ────────────────────────────────────────────
  const countdowns = document.querySelectorAll("[data-end-time]");
  countdowns.forEach(function (el) {
    const endTime = new Date(el.dataset.endTime);

    function tick() {
      const now  = new Date();
      const diff = endTime - now;
      if (diff <= 0) {
        el.textContent = "Auction closed";
        el.classList.remove("auction-live");
        return;
      }
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      el.textContent = `${h}h ${m}m ${s}s remaining`;
      if (diff < 300000) el.classList.add("auction-live"); // pulse in final 5 mins
    }

    tick();
    setInterval(tick, 1000);
  });

  // ── Confirm on destructive actions ───────────────────────────────────
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      if (!window.confirm(el.dataset.confirm || "Are you sure?")) {
        e.preventDefault();
      }
    });
  });

  // ── Quote/Invoice live line-item total preview ────────────────────────
  function updateLineItemTotals() {
    let grandTotal = 0;
    document.querySelectorAll(".line-item-row").forEach(function (row) {
      const qty   = parseFloat(row.querySelector(".li-qty")?.value  || 0);
      const price = parseFloat(row.querySelector(".li-price")?.value || 0);
      const total = qty * price;
      grandTotal += total;
      const totalEl = row.querySelector(".li-total");
      if (totalEl) totalEl.textContent = "KES " + total.toLocaleString("en-KE", {minimumFractionDigits: 2});
    });
    const grandEl = document.getElementById("grand-total");
    if (grandEl) grandEl.textContent = "KES " + grandTotal.toLocaleString("en-KE", {minimumFractionDigits: 2});
  }

  document.querySelectorAll(".li-qty, .li-price").forEach(function (input) {
    input.addEventListener("input", updateLineItemTotals);
  });
  updateLineItemTotals();

  // ── BOM entry running COGS total ─────────────────────────────────────
  function updateBOMTotal() {
    let total = 0;
    document.querySelectorAll("[data-bom-cost]").forEach(function (el) {
      total += parseFloat(el.dataset.bomCost || 0);
    });
    const el = document.getElementById("bom-running-total");
    if (el) el.textContent = "KES " + total.toLocaleString("en-KE", {minimumFractionDigits: 2});
  }
  updateBOMTotal();

});
