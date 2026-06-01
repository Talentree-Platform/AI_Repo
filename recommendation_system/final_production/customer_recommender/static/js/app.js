document.addEventListener("DOMContentLoaded", () => {
    // DOM Cache
    const btnRecommend = document.getElementById("btn-recommend");
    const btnRetrain = document.getElementById("btn-retrain");
    const selectCustomerId = document.getElementById("select-customer-id");
    const inputTopK = document.getElementById("input-top-k");
    
    const statClass = document.getElementById("stat-class");
    const statAlpha = document.getElementById("stat-alpha");
    const statUsers = document.getElementById("stat-users");
    const statUpdated = document.getElementById("stat-updated");
    
    const loader = document.getElementById("loader");
    const noResults = document.getElementById("no-results");
    const resultsGrid = document.getElementById("results-grid");
    const retrainBanner = document.getElementById("retrain-banner");
    
    const alertModal = document.getElementById("alert-modal");
    const alertMessage = document.getElementById("alert-message");
    
    const API_BASE = ""; // Relative paths since hosted on same server

    // Fetch and populate customer dropdown list
    async function loadCustomersList() {
        try {
            const res = await fetch(`${API_BASE}/customer/list`);
            if (!res.ok) throw new Error("Failed to load customer list");
            const customers = await res.json();
            
            selectCustomerId.innerHTML = "";
            customers.forEach(cust => {
                const opt = document.createElement("option");
                opt.value = cust.user_id;
                const displayId = cust.user_id.length > 8 ? `${cust.user_id.substring(0, 8)}...` : cust.user_id;
                opt.textContent = `${cust.name} [${displayId}]`;
                if (cust.user_id === "123") {
                    opt.selected = true;
                }
                selectCustomerId.appendChild(opt);
            });
        } catch (err) {
            console.error(err);
            selectCustomerId.innerHTML = '<option value="123" selected>Active Demo User #123</option>';
        }
    }

    // Fetch and populate active model info
    async function loadModelStats() {
        try {
            const res = await fetch(`${API_BASE}/customer/model-info`);
            if (!res.ok) throw new Error("Failed to load model specifications");
            const data = await res.json();
            
            if (data.status === "active") {
                statClass.textContent = data.model_class;
                statAlpha.textContent = data.alpha;
                statUsers.textContent = data.trained_users_count;
                
                // Format timestamp
                if (data.last_modified && data.last_modified !== "N/A") {
                    const date = new Date(data.last_modified);
                    statUpdated.textContent = date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                } else {
                    statUpdated.textContent = "N/A (Preloaded)";
                }
            } else {
                statClass.textContent = "Fallback Mode";
                statAlpha.textContent = "N/A";
                statUsers.textContent = "0";
                statUpdated.textContent = "N/A";
            }
        } catch (err) {
            console.error(err);
            statClass.textContent = "Disconnected";
        }
    }

    // Trigger Recommendation Request
    async function getRecommendations() {
        const customerId = selectCustomerId.value;
        const topK = parseInt(inputTopK.value);
        
        if (!customerId) {
            showAlert("Please select a Customer Profile.");
            return;
        }
        if (isNaN(topK) || topK < 1 || topK > 50) {
            showAlert("Please choose a recommendation count between 1 and 50.");
            return;
        }
        
        // UI states
        loader.classList.remove("hidden");
        noResults.classList.add("hidden");
        resultsGrid.classList.add("hidden");
        
        try {
            const res = await fetch(`${API_BASE}/customer/recommend`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ customer_id: customerId, top_k: topK })
            });
            
            if (!res.ok) throw new Error("Server returned recommendation failure");
            const data = await res.json();
            
            renderRecommendations(data.recommendations);
        } catch (err) {
            console.error(err);
            showAlert("Could not compute product recommendations. Verify that the selected Customer profile has interaction logs.");
            noResults.classList.remove("hidden");
        } finally {
            loader.classList.add("hidden");
        }
    }

    // Render Cards in Results Grid
    function renderRecommendations(items) {
        resultsGrid.innerHTML = "";
        
        if (!items || items.length === 0) {
            noResults.classList.remove("hidden");
            return;
        }
        
        items.forEach(item => {
            const card = document.createElement("div");
            card.className = "product-card";
            
            // Format match score as percentage
            const pct = Math.round(item.score * 100);
            
            card.innerHTML = `
                <span class="prod-score-badge">${pct}% Match</span>
                <span class="prod-category">${item.category}</span>
                <h4 class="prod-title">${item.product_name}</h4>
                <p class="prod-desc">${item.description}</p>
                <div class="prod-footer">
                    <span class="prod-price">$${item.price.toFixed(2)}</span>
                    <button class="prod-buy-btn" onclick="alert('Added item #${item.product_id} to simulated cart!')">Add to Cart</button>
                </div>
            `;
            resultsGrid.appendChild(card);
        });
        
        resultsGrid.classList.remove("hidden");
    }

    // Trigger Weekly Retraining Background Task
    async function triggerRetraining() {
        btnRetrain.disabled = true;
        btnRetrain.textContent = "Retraining...";
        
        try {
            const res = await fetch(`${API_BASE}/customer/retrain`, { method: "POST" });
            if (!res.ok) throw new Error("Pipeline trigger failure");
            
            // Show success banner
            retrainBanner.classList.remove("hidden");
            setTimeout(() => {
                retrainBanner.classList.add("hidden");
            }, 6000);
            
            // Refresh stats shortly
            setTimeout(loadModelStats, 3000);
        } catch (err) {
            console.error(err);
            showAlert("Failed to initiate retraining pipeline. Database may be disconnected.");
        } finally {
            btnRetrain.disabled = false;
            btnRetrain.innerHTML = `<span class="btn-icon">⚡</span> Retrain Pipeline`;
        }
    }

    // Utility alerts modal
    function showAlert(msg) {
        alertMessage.textContent = msg;
        alertModal.classList.remove("hidden");
    }

    // Attach Event Listeners
    btnRecommend.addEventListener("click", getRecommendations);
    btnRetrain.addEventListener("click", triggerRetraining);
    // Initial setups
    loadModelStats();
    loadCustomersList();
});
