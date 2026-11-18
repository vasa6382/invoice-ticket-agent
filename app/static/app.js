// Automated Invoice & Ticket Processing Agent Client Logic

let currentInvoice = {
  vendor_name: "Acme Cloud Solutions Inc.",
  invoice_id: "INV-2026-9812",
  invoice_date: "2026-10-12",
  total_amount: 450.00,
  currency: "USD",
  line_items: [
    { description: "Cloud Infrastructure Tier 1", quantity: 1, unit_price: 450.00, amount: 450.00 }
  ],
  confidence_score: 0.94,
  extraction_engine: "AI Builder / Prebuilt Model",
  status: "Auto-Approved"
};

const SAMPLES = {
  happy_low: {
    vendor_name: "GitHub Inc. Enterprise",
    invoice_id: "INV-GH-44910",
    invoice_date: "2026-10-10",
    total_amount: 450.00,
    currency: "USD",
    line_items: [
      { description: "GitHub Copilot Enterprise Seats (x10)", quantity: 10, unit_price: 39.00, amount: 390.00 },
      { description: "GitHub Actions Compute Minutes", quantity: 1, unit_price: 60.00, amount: 60.00 }
    ],
    confidence_score: 0.96,
    extraction_engine: "AI Builder Prebuilt Invoice Model",
    raw_text: "GitHub Inc. Enterprise\nInvoice #: INV-GH-44910\nDate: 2026-10-10\nSeats: 10 @ $39.00 = $390.00\nActions: $60.00\nTotal Amount: $450.00 USD"
  },
  high_val: {
    vendor_name: "Microsoft Cloud & AI Division",
    invoice_id: "MSFT-AZ-892144",
    invoice_date: "2026-10-11",
    total_amount: 4850.00,
    currency: "USD",
    line_items: [
      { description: "Azure OpenAI Dedicated Deployment (GPT-4o)", quantity: 1, unit_price: 3500.00, amount: 3500.00 },
      { description: "Azure Cosmos DB Multi-Region Write", quantity: 1, unit_price: 1350.00, amount: 1350.00 }
    ],
    confidence_score: 0.92,
    extraction_engine: "AI Builder Prebuilt Invoice Model",
    raw_text: "Microsoft Corporation\nInvoice Number: MSFT-AZ-892144\nDate: 2026-10-11\nAzure OpenAI: $3500.00\nCosmos DB: $1350.00\nTotal Due: $4,850.00 USD"
  },
  inr_high: {
    vendor_name: "Tata Consultancy & Cloud Services Ltd",
    invoice_id: "TCS-BILL-2026-778",
    invoice_date: "2026-10-12",
    total_amount: 125000.00,
    currency: "INR",
    line_items: [
      { description: "Managed Automation Cloud Maintenance", quantity: 1, unit_price: 125000.00, amount: 125000.00 }
    ],
    confidence_score: 0.89,
    extraction_engine: "PyMuPDF + Pattern Heuristics",
    raw_text: "Tata Consultancy & Cloud Services Ltd\nGSTIN: 27AAACT2727Q1ZW\nBill ID: TCS-BILL-2026-778\nDate: 12-10-2026\nDescription: Managed Automation Cloud Maintenance\nTotal Payable: ₹1,25,000.00 INR"
  },
  low_conf: {
    vendor_name: "Unknown Vendor (Blurry)",
    invoice_id: "GEN-202610130950",
    invoice_date: "2026-10-13",
    total_amount: 0.00,
    currency: "USD",
    line_items: [
      { description: "Unparsed Document Content", quantity: 1, unit_price: 0.00, amount: 0.00 }
    ],
    confidence_score: 0.38,
    extraction_engine: "Fallback OCR Stream",
    raw_text: "Scan #99 ... illegible receipt header ... blurred text ... missing total summary ... low DPI scan"
  }
};

document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupDropzone();
  setupSampleButtons();
  setupActionButtons();
  updateUI();
  loadAuditLogs();
});

// Tab Navigation
function setupTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      document.getElementById(targetId).classList.add("active");

      if (targetId === "tab-audit") {
        loadAuditLogs();
      }
    });
  });
}

// Drag & Drop
function setupDropzone() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files.length > 0) {
      handleFileUpload(fileInput.files[0]);
    }
  });
}

// Upload file to Backend Extraction API
async function handleFileUpload(file) {
  const fileInfoBox = document.getElementById("fileInfoBox");
  const infoFileName = document.getElementById("infoFileName");
  const infoFileSize = document.getElementById("infoFileSize");
  const uploadSpinner = document.getElementById("uploadSpinner");

  fileInfoBox.style.display = "flex";
  infoFileName.textContent = file.name;
  infoFileSize.textContent = `${(file.size / 1024).toFixed(1)} KB`;
  uploadSpinner.style.display = "inline-block";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/v1/extract-invoice", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Extraction failed");
    }

    const data = await res.json();
    currentInvoice = data;

    // Evaluate routing rule
    await evaluateRoutingRule();
    updateUI();

    document.getElementById("rawTextContainer").textContent = data.raw_text_snippet || "Text processed successfully.";
  } catch (error) {
    alert("Error processing file: " + error.message);
  } finally {
    uploadSpinner.style.display = "none";
  }
}

// Setup Sample Buttons
function setupSampleButtons() {
  document.querySelectorAll(".btn-sample[data-sample]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const key = btn.getAttribute("data-sample");
      const sample = SAMPLES[key];
      if (sample) {
        currentInvoice = { ...sample };
        document.getElementById("fileInfoBox").style.display = "flex";
        document.getElementById("infoFileName").textContent = `${key}_sample_invoice.pdf`;
        document.getElementById("infoFileSize").textContent = "38.4 KB";
        document.getElementById("rawTextContainer").textContent = sample.raw_text;

        await evaluateRoutingRule();
        updateUI();
      }
    });
  });
}

// Evaluate routing via API
async function evaluateRoutingRule() {
  try {
    const res = await fetch("/api/v1/evaluate-routing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        total_amount: currentInvoice.total_amount,
        currency: currentInvoice.currency,
        confidence_score: currentInvoice.confidence_score
      })
    });
    const decision = await res.json();
    currentInvoice.routing = decision;
    currentInvoice.status = decision.status;
  } catch (e) {
    console.error("Routing evaluation error:", e);
  }
}

// Update Dashboard UI Elements
function updateUI() {
  // Update fields
  document.getElementById("fieldVendor").textContent = currentInvoice.vendor_name;
  document.getElementById("fieldInvoiceId").textContent = currentInvoice.invoice_id;
  document.getElementById("fieldDate").textContent = currentInvoice.invoice_date;

  const symbol = currentInvoice.currency === "INR" ? "₹" : (currentInvoice.currency === "EUR" ? "€" : "$");
  document.getElementById("fieldAmount").textContent = `${symbol}${currentInvoice.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;

  // Update confidence badge
  const confBadge = document.getElementById("confidenceBadge");
  const confPercent = (currentInvoice.confidence_score * 100).toFixed(0);
  confBadge.textContent = `Confidence: ${confPercent}%`;
  if (currentInvoice.confidence_score >= 0.8) {
    confBadge.style.background = "rgba(16, 185, 129, 0.15)";
    confBadge.style.color = "#34d399";
  } else if (currentInvoice.confidence_score >= 0.65) {
    confBadge.style.background = "rgba(245, 158, 11, 0.15)";
    confBadge.style.color = "#fbbf24";
  } else {
    confBadge.style.background = "rgba(239, 68, 68, 0.15)";
    confBadge.style.color = "#f87171";
  }

  // Update Engine badge
  if (currentInvoice.extraction_engine) {
    document.getElementById("engineBadge").textContent = currentInvoice.extraction_engine;
  }

  // Update Routing Banner
  const banner = document.getElementById("routingBanner");
  const title = document.getElementById("routingStatusTitle");
  const reason = document.getElementById("routingStatusReason");
  const actions = document.getElementById("routingActions");

  banner.className = "routing-banner";

  if (currentInvoice.confidence_score < 0.65) {
    banner.classList.add("low-confidence");
    title.innerHTML = "🔴 Flagged: Low AI Confidence (< 65%)";
    reason.textContent = "OCR extraction did not meet quality thresholds. Manual verification required.";
    actions.style.display = "flex";
  } else if (currentInvoice.routing && currentInvoice.routing.requires_approval) {
    banner.classList.add("needs-approval");
    title.innerHTML = `🟡 Pending Approval (Threshold > ${currentInvoice.currency} ${currentInvoice.routing.threshold_applied.toLocaleString()})`;
    reason.textContent = currentInvoice.routing.reason;
    actions.style.display = "flex";
  } else {
    banner.classList.add("auto-approved");
    title.innerHTML = "🟢 Auto-Approved (Within Limits)";
    reason.textContent = currentInvoice.routing ? currentInvoice.routing.reason : "Passed all financial limits. Automatically logged.";
    actions.style.display = "none";
  }

  // Populate Line Items Table
  const tbody = document.getElementById("lineItemsTableBody");
  tbody.innerHTML = "";
  if (currentInvoice.line_items && currentInvoice.line_items.length > 0) {
    document.getElementById("lineItemCount").textContent = `${currentInvoice.line_items.length} items detected`;
    currentInvoice.line_items.forEach(item => {
      const tr = document.createElement("tr");
      const unit = item.unit_price != null ? `${symbol}${item.unit_price.toFixed(2)}` : "--";
      const amt = item.amount != null ? `${symbol}${item.amount.toFixed(2)}` : "--";
      tr.innerHTML = `
        <td>${item.description}</td>
        <td>${item.quantity || 1}</td>
        <td>${unit}</td>
        <td>${amt}</td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    document.getElementById("lineItemCount").textContent = "0 items";
    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-dim);">No individual line items parsed</td></tr>`;
  }
}

// Action Buttons: Approve, Reject, Save to DB
function setupActionButtons() {
  document.getElementById("btnApprove").addEventListener("click", () => {
    currentInvoice.status = "Approved";
    saveRecordToDB("Approved by Finance Manager via Teams/Outlook");
  });

  document.getElementById("btnReject").addEventListener("click", () => {
    currentInvoice.status = "Rejected";
    saveRecordToDB("Rejected: Vendor invoice amount mismatch");
  });

  document.getElementById("btnSaveAudit").addEventListener("click", () => {
    saveRecordToDB("Saved directly to Dataverse");
  });

  document.getElementById("btnRefreshAudit").addEventListener("click", loadAuditLogs);
}

// Save to Database
async function saveRecordToDB(remarks = "Automated processing") {
  try {
    const payload = {
      invoice_id: currentInvoice.invoice_id,
      vendor_name: currentInvoice.vendor_name,
      invoice_date: currentInvoice.invoice_date,
      total_amount: currentInvoice.total_amount,
      currency: currentInvoice.currency,
      status: currentInvoice.status || "Auto-Approved",
      confidence_score: currentInvoice.confidence_score,
      sender_email: "billing@" + currentInvoice.vendor_name.toLowerCase().replace(/[^a-z]/g, "") + ".com",
      approval_remarks: remarks
    };

    const res = await fetch("/api/v1/invoices/record", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      alert(`Success! Invoice ${currentInvoice.invoice_id} successfully recorded with status: ${currentInvoice.status}`);
      loadAuditLogs();
    }
  } catch (e) {
    alert("Failed to save audit record: " + e.message);
  }
}

// Fetch and Render Audit Logs
async function loadAuditLogs() {
  const tbody = document.getElementById("auditTableBody");
  try {
    const res = await fetch("/api/v1/invoices?limit=50");
    const data = await res.json();

    if (!data || data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; color: var(--text-dim); padding: 24px;">No records found. Click 'Save Record' to add one.</td></tr>`;
      return;
    }

    tbody.innerHTML = "";
    data.forEach(item => {
      const tr = document.createElement("tr");
      let badgeClass = "badge-auto";
      if (item.status === "Approved") badgeClass = "badge-approved";
      if (item.status === "Pending Approval" || item.status.includes("Flagged")) badgeClass = "badge-pending";
      if (item.status === "Rejected") badgeClass = "badge-rejected";

      const currSym = item.currency === "INR" ? "₹" : (item.currency === "EUR" ? "€" : "$");

      tr.innerHTML = `
        <td style="color: var(--text-dim);">#${item.id}</td>
        <td><strong>${item.invoice_id}</strong></td>
        <td>${item.vendor_name}</td>
        <td>${item.invoice_date}</td>
        <td style="font-weight: 600;">${currSym}${item.total_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
        <td><span class="badge ${badgeClass}">${item.status}</span></td>
        <td>${(item.confidence_score * 100).toFixed(0)}%</td>
        <td style="color: var(--text-muted); font-size: 0.78rem;">${item.approval_remarks || "--"}</td>
        <td style="color: var(--text-dim); font-size: 0.75rem;">${item.processed_at ? item.processed_at.split("T")[0] : "--"}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("Failed to load audit logs:", e);
  }
}

// Copy Code helper
window.copyCode = function(button) {
  const pre = button.parentElement.querySelector("pre");
  if (pre) {
    navigator.clipboard.writeText(pre.innerText).then(() => {
      const orig = button.innerText;
      button.innerText = "Copied!";
      setTimeout(() => button.innerText = orig, 1800);
    });
  }
};
