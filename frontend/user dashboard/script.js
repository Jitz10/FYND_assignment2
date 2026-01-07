const API_BASE = window.location.origin;

const form = document.getElementById("review-form");
const websiteEl = document.getElementById("website");
const productEl = document.getElementById("product");
const ratingEl = document.getElementById("rating");
const feedbackEl = document.getElementById("feedback");
const submitBtn = document.getElementById("submit-btn");
const formHint = document.getElementById("form-hint");
const apiStatus = document.getElementById("api-status");
const insightsSection = document.getElementById("insights");
const insightsBody = document.getElementById("insights-body");
const insightsLoading = document.getElementById("insights-loading");
const insightSummaryUser = document.getElementById("insight-summary-user");
const insightSuggestionsUser = document.getElementById("insight-suggestions-user");
const insightRating = document.getElementById("insight-rating");
const insightClassification = document.getElementById("insight-classification");

const CATALOG = {
  "alpha-shop": ["alpha-phone", "alpha-case", "alpha-charge"],
  "beta-store": ["beta-laptop", "beta-mouse", "beta-bag"],
  "gamma-mart": ["gamma-watch", "gamma-band", "gamma-scale"],
};

function populateWebsites() {
  websiteEl.innerHTML = '<option value="" disabled selected>Select website</option>' +
    Object.keys(CATALOG).map((w) => `<option value="${w}">${w}</option>`).join("");
  productEl.innerHTML = '<option value="" disabled selected>Select product</option>';
}

function populateProducts(website) {
  const products = CATALOG[website] || [];
  productEl.innerHTML = '<option value="" disabled selected>Select product</option>' +
    products.map((p) => `<option value="${p}">${p}</option>`).join("");
}

async function checkHealth() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    const res = await fetch(`${API_BASE}/health`, { signal: controller.signal });
    clearTimeout(timeoutId);
    if (!res.ok) throw new Error("Health check failed");
    apiStatus.textContent = "API online";
    apiStatus.style.background = "rgba(34, 197, 94, 0.12)";
    apiStatus.style.borderColor = "rgba(34, 197, 94, 0.4)";
    apiStatus.style.color = "#bbf7d0";
  } catch (err) {
    apiStatus.textContent = err.name === 'AbortError' ? "API timeout" : "API offline";
    apiStatus.style.background = "rgba(239, 68, 68, 0.12)";
    apiStatus.style.borderColor = "rgba(239, 68, 68, 0.4)";
    apiStatus.style.color = "#fecdd3";
  }
}

function renderInsight(review) {
  if (!review) {
    console.error('No review data to render');
    return;
  }
  // Show insights content and hide loader
  insightsSection.hidden = false;
  insightsLoading.hidden = true;
  insightsBody.hidden = false;
  
  insightSummaryUser.textContent = review.ai_summary_user || "(no summary)";
  insightRating.textContent = review.rating ? `${review.rating}/5` : "—";
  insightClassification.textContent = review.classification || "—";
  const suggestionsUser = Array.isArray(review.ai_suggestions_user) ? review.ai_suggestions_user : [];
  insightSuggestionsUser.innerHTML = suggestionsUser.length
    ? suggestionsUser.map((s) => `<li>${escapeHtml(String(s))}</li>`).join("")
    : "<li>No suggestions available</li>";
  insightsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  
  // Validation
  const rating = Number(ratingEl.value);
  const feedback = feedbackEl.value.trim();
  const website = websiteEl.value;
  const product = productEl.value;
  
  if (!rating || rating < 1 || rating > 5) {
    formHint.textContent = "Please select a valid rating (1-5).";
    formHint.style.color = "#fca5a5";
    return;
  }
  if (!feedback || feedback.length < 3) {
    formHint.textContent = "Feedback must be at least 3 characters.";
    formHint.style.color = "#fca5a5";
    return;
  }
  if (!website || !product) {
    formHint.textContent = "Please select both website and product.";
    formHint.style.color = "#fca5a5";
    return;
  }

  // Show loading state
  submitBtn.disabled = true;
  submitBtn.textContent = "Submitting...";
  formHint.textContent = "";
  formHint.style.color = "";
  insightsSection.hidden = false;
  insightsLoading.hidden = false;
  insightsBody.hidden = true;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout
    
    const res = await fetch(`${API_BASE}/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating, feedback, website, product }),
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    if (!res.ok) {
      let errorMsg = "Request failed";
      try {
        const errorData = await res.json();
        errorMsg = errorData.detail || errorData.message || errorMsg;
      } catch {
        errorMsg = await res.text() || errorMsg;
      }
      throw new Error(errorMsg);
    }
    
    const data = await res.json();
    
    if (!data) {
      throw new Error("No data received from server");
    }
    
    // Minimum animation duration (1.5s) for smooth UX
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    renderInsight(data);
    formHint.textContent = "✓ Review submitted successfully!";
    formHint.style.color = "#86efac";
    
    // Reset form
    ratingEl.value = "";
    feedbackEl.value = "";
    websiteEl.value = "";
    productEl.innerHTML = '<option value="" disabled selected>Select product</option>';
    
  } catch (err) {
    insightsLoading.hidden = true;
    insightsBody.hidden = true;
    insightsSection.hidden = true;
    
    let userMessage = "An error occurred. Please try again.";
    
    if (err.name === 'AbortError') {
      userMessage = "Request timed out. Please check your connection and try again.";
    } else if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
      userMessage = "Network error. Please check your connection.";
    } else if (err.message) {
      userMessage = err.message.length > 100 ? "Server error. Please try again." : err.message;
    }
    
    formHint.textContent = `⚠ ${userMessage}`;
    formHint.style.color = "#fca5a5";
    console.error('Submit error:', err);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Submit Review";
  }
});

websiteEl.addEventListener("change", (e) => {
  try {
    populateProducts(e.target.value);
    productEl.value = "";
  } catch (err) {
    console.error('Error populating products:', err);
    productEl.innerHTML = '<option value="" disabled selected>Error loading products</option>';
  }
});

// Initialize on page load
populateWebsites();
insightsLoading.hidden = true;
insightsBody.hidden = true;
insightsSection.hidden = true;
checkHealth();