// EduGenie Main Client Application Script

document.addEventListener("DOMContentLoaded", () => {
  // --- State Variables ---
  let uiLanguage = "en";
  let responseLanguage = "en";
  let activeTab = "ask";
  let selectedExplainLevel = "Beginner";
  let currentQuizData = null;
  let userQuizAnswers = {};

  // --- DOM Elements ---
  const uiLangSelect = document.getElementById("uiLangSelect");
  const aiLangSelect = document.getElementById("aiLangSelect");

  // Tab Cards & Tool Panes
  const tabCards = document.querySelectorAll(".tab-card");
  const toolPanes = document.querySelectorAll(".tool-pane");

  // Modal Elements
  const setupModal = document.getElementById("setupModal");
  const openModalBtn = document.getElementById("openModalBtn");
  const closeModalBtn = document.getElementById("closeModalBtn");

  // --- Initialization ---
  initEventListeners();
  updateUILanguage();

  function initEventListeners() {
    // Language Selectors
    if (uiLangSelect) {
      uiLangSelect.addEventListener("change", (e) => {
        uiLanguage = e.target.value;
        updateUILanguage();
      });
    }

    if (aiLangSelect) {
      aiLangSelect.addEventListener("change", (e) => {
        responseLanguage = e.target.value;
      });
    }

    // Modal Listeners
    if (openModalBtn && setupModal) {
      openModalBtn.addEventListener("click", () => setupModal.style.display = "flex");
    }
    if (closeModalBtn && setupModal) {
      closeModalBtn.addEventListener("click", () => setupModal.style.display = "none");
    }
    if (setupModal) {
      setupModal.addEventListener("click", (e) => {
        if (e.target === setupModal) setupModal.style.display = "none";
      });
    }

    // Tabs Switching
    tabCards.forEach((card) => {
      card.addEventListener("click", () => {
        const targetTab = card.getAttribute("data-tab");
        switchTab(targetTab);
      });
    });

    // Level Buttons for Explain Concept
    const levelBtns = document.querySelectorAll(".level-btn");
    levelBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        levelBtns.forEach((b) => b.classList.remove("selected"));
        btn.classList.add("selected");
        selectedExplainLevel = btn.getAttribute("data-level");
      });
    });

    // Example Prompt Pills
    const examplePills = document.querySelectorAll(".example-pill");
    examplePills.forEach((pill) => {
      pill.addEventListener("click", () => {
        const targetInputId = pill.getAttribute("data-input-id");
        const promptText = pill.getAttribute("data-text");
        const targetInput = document.getElementById(targetInputId);
        if (targetInput) {
          targetInput.value = promptText;
          targetInput.focus();
        }
      });
    });

    // Tool Form Submit Buttons
    document.getElementById("btnAsk")?.addEventListener("click", handleAskEduGenie);
    document.getElementById("btnExplain")?.addEventListener("click", handleExplainConcept);
    document.getElementById("btnQuiz")?.addEventListener("click", handleGenerateQuiz);
    document.getElementById("btnSummarize")?.addEventListener("click", handleSummarizeNotes);
    document.getElementById("btnPath")?.addEventListener("click", handleLearningPath);
  }

  // --- UI Translation Renderer ---
  function updateUILanguage() {
    const t = translations[uiLanguage] || translations.en;

    document.querySelectorAll("[data-t]").forEach((elem) => {
      const key = elem.getAttribute("data-t");
      if (t[key]) {
        elem.textContent = t[key];
      }
    });

    document.querySelectorAll("[data-t-placeholder]").forEach((elem) => {
      const key = elem.getAttribute("data-t-placeholder");
      if (t[key]) {
        elem.placeholder = t[key];
      }
    });
  }

  function switchTab(tabId) {
    activeTab = tabId;
    tabCards.forEach((c) => {
      if (c.getAttribute("data-tab") === tabId) {
        c.classList.add("active");
        c.setAttribute("aria-selected", "true");
      } else {
        c.classList.remove("active");
        c.setAttribute("aria-selected", "false");
      }
    });

    toolPanes.forEach((pane) => {
      if (pane.id === `pane-${tabId}`) {
        pane.classList.add("active");
      } else {
        pane.classList.remove("active");
      }
    });
  }

  // --- Helper UI Utilities ---
  function showLoading(prefix) {
    document.getElementById(`${prefix}-loading`).style.display = "block";
    document.getElementById(`${prefix}-results`).style.display = "none";
    document.getElementById(`${prefix}-error`).style.display = "none";
  }

  function hideLoading(prefix) {
    document.getElementById(`${prefix}-loading`).style.display = "none";
  }

  function showError(prefix, message, helpText) {
    hideLoading(prefix);
    const errBox = document.getElementById(`${prefix}-error`);
    const errText = document.getElementById(`${prefix}-error-text`);
    if (errBox && errText) {
      errText.innerHTML = `<strong>${message}</strong>${helpText ? `<br><small>${helpText}</small>` : ""}`;
      errBox.style.display = "block";
    }
  }

  function showResults(prefix) {
    hideLoading(prefix);
    document.getElementById(`${prefix}-error`).style.display = "none";
    const resBox = document.getElementById(`${prefix}-results`);
    resBox.style.display = "block";
    resBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // --- Tool 1: Ask EduGenie ---
  async function handleAskEduGenie() {
    const input = document.getElementById("askInput").value.trim();
    const t = translations[uiLanguage] || translations.en;
    if (!input) {
      alert(t.emptyInputWarn);
      return;
    }

    showLoading("ask");

    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: input, language: responseLanguage })
      });

      const data = await response.json();
      if (!response.ok) {
        showError("ask", data.detail || t.errorTitle, data.configurable_help);
        return;
      }

      document.getElementById("askResultAnswer").textContent = data.answer;
      document.getElementById("askResultExplanation").textContent = data.explanation;
      showResults("ask");
    } catch (err) {
      showError("ask", t.errorTitle, "Network connection error.");
    }
  }

  // --- Tool 2: Explain Concept ---
  async function handleExplainConcept() {
    const input = document.getElementById("explainInput").value.trim();
    const t = translations[uiLanguage] || translations.en;
    if (!input) {
      alert(t.emptyInputWarn);
      return;
    }

    showLoading("explain");

    try {
      const response = await fetch("/api/explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          concept: input,
          level: selectedExplainLevel,
          language: responseLanguage
        })
      });

      const data = await response.json();
      if (!response.ok) {
        showError("explain", data.detail || t.errorTitle, data.configurable_help);
        return;
      }

      document.getElementById("explainResultText").textContent = data.explanation;

      // Key takeaways list
      const takeawaysList = document.getElementById("explainTakeawaysList");
      takeawaysList.innerHTML = "";
      if (data.key_takeaways && data.key_takeaways.length > 0) {
        data.key_takeaways.forEach((point) => {
          const li = document.createElement("li");
          li.textContent = point;
          takeawaysList.appendChild(li);
        });
      }

      // Analogy
      const analogyBox = document.getElementById("explainAnalogyCard");
      if (data.analogy) {
        document.getElementById("explainAnalogyText").textContent = data.analogy;
        analogyBox.style.display = "block";
      } else {
        analogyBox.style.display = "none";
      }

      showResults("explain");
    } catch (err) {
      showError("explain", t.errorTitle, "Network connection error.");
    }
  }

  // --- Tool 3: Generate Quiz ---
  async function handleGenerateQuiz() {
    const input = document.getElementById("quizInput").value.trim();
    const t = translations[uiLanguage] || translations.en;
    if (!input) {
      alert(t.emptyInputWarn);
      return;
    }

    showLoading("quiz");
    userQuizAnswers = {};

    try {
      const response = await fetch("/api/quiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: input, language: responseLanguage })
      });

      const data = await response.json();
      if (!response.ok) {
        showError("quiz", data.detail || t.errorTitle, data.configurable_help);
        return;
      }

      currentQuizData = data;
      renderQuizQuestions(data);
      showResults("quiz");
    } catch (err) {
      showError("quiz", t.errorTitle, "Network connection error.");
    }
  }

  function renderQuizQuestions(data) {
    const container = document.getElementById("quizQuestionsContainer");
    const t = translations[uiLanguage] || translations.en;
    container.innerHTML = "";

    // Reset score area
    const scoreArea = document.getElementById("quizScoreArea");
    scoreArea.style.display = "none";

    data.questions.forEach((q, qIndex) => {
      const qCard = document.createElement("div");
      qCard.className = "quiz-card";

      qCard.innerHTML = `
        <div class="quiz-q-num">Question ${qIndex + 1} of 3</div>
        <div class="quiz-question">${escapeHTML(q.question)}</div>
        <div class="options-group" id="opt-group-${qIndex}">
          ${q.options.map((optText, oIndex) => `
            <label class="option-item" id="opt-label-${qIndex}-${oIndex}">
              <input type="radio" name="quiz_q_${qIndex}" value="${oIndex}" class="option-radio" data-q="${qIndex}" data-o="${oIndex}">
              <span class="option-text">${escapeHTML(optText)}</span>
            </label>
          `).join("")}
        </div>
        <div class="quiz-expl-box" id="expl-box-${qIndex}" style="display: none;">
          💡 <strong>Explanation:</strong> ${escapeHTML(q.explanation)}
        </div>
      `;

      container.appendChild(qCard);
    });

    // Add radio click handlers
    container.querySelectorAll(".option-radio").forEach((radio) => {
      radio.addEventListener("change", (e) => {
        const qIdx = parseInt(e.target.getAttribute("data-q"));
        const oIdx = parseInt(e.target.getAttribute("data-o"));
        userQuizAnswers[qIdx] = oIdx;
      });
    });

    // Submit Quiz Answers Button
    const actionsArea = document.createElement("div");
    actionsArea.style.marginTop = "1.5rem";
    actionsArea.innerHTML = `
      <button id="btnSubmitQuiz" class="btn-submit">
        <span>🎯</span> ${t.quizSubmitAnswers}
      </button>
    `;
    container.appendChild(actionsArea);

    document.getElementById("btnSubmitQuiz").addEventListener("click", evaluateQuiz);
  }

  function evaluateQuiz() {
    const t = translations[uiLanguage] || translations.en;
    if (!currentQuizData) return;

    // Validate that all 3 questions answered
    if (Object.keys(userQuizAnswers).length < 3) {
      alert(t.quizSelectWarning);
      return;
    }

    let score = 0;
    currentQuizData.questions.forEach((q, qIndex) => {
      const userChoice = userQuizAnswers[qIndex];
      const correctChoice = q.correct_index;

      if (userChoice === correctChoice) {
        score++;
      }

      // Highlight options
      q.options.forEach((_, oIndex) => {
        const labelElem = document.getElementById(`opt-label-${qIndex}-${oIndex}`);
        if (!labelElem) return;

        if (oIndex === correctChoice) {
          labelElem.classList.add("correct");
        }
        if (userChoice === oIndex && userChoice !== correctChoice) {
          labelElem.classList.add("incorrect");
        }
      });

      // Show explanation box
      const explBox = document.getElementById(`expl-box-${qIndex}`);
      if (explBox) explBox.style.display = "block";
    });

    // Render score banner
    const scoreArea = document.getElementById("quizScoreArea");
    scoreArea.innerHTML = `
      <div class="score-banner">
        <div class="score-number">${score} / 3 Correct!</div>
        <p style="margin-top: 0.5rem; color: #a5b4fc;">
          ${score === 3 ? "🎉 Outstanding! You mastered this topic." : score >= 2 ? "👍 Good effort! Review the explanations above." : "💪 Keep learning! Try review mode and re-quiz."}
        </p>
        <div style="margin-top: 1rem; display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap;">
          <button id="btnRetakeQuiz" class="btn-secondary">🔄 ${t.quizRetake}</button>
        </div>
      </div>
    `;
    scoreArea.style.display = "block";
    scoreArea.scrollIntoView({ behavior: "smooth" });

    // Retake Quiz Listener
    document.getElementById("btnRetakeQuiz")?.addEventListener("click", () => {
      userQuizAnswers = {};
      renderQuizQuestions(currentQuizData);
    });
  }

  // --- Tool 4: Summarize Notes ---
  async function handleSummarizeNotes() {
    const input = document.getElementById("summarizeInput").value.trim();
    const t = translations[uiLanguage] || translations.en;
    if (!input || input.length < 10) {
      alert(t.emptyInputWarn);
      return;
    }

    showLoading("summarize");

    try {
      const response = await fetch("/api/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: input, language: responseLanguage })
      });

      const data = await response.json();
      if (!response.ok) {
        showError("summarize", data.detail || t.errorTitle, data.configurable_help);
        return;
      }

      document.getElementById("summarizeText").textContent = data.summary;

      // Copy summary listener
      const copyBtn = document.getElementById("btnCopySummary");
      if (copyBtn) {
        copyBtn.onclick = () => {
          navigator.clipboard.writeText(data.summary);
          copyBtn.textContent = t.copiedMsg;
          setTimeout(() => copyBtn.textContent = t.copyBtn, 2000);
        };
      }

      // Key points
      const keyPointsList = document.getElementById("summarizeKeyPoints");
      keyPointsList.innerHTML = "";
      (data.key_points || []).forEach((pt) => {
        const li = document.createElement("li");
        li.textContent = pt;
        keyPointsList.appendChild(li);
      });

      // Important terms grid
      const termsGrid = document.getElementById("summarizeTermsGrid");
      termsGrid.innerHTML = "";
      if (data.important_terms && data.important_terms.length > 0) {
        data.important_terms.forEach((tItem) => {
          const card = document.createElement("div");
          card.className = "term-card";
          card.innerHTML = `
            <div class="term-name">${escapeHTML(tItem.term)}</div>
            <div class="term-def">${escapeHTML(tItem.definition)}</div>
          `;
          termsGrid.appendChild(card);
        });
        document.getElementById("summarizeTermsCard").style.display = "block";
      } else {
        document.getElementById("summarizeTermsCard").style.display = "none";
      }

      showResults("summarize");
    } catch (err) {
      showError("summarize", t.errorTitle, "Network connection error.");
    }
  }

  // --- Tool 5: Create Learning Path ---
  async function handleLearningPath() {
    const input = document.getElementById("pathInput").value.trim();
    const t = translations[uiLanguage] || translations.en;
    if (!input) {
      alert(t.emptyInputWarn);
      return;
    }

    showLoading("path");

    try {
      const response = await fetch("/api/learning-path", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: input, language: responseLanguage })
      });

      const data = await response.json();
      if (!response.ok) {
        showError("path", data.detail || t.errorTitle, data.configurable_help);
        return;
      }

      document.getElementById("pathOverviewText").textContent = data.overview;

      // Modules Timeline
      const modulesContainer = document.getElementById("pathModulesContainer");
      modulesContainer.innerHTML = "";
      (data.modules || []).forEach((mod, idx) => {
        const mCard = document.createElement("div");
        mCard.className = "module-card";
        mCard.innerHTML = `
          <div class="module-header">
            <span class="module-title">${escapeHTML(mod.title)}</span>
            <span class="module-badge">${escapeHTML(mod.level)} • ${escapeHTML(mod.estimated_hours)}</span>
          </div>
          <ul class="bullet-list">
            ${(mod.topics || []).map((tp) => `<li>${escapeHTML(tp)}</li>`).join("")}
          </ul>
        `;
        modulesContainer.appendChild(mCard);
      });

      // Milestones List
      const milestonesList = document.getElementById("pathMilestonesList");
      milestonesList.innerHTML = "";
      (data.milestones || []).forEach((ms) => {
        const li = document.createElement("li");
        li.textContent = ms;
        milestonesList.appendChild(li);
      });

      // Resource Suggestions
      const resourcesContainer = document.getElementById("pathResourcesContainer");
      resourcesContainer.innerHTML = "";
      (data.resource_suggestions || []).forEach((r) => {
        const rItem = document.createElement("div");
        rItem.className = "resource-item";
        rItem.innerHTML = `
          <div class="resource-info">
            <span class="resource-name">${escapeHTML(r.name)}</span>
            <span class="resource-desc">${escapeHTML(r.description)}</span>
          </div>
          <span class="resource-type-tag">${escapeHTML(r.type)}</span>
        `;
        resourcesContainer.appendChild(rItem);
      });

      showResults("path");
    } catch (err) {
      showError("path", t.errorTitle, "Network connection error.");
    }
  }

  function escapeHTML(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
