/**
 * Synapse Hardware Hub Storefront Application Logic
 * Communicates directly with the API Gateway at port 9101.
 * Executes genuine distributed HTTP requests across all 10 microservices.
 */

const API_BASE = "http://localhost:9101/api";

// App State
let currentUser = {
  user_id: "usr-admin",
  username: "admin",
  full_name: "Platform Administrator",
};
let currentCart = { items: [], total_amount: 0.0 };
let currentCategory = "All";
let allProducts = [];
let pollInterval = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", async () => {
  if (window.lucide) lucide.createIcons();
  updateUserUI();
  await loadCategories();
  await loadProducts();
  await loadRecommendations();
  await loadCart();
  await fetchNotifications();

  // Auto poll operations health every 5 seconds if on operations tab
  pollInterval = setInterval(() => {
    const opsView = document.getElementById("view-operations");
    if (opsView && !opsView.classList.contains("hidden")) {
      fetchSystemStatus();
    }
  }, 5000);
});

// -------------------------------------------------------------
// UI & Navigation Handlers
// -------------------------------------------------------------
function switchTab(tabId) {
  const views = ["store", "orders", "operations"];
  views.forEach((v) => {
    const el = document.getElementById(`view-${v}`);
    const btn = document.getElementById(`tab-btn-${v}`);
    if (el) el.classList.add("hidden");
    if (btn) {
      btn.classList.remove("text-telemetry-cyan", "bg-white/5", "font-semibold");
      btn.classList.add("text-slate-400");
    }
  });

  const activeView = document.getElementById(`view-${tabId}`);
  const activeBtn = document.getElementById(`tab-btn-${tabId}`);
  if (activeView) activeView.classList.remove("hidden");
  if (activeBtn) {
    activeBtn.classList.remove("text-slate-400");
    activeBtn.classList.add("text-telemetry-cyan", "bg-white/5", "font-semibold");
  }

  if (tabId === "orders") fetchOrders();
  if (tabId === "operations") fetchSystemStatus();
  if (window.lucide) lucide.createIcons();
}

function toggleTheme() {
  document.documentElement.classList.toggle("dark");
  if (window.lucide) lucide.createIcons();
}

function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  const text = document.getElementById("toast-text");
  if (!toast || !text) return;
  text.textContent = message;
  toast.className = `fixed bottom-5 right-5 z-50 glass px-4 py-3 rounded-xl shadow-2xl text-xs font-semibold text-white flex items-center gap-2 transform transition-all duration-300 ${
    isError ? "border-rose-500/50 bg-rose-950/80" : "border-emerald-500/50 bg-emerald-950/80"
  }`;
  toast.style.opacity = "1";
  toast.style.transform = "translateY(0)";
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(20px)";
  }, 3500);
}

// -------------------------------------------------------------
// Catalog & Products (catalog-service :9104)
// -------------------------------------------------------------
async function loadCategories() {
  try {
    const res = await fetch(`${API_BASE}/products/categories`);
    if (res.ok) {
      const data = await res.json();
      const container = document.getElementById("category-pills");
      container.innerHTML = data.categories
        .map(
          (c) => `
        <button onclick="selectCategory('${c}')" class="px-3 py-1.5 rounded-lg whitespace-nowrap transition-all ${
            c === currentCategory
              ? "bg-telemetry-cyan/20 text-telemetry-cyan font-bold border border-telemetry-cyan/40"
              : "text-slate-400 hover:text-white border border-transparent hover:bg-white/5"
          }">
          ${c}
        </button>
      `
        )
        .join("");
    }
  } catch (err) {
    console.warn("Failed to load categories:", err);
  }
}

async function selectCategory(cat) {
  currentCategory = cat;
  await loadCategories();
  await loadProducts();
}

async function loadProducts(searchQuery = "") {
  const container = document.getElementById("products-grid");
  const countLabel = document.getElementById("product-count-label");
  let url = `${API_BASE}/products`;
  const params = [];
  if (currentCategory && currentCategory !== "All") params.push(`category=${encodeURIComponent(currentCategory)}`);
  if (searchQuery) params.push(`q=${encodeURIComponent(searchQuery)}`);
  if (params.length) url += `?${params.join("&")}`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    allProducts = await res.json();
    countLabel.textContent = `${allProducts.length} items available`;

    if (!allProducts.length) {
      container.innerHTML = `<div class="col-span-full py-12 text-center text-slate-400">No hardware components found matching criteria.</div>`;
      return;
    }

    container.innerHTML = allProducts
      .map(
        (p) => `
      <div class="glass rounded-2xl overflow-hidden border dark:border-white/10 border-slate-200 flex flex-col group hover:border-telemetry-cyan/40 transition-all duration-300">
        <div class="h-44 overflow-hidden relative bg-obsidian-800">
          <img src="${p.image_url}" alt="${p.name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500">
          <span class="absolute top-3 left-3 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider ${
            p.stock_count > 0 ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
          }">
            ${p.stock_count > 0 ? `${p.stock_count} In Stock` : "Out of Stock"}
          </span>
          <span class="absolute top-3 right-3 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-black/60 text-slate-300 backdrop-blur-md">
            ${p.category}
          </span>
        </div>
        <div class="p-5 flex-1 flex flex-col justify-between space-y-3">
          <div>
            <div class="flex items-center gap-1 text-telemetry-amber text-[11px] mb-1">
              <i data-lucide="star" class="w-3.5 h-3.5 fill-current"></i>
              <span>${p.rating} / 5.0</span>
            </div>
            <h3 class="font-bold text-sm text-white line-clamp-1 group-hover:text-telemetry-cyan transition-colors">${p.name}</h3>
            <p class="text-xs text-slate-400 line-clamp-2 mt-1 leading-relaxed">${p.description}</p>
          </div>
          <div class="flex items-center justify-between pt-2 border-t border-white/5">
            <span class="text-base font-extrabold text-white font-mono">$${p.price.toFixed(2)}</span>
            <button onclick="addToCart('${p.id}')" ${p.stock_count <= 0 ? "disabled" : ""} class="px-3.5 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-40 text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-brand-500/20 transition-all">
              <i data-lucide="plus" class="w-3.5 h-3.5"></i>
              Add
            </button>
          </div>
        </div>
      </div>
    `
      )
      .join("");
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    container.innerHTML = `<div class="col-span-full py-8 text-center text-rose-400">Failed to load catalog from API Gateway. Error: ${err.message}</div>`;
  }
}

function handleSearch(event) {
  const query = event.target.value.trim();
  loadProducts(query);
}

// -------------------------------------------------------------
// Recommendations (recommendation-service :9110)
// -------------------------------------------------------------
async function loadRecommendations() {
  const container = document.getElementById("recommendations-container");
  if (!container) return;
  try {
    const res = await fetch(`${API_BASE}/recommendations/trending`);
    if (res.ok) {
      const items = await res.json();
      container.innerHTML = items
        .map(
          (p) => `
        <div class="glass rounded-xl p-4 border border-white/10 flex items-center gap-3">
          <img src="${p.image_url}" class="w-14 h-14 rounded-lg object-cover">
          <div class="flex-1 min-w-0">
            <h4 class="text-xs font-bold text-white truncate">${p.name}</h4>
            <span class="text-xs font-mono text-telemetry-cyan font-bold">$${p.price.toFixed(2)}</span>
          </div>
          <button onclick="addToCart('${p.id}')" class="p-2 rounded-lg bg-white/5 hover:bg-brand-600 text-slate-300 hover:text-white transition-all">
            <i data-lucide="shopping-cart" class="w-4 h-4"></i>
          </button>
        </div>
      `
        )
        .join("");
      if (window.lucide) lucide.createIcons();
    }
  } catch (e) {
    console.warn("Recommendations skipped:", e);
  }
}

// -------------------------------------------------------------
// Cart Operations (cart-service :9106)
// -------------------------------------------------------------
async function loadCart() {
  try {
    const res = await fetch(`${API_BASE}/cart/${currentUser.user_id}`);
    if (res.ok) {
      currentCart = await res.json();
      updateCartBadge();
    }
  } catch (err) {
    console.warn("Failed to load cart:", err);
  }
}

function updateCartBadge() {
  const badge = document.getElementById("cart-count");
  const count = (currentCart.items || []).reduce((acc, i) => acc + i.quantity, 0);
  if (badge) badge.textContent = count;
}

function openCart() {
  const drawer = document.getElementById("cart-drawer");
  if (drawer) drawer.classList.remove("translate-x-full");
  renderCartDrawer();
}

function closeCart() {
  const drawer = document.getElementById("cart-drawer");
  if (drawer) drawer.classList.add("translate-x-full");
}

function renderCartDrawer() {
  const container = document.getElementById("cart-items-container");
  const subtotal = document.getElementById("cart-subtotal");
  const checkoutBtn = document.getElementById("checkout-btn");

  subtotal.textContent = `$${(currentCart.total_amount || 0).toFixed(2)}`;

  if (!currentCart.items || !currentCart.items.length) {
    container.innerHTML = `
      <div class="py-16 text-center text-slate-400 space-y-2">
        <i data-lucide="shopping-bag" class="w-10 h-10 mx-auto text-slate-600"></i>
        <p class="text-xs">Your shopping cart is currently empty</p>
      </div>`;
    if (checkoutBtn) checkoutBtn.disabled = true;
    if (window.lucide) lucide.createIcons();
    return;
  }

  if (checkoutBtn) checkoutBtn.disabled = false;

  container.innerHTML = currentCart.items
    .map(
      (item) => `
    <div class="p-3 rounded-xl bg-white/5 border border-white/10 flex items-center gap-3">
      <img src="${item.image_url}" class="w-12 h-12 rounded-lg object-cover">
      <div class="flex-1 min-w-0">
        <h4 class="text-xs font-bold text-white truncate">${item.name}</h4>
        <div class="text-[11px] text-slate-400 font-mono mt-0.5">$${item.price.toFixed(2)} each</div>
      </div>
      <div class="flex items-center gap-2">
        <button onclick="updateItemQuantity('${item.product_id}', ${item.quantity - 1})" class="w-6 h-6 rounded bg-white/10 text-white flex items-center justify-center hover:bg-white/20">-</button>
        <span class="text-xs font-mono font-bold text-white w-4 text-center">${item.quantity}</span>
        <button onclick="updateItemQuantity('${item.product_id}', ${item.quantity + 1})" class="w-6 h-6 rounded bg-white/10 text-white flex items-center justify-center hover:bg-white/20">+</button>
      </div>
    </div>
  `
    )
    .join("");
  if (window.lucide) lucide.createIcons();
}

async function addToCart(productId) {
  try {
    const res = await fetch(`${API_BASE}/cart/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: currentUser.user_id,
        product_id: productId,
        quantity: 1,
      }),
    });
    if (!res.ok) throw new Error("Failed to add to cart");
    currentCart = await res.json();
    updateCartBadge();
    showToast("Added item to cart");
  } catch (err) {
    showToast(`Error adding to cart: ${err.message}`, true);
  }
}

async function updateItemQuantity(productId, newQty) {
  try {
    const res = await fetch(`${API_BASE}/cart/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: currentUser.user_id,
        product_id: productId,
        quantity: newQty,
      }),
    });
    if (res.ok) {
      currentCart = await res.json();
      updateCartBadge();
      renderCartDrawer();
    }
  } catch (err) {
    console.error(err);
  }
}

// -------------------------------------------------------------
// Checkout & Distributed Order Execution (order-service :9107)
// -------------------------------------------------------------
function openCheckoutModal() {
  closeCart();
  const modal = document.getElementById("checkout-modal");
  const totalLabel = document.getElementById("checkout-total-label");
  totalLabel.textContent = `$${(currentCart.total_amount || 0).toFixed(2)}`;
  if (modal) modal.classList.remove("hidden");
}

function closeCheckoutModal() {
  const modal = document.getElementById("checkout-modal");
  if (modal) modal.classList.add("hidden");
}

async function submitCheckout() {
  const btn = document.getElementById("submit-checkout-btn");
  const statusMsg = document.getElementById("checkout-status-msg");
  const address = document.getElementById("checkout-address").value;
  const payMethod = document.getElementById("checkout-payment-method").value;

  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Processing Transaction...`;
  statusMsg.className = "text-xs font-mono p-3 rounded-lg bg-brand-500/10 text-brand-300 border border-brand-500/20";
  statusMsg.textContent = "1/4 Reserving inventory -> 2/4 Authorizing payment -> 3/4 Confirming order...";
  statusMsg.classList.remove("hidden");
  if (window.lucide) lucide.createIcons();

  try {
    const res = await fetch(`${API_BASE}/orders/checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: currentUser.user_id,
        payment_method: payMethod,
        shipping_address: address,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Transaction failed");
    }

    // Success!
    closeCheckoutModal();
    await loadCart();
    await loadProducts(); // Refresh stock
    await fetchNotifications();
    showToast(`Order Confirmed! Ref #${data.order_id}`);
    switchTab("orders");
  } catch (err) {
    statusMsg.className = "text-xs font-mono p-3 rounded-lg bg-rose-500/20 text-rose-300 border border-rose-500/40";
    statusMsg.textContent = `❌ Checkout Failed: ${err.message}`;
    showToast(err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Authorize & Pay";
  }
}

// 1-Click Simulation for Quick Demo Presentation
async function quickDemoOrder() {
  if (!allProducts.length) await loadProducts();
  const sample = allProducts[0];
  if (!sample) return;
  await addToCart(sample.id);
  openCheckoutModal();
}

// -------------------------------------------------------------
// Orders History (order-service :9107)
// -------------------------------------------------------------
async function fetchOrders() {
  const container = document.getElementById("orders-list-container");
  container.innerHTML = `<div class="py-8 text-center text-slate-400">Loading order receipts...</div>`;

  try {
    const res = await fetch(`${API_BASE}/orders/user/${currentUser.user_id}`);
    if (!res.ok) throw new Error("Failed to load orders");
    const orders = await res.json();

    if (!orders.length) {
      container.innerHTML = `<div class="glass p-8 rounded-xl text-center text-slate-400">No orders placed yet. Add items and complete checkout!</div>`;
      return;
    }

    container.innerHTML = orders
      .map(
        (o) => `
      <div class="glass rounded-xl p-5 border border-white/10 space-y-3">
        <div class="flex items-center justify-between border-b border-white/5 pb-3">
          <div>
            <span class="text-xs font-mono font-bold text-telemetry-cyan">ORDER #${o.order_id}</span>
            <span class="text-[11px] text-slate-400 ml-3">${new Date(o.created_at).toLocaleString()}</span>
          </div>
          <span class="px-2.5 py-1 rounded text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            ${o.status}
          </span>
        </div>
        <div class="text-xs space-y-1">
          <div class="text-slate-300 font-semibold">Items:</div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-400">
            ${o.items.map((i) => `<div>• ${i.name} (x${i.quantity}) — $${(i.price * i.quantity).toFixed(2)}</div>`).join("")}
          </div>
        </div>
        <div class="flex items-center justify-between pt-2 border-t border-white/5 text-xs font-mono">
          <span class="text-slate-400">Payment Ref: ${o.payment_id || "N/A"}</span>
          <span class="text-base font-bold text-white">Total: $${o.total_amount.toFixed(2)}</span>
        </div>
      </div>
    `
      )
      .join("");
  } catch (err) {
    container.innerHTML = `<div class="text-rose-400 p-4">Error loading orders: ${err.message}</div>`;
  }
}

// -------------------------------------------------------------
// Operations & Microservices Health (All 10 Services)
// -------------------------------------------------------------
async function fetchSystemStatus() {
  const container = document.getElementById("services-grid");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/operations/system-status`);
    if (!res.ok) throw new Error("Gateway health unreachable");
    const data = await res.json();

    container.innerHTML = Object.entries(data.services)
      .map(([name, s]) => {
        const isHealthy = s.status === "healthy" && !s.has_active_fault;
        const activeFaultKeys = Object.keys(s.active_faults || {});
        return `
        <div class="glass rounded-xl p-5 border ${
          isHealthy ? "border-emerald-500/30 bg-emerald-950/10" : "border-amber-500/40 bg-amber-950/20"
        } space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold font-mono text-white">${name}</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
              isHealthy ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
            }">
              ${isHealthy ? "HEALTHY" : "FAULT ACTIVE"}
            </span>
          </div>
          <div class="text-[11px] font-mono text-slate-400 space-y-1">
            <div class="flex justify-between">
              <span>Port / URL:</span>
              <span class="text-slate-200">${s.url}</span>
            </div>
            <div class="flex justify-between">
              <span>Probe Latency:</span>
              <span class="text-slate-200">${s.latency_ms !== null ? `${s.latency_ms}ms` : "N/A"}</span>
            </div>
            ${
              activeFaultKeys.length
                ? `<div class="text-amber-400 font-bold">Active Faults: ${activeFaultKeys.join(", ")}</div>`
                : ""
            }
          </div>
          <div class="pt-2 border-t border-white/5 flex gap-2">
            <button onclick="injectChaos('${name}', 'latency', 60, 0.8)" class="flex-1 py-1 rounded bg-white/5 hover:bg-amber-500/20 hover:text-amber-300 text-[10px] font-semibold text-slate-300 border border-white/10 transition-all">
              + Latency
            </button>
            <button onclick="injectChaos('${name}', 'error_rate', 60, 0.8)" class="flex-1 py-1 rounded bg-white/5 hover:bg-rose-500/20 hover:text-rose-300 text-[10px] font-semibold text-slate-300 border border-white/10 transition-all">
              + 500 Errors
            </button>
          </div>
        </div>
      `;
      })
      .join("");
  } catch (err) {
    container.innerHTML = `<div class="col-span-full text-rose-400 text-xs font-mono">Error polling system status: ${err.message}</div>`;
  }
}

async function injectChaos(serviceName, faultType, duration = 120, intensity = 0.8) {
  try {
    const res = await fetch(`${API_BASE}/operations/chaos/inject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        service_name: serviceName,
        fault_type: faultType,
        duration_seconds: duration,
        intensity: intensity,
      }),
    });
    const data = await res.json();
    showToast(`Chaos injected into [${serviceName}]: ${faultType}`);
    await fetchSystemStatus();
  } catch (err) {
    showToast(`Chaos injection error: ${err.message}`, true);
  }
}

async function clearAllChaos() {
  try {
    await fetch(`${API_BASE}/operations/chaos/clear-all`, { method: "POST" });
    showToast("Cleared all faults across all 10 services!");
    await fetchSystemStatus();
  } catch (err) {
    showToast(err.message, true);
  }
}

// -------------------------------------------------------------
// Notifications
// -------------------------------------------------------------
async function fetchNotifications() {
  try {
    const res = await fetch(`${API_BASE}/notifications/${currentUser.user_id}`);
    if (res.ok) {
      const items = await res.json();
      const badge = document.getElementById("notif-badge");
      const unread = items.some((i) => !i.read);
      if (badge) badge.classList.toggle("hidden", !unread);

      const container = document.getElementById("notif-list-container");
      if (container) {
        if (!items.length) {
          container.innerHTML = `<div class="py-8 text-center text-xs text-slate-400">No alerts yet</div>`;
          return;
        }
        container.innerHTML = items
          .map(
            (n) => `
          <div class="p-3 rounded-lg bg-white/5 border border-white/10 space-y-1">
            <div class="text-xs font-bold text-white">${n.title}</div>
            <div class="text-[11px] text-slate-300 leading-tight">${n.message}</div>
            <div class="text-[9px] font-mono text-slate-400">${new Date(n.timestamp).toLocaleTimeString()}</div>
          </div>
        `
          )
          .join("");
      }
    }
  } catch (e) {
    console.warn("Notifications error:", e);
  }
}

function toggleNotifications() {
  const drawer = document.getElementById("notif-drawer");
  if (drawer) drawer.classList.toggle("translate-x-full");
}

// -------------------------------------------------------------
// User Authentication
// -------------------------------------------------------------
function updateUserUI() {
  const container = document.getElementById("user-pill-container");
  if (!container) return;
  if (currentUser) {
    container.innerHTML = `
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg glass border border-white/10 text-xs">
        <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
        <span class="font-bold text-white">${currentUser.username}</span>
      </div>`;
  }
}

function openAuthModal() {
  const modal = document.getElementById("auth-modal");
  if (modal) modal.classList.remove("hidden");
}

function closeAuthModal() {
  const modal = document.getElementById("auth-modal");
  if (modal) modal.classList.add("hidden");
}

async function submitAuth() {
  const u = document.getElementById("auth-username").value;
  const p = document.getElementById("auth-password").value;
  const errEl = document.getElementById("auth-error-msg");
  errEl.classList.add("hidden");

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u, password: p }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Authentication failed");
    }
    const data = await res.json();
    currentUser = data.user;
    updateUserUI();
    closeAuthModal();
    showToast(`Welcome back, ${currentUser.full_name}!`);
    await loadCart();
    await fetchOrders();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove("hidden");
  }
}
