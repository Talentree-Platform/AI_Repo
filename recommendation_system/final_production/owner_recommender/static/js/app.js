document.addEventListener("DOMContentLoaded", () => {
    // DOM Cache
    const btnRecommend = document.getElementById("btn-recommend");
    const btnRetrain = document.getElementById("btn-retrain");
    const selectOwnerId = document.getElementById("select-owner-id");
    const inputTopK = document.getElementById("input-top-k");
    
    const statClass = document.getElementById("stat-class");
    const statCycles = document.getElementById("stat-cycles");
    const statMaterials = document.getElementById("stat-materials");
    const statUpdated = document.getElementById("stat-updated");
    
    const loader = document.getElementById("loader");
    const noResults = document.getElementById("no-results");
    const resultsTableContainer = document.getElementById("results-table-container");
    const resultsTableBody = document.getElementById("results-table-body");
    const retrainBanner = document.getElementById("retrain-banner");
    
    const alertModal = document.getElementById("alert-modal");
    const alertMessage = document.getElementById("alert-message");
    
    const API_BASE = ""; // Host relative

    // Fetch and populate owner dropdown list
    async function loadOwnersList() {
        try {
            const res = await fetch(`${API_BASE}/owner/list`);
            if (!res.ok) throw new Error("Failed to load owner list");
            const owners = await res.json();
            
            selectOwnerId.innerHTML = "";
            owners.forEach(owner => {
                const opt = document.createElement("option");
                opt.value = owner.owner_id;
                opt.textContent = `${owner.name} [ID: ${owner.owner_id}]`;
                if (owner.owner_id === "33" || owner.owner_id === "3") {
                    opt.selected = true; // Pre-select a pre-trained active owner
                }
                selectOwnerId.appendChild(opt);
            });
        } catch (err) {
            console.error(err);
            selectOwnerId.innerHTML = '<option value="33" selected>Active Demo Owner #33</option>';
        }
    }

    // Fetch active model specs
    async function loadModelStats() {
        try {
            const res = await fetch(`${API_BASE}/owner/model-info`);
            if (!res.ok) throw new Error("Failed to load forecasting specifications");
            const data = await res.json();
            
            if (data.status === "active") {
                statClass.textContent = "Ridge Regressor + Cyclic";
                statCycles.textContent = data.reorder_cycles_tracked;
                statMaterials.textContent = data.trained_materials_count;
                
                if (data.last_modified && data.last_modified !== "N/A") {
                    const date = new Date(data.last_modified);
                    statUpdated.textContent = date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                } else {
                    statUpdated.textContent = "N/A (Preloaded)";
                }
            } else {
                statClass.textContent = "Fallback Mode";
                statCycles.textContent = "N/A";
                statMaterials.textContent = "0";
                statUpdated.textContent = "N/A";
            }
        } catch (err) {
            console.error(err);
            statClass.textContent = "Disconnected";
        }
    }

    // Fetch recommendations list
    async function getRecommendations() {
        const ownerId = selectOwnerId.value;
        const topK = parseInt(inputTopK.value);
        
        if (!ownerId) {
            showAlert("Please select a Business Owner Profile.");
            return;
        }
        if (isNaN(topK) || topK < 1 || topK > 50) {
            showAlert("Please choose a recommendation count between 1 and 50.");
            return;
        }
        
        // UI reset states
        loader.classList.remove("hidden");
        noResults.classList.add("hidden");
        resultsTableContainer.classList.add("hidden");
        
        try {
            const res = await fetch(`${API_BASE}/owner/recommend`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ owner_id: ownerId, top_k: topK })
            });
            
            if (!res.ok) throw new Error("Server returned recommendation failure");
            const data = await res.json();
            
            renderRecommendationsTable(data.recommendations);
        } catch (err) {
            console.error(err);
            showAlert("Could not compute procurement plans. Verify that selected Owner profile has historical procurement data.");
            noResults.classList.remove("hidden");
        } finally {
            loader.classList.add("hidden");
        }
    }

    // Render Table Body
    function renderRecommendationsTable(items) {
        resultsTableBody.innerHTML = "";
        
        if (!items || items.length === 0) {
            noResults.classList.remove("hidden");
            return;
        }
        
        items.forEach(item => {
            const row = document.createElement("tr");
            
            // Format score as percentage
            const pct = Math.round(item.score * 100);
            
            // Calculate urgency badge
            let urgencyBadge = `<span class="badge badge-success">Stock Adequate</span>`;
            if (item.urgency_days_elapsed > 0 && item.urgency_cycle_days > 0) {
                const ratio = item.urgency_days_elapsed / item.urgency_cycle_days;
                if (ratio >= 1.0) {
                    urgencyBadge = `<span class="badge badge-danger">Reorder Critical</span>`;
                } else if (ratio >= 0.75) {
                    urgencyBadge = `<span class="badge badge-warning">Due Soon</span>`;
                }
            } else if (item.urgency_days_elapsed === 0) {
                // Mock default fallback
                urgencyBadge = `<span class="badge badge-warning">Due Soon</span>`;
            }
            
            const reorderCycleText = item.urgency_cycle_days > 0 
                ? `Every ${item.urgency_cycle_days} days` 
                : "N/A";
                
            row.innerHTML = `
                <td>
                    <strong style="color: #ffffff; display: block;">${item.material_name}</strong>
                    <span style="font-size: 0.75rem; color: var(--text-muted);">${item.description}</span>
                </td>
                <td>${item.category}</td>
                <td>$${item.price.toFixed(2)}</td>
                <td><strong>${item.predicted_demand_qty}</strong> units/wk</td>
                <td>${urgencyBadge}</td>
                <td>${reorderCycleText}</td>
                <td>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <div style="flex-grow:1; height:6px; background:rgba(255,255,255,0.05); border-radius:3px; overflow:hidden;">
                            <div style="width: ${pct}%; height:100%; background:var(--accent);"></div>
                        </div>
                        <strong>${pct}%</strong>
                    </div>
                </td>
                <td>
                    <button class="btn-table-action" onclick="alert('Triggered procurement purchase order of ${Math.round(item.predicted_demand_qty)} units of raw ${item.material_name}!')">Procure</button>
                </td>
            `;
            resultsTableBody.appendChild(row);
        });
        
        resultsTableContainer.classList.remove("hidden");
    }

    // Trigger retraining background task
    async function triggerRetraining() {
        btnRetrain.disabled = true;
        btnRetrain.textContent = "Retraining...";
        
        try {
            const res = await fetch(`${API_BASE}/owner/retrain`, { method: "POST" });
            if (!res.ok) throw new Error("Pipeline trigger failure");
            
            retrainBanner.classList.remove("hidden");
            setTimeout(() => {
                retrainBanner.classList.add("hidden");
            }, 6000);
            
            setTimeout(loadModelStats, 3000);
        } catch (err) {
            console.error(err);
            showAlert("Failed to initiate retraining pipeline. Database may be disconnected.");
        } finally {
            btnRetrain.disabled = false;
            btnRetrain.innerHTML = `<span class="btn-icon">⚡</span> Retrain Pipeline`;
        }
    }

    // Show alerts modal
    function showAlert(msg) {
        alertMessage.textContent = msg;
        alertModal.classList.remove("hidden");
    }

    // Attach Event Listeners
    btnRecommend.addEventListener("click", getRecommendations);
    btnRetrain.addEventListener("click", triggerRetraining);
    // Startup
    loadModelStats();
    loadOwnersList();
});
