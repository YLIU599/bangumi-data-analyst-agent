function buildRequestBody() {
    return {
        season_a: {
            year: parseInt(document.getElementById("yearA").value, 10),
            season: document.getElementById("seasonA").value.trim().toLowerCase(),
        },
        season_b: {
            year: parseInt(document.getElementById("yearB").value, 10),
            season: document.getElementById("seasonB").value.trim().toLowerCase(),
        },
        page_limit: 4,
        per_page: 25,
        top_n: 5,
        min_rating_total: 30,
    };
}

function applyPreset(yearA, seasonA, yearB, seasonB, mode) {
    document.getElementById("yearA").value = yearA;
    document.getElementById("seasonA").value = seasonA;
    document.getElementById("yearB").value = yearB;
    document.getElementById("seasonB").value = seasonB;
    document.getElementById("mode").value = mode;
    document.getElementById("questionYear").value = yearA;
    updateHeaderState();
    updateQuestionTemplates();
}

function fillChatQuestion(text) {
    document.getElementById("chatInput").value = text;
}

function getSelectedBuilderYear() {
    return document.getElementById("questionYear").value.trim() || "2025";
}

function getSelectedBuilderSeason() {
    return document.getElementById("questionSeason").value.trim().toLowerCase() || "spring";
}

function getTemplateQuestion(kind) {
    const year = getSelectedBuilderYear();
    const season = getSelectedBuilderSeason();

    if (kind === "popularity") {
        return `Which season was more popular in ${year}?`;
    }
    if (kind === "score") {
        return `Which season had the highest average score in ${year}?`;
    }
    if (kind === "yearTopRated") {
        return `What are the top rated anime in ${year}?`;
    }
    if (kind === "yearMostPopular") {
        return `What are the most popular anime in ${year}?`;
    }
    if (kind === "seasonTopRated") {
        return `What are the top rated anime in ${season} ${year}?`;
    }
    if (kind === "seasonMostPopular") {
        return `What are the most popular anime in ${season} ${year}?`;
    }
    return "";
}

function updateQuestionTemplates() {
    document.getElementById("templatePopularity").innerText = getTemplateQuestion("popularity");
    document.getElementById("templateScore").innerText = getTemplateQuestion("score");
    document.getElementById("templateYearTopRated").innerText = getTemplateQuestion("yearTopRated");
    document.getElementById("templateYearMostPopular").innerText = getTemplateQuestion("yearMostPopular");
    document.getElementById("templateSeasonTopRated").innerText = getTemplateQuestion("seasonTopRated");
    document.getElementById("templateSeasonMostPopular").innerText = getTemplateQuestion("seasonMostPopular");
}

function submitTemplateQuestion(kind) {
    const question = getTemplateQuestion(kind);
    fillChatQuestion(question);
    submitChatQuestion();
}

function normalizePath(path) {
    if (!path) {
        return "";
    }
    if (path.startsWith("/outputs/")) {
        return path;
    }
    if (path.startsWith("outputs/")) {
        return `/${path}`;
    }
    return path.startsWith("/") ? path : `/${path}`;
}

function updateHeaderState() {
    const yearA = document.getElementById("yearA").value;
    const seasonA = document.getElementById("seasonA").value;
    const yearB = document.getElementById("yearB").value;
    const seasonB = document.getElementById("seasonB").value;
    const mode = document.getElementById("mode").value;

    document.getElementById("currentPair").innerText = `${yearA} ${seasonA} vs ${yearB} ${seasonB}`;
    document.getElementById("currentMode").innerText = mode === "agent" ? "Agent" : "Deterministic";
}

function renderArtifacts(artifacts) {
    const container = document.getElementById("artifacts");
    container.innerHTML = "";

    if (!artifacts || typeof artifacts !== "object") {
        container.innerText = "No artifacts returned.";
        return;
    }

    const entries = Object.entries(artifacts);
    if (entries.length === 0) {
        container.innerText = "No artifacts returned.";
        return;
    }

    for (const [key, rawPath] of entries) {
        const item = document.createElement("div");
        item.className = "artifact-item";

        const title = document.createElement("div");
        title.innerHTML = `<strong>${key}</strong>`;
        item.appendChild(title);

        if (typeof rawPath === "string" && rawPath.length > 0) {
            const normalized = normalizePath(rawPath);

            const link = document.createElement("a");
            link.href = normalized;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.innerText = rawPath;
            item.appendChild(link);

            if (key === "scatter_plot_png" || rawPath.toLowerCase().endsWith(".png")) {
                const img = document.createElement("img");
                img.src = normalized;
                img.alt = key;
                img.className = "artifact-preview";
                item.appendChild(img);
            }
        } else {
            const empty = document.createElement("div");
            empty.innerText = "N/A";
            item.appendChild(empty);
        }

        container.appendChild(item);
    }
}

function setCriticVerdict(verdict) {
    const verdictEl = document.getElementById("criticVerdict");
    const normalized = (verdict || "UNKNOWN").toUpperCase();

    verdictEl.className = "critic-verdict";
    if (normalized === "PASS") {
        verdictEl.classList.add("pass");
    } else if (normalized === "REVISE") {
        verdictEl.classList.add("revise");
    } else {
        verdictEl.classList.add("unknown");
    }
    verdictEl.innerText = `Verdict: ${normalized}`;
}

function resetAgentSecondary() {
    const detailsEl = document.getElementById("orchestratorDetails");
    const outputEl = document.getElementById("orchestratorOutput");
    detailsEl.hidden = true;
    detailsEl.open = false;
    outputEl.innerText = "N/A";
}

function renderDeterministicOutput(data) {
    const summaryEl = document.getElementById("summary");
    const hypothesisEl = document.getElementById("hypothesis");
    const criticEl = document.getElementById("critic");

    const cohorts = Array.isArray(data.cohorts) ? data.cohorts : [];
    const comparison = data.comparison || {};
    const a = cohorts[0] || {};
    const b = cohorts[1] || {};

    const lines = [];
    if (a.season_label && b.season_label) {
        lines.push(`Compared ${a.season_label} against ${b.season_label}.`);
    }
    if (a.n_titles != null && b.n_titles != null) {
        lines.push(`Titles: ${a.n_titles} vs ${b.n_titles}.`);
    }
    if (a.avg_score != null && b.avg_score != null) {
        lines.push(`Average score: ${Number(a.avg_score).toFixed(2)} vs ${Number(b.avg_score).toFixed(2)}.`);
    }
    if (a.avg_rating_total != null && b.avg_rating_total != null) {
        lines.push(`Average rating total: ${Number(a.avg_rating_total).toFixed(2)} vs ${Number(b.avg_rating_total).toFixed(2)}.`);
    }
    if (comparison.higher_scoring_season) {
        lines.push(`Higher-scoring season: ${comparison.higher_scoring_season}.`);
    }
    if (comparison.higher_popularity_season) {
        lines.push(`Higher-popularity season: ${comparison.higher_popularity_season}.`);
    }
    if (comparison.hypothesis) {
        lines.push("");
        lines.push(`Takeaway: ${comparison.hypothesis}`);
    }

    summaryEl.innerText = lines.join("\n");
    hypothesisEl.innerText = comparison.hypothesis || "N/A";

    document.getElementById("criticVerdict").className = "critic-verdict muted";
    document.getElementById("criticVerdict").innerText = "N/A";
    criticEl.innerText = "Critic check is only shown for Agent mode.";

    document.getElementById("orchestratorDetails").hidden = false;
    document.getElementById("orchestratorOutput").innerText = JSON.stringify(
        {
            cohorts: data.cohorts ?? [],
            comparison: data.comparison ?? {},
            artifacts: data.artifacts ?? {},
        },
        null,
        2
    );

    renderArtifacts(data.artifacts || null);
}

function renderAgentOutput(data) {
    const summaryEl = document.getElementById("summary");
    const hypothesisEl = document.getElementById("hypothesis");
    const criticEl = document.getElementById("critic");
    const detailsEl = document.getElementById("orchestratorDetails");
    const outputEl = document.getElementById("orchestratorOutput");

    summaryEl.innerText = data.final_report || "N/A";
    hypothesisEl.innerText = data.final_report || "N/A";
    setCriticVerdict(data.critic_verdict || "UNKNOWN");
    criticEl.innerText = data.critic_feedback || "N/A";

    if (data.orchestrator_output) {
        detailsEl.hidden = false;
        outputEl.innerText = data.orchestrator_output;
    } else {
        resetAgentSecondary();
    }

    renderArtifacts(data.artifacts || null);
}

function renderTitleCards(titles) {
    if (!titles || titles.length === 0) {
        return "";
    }

    const cards = titles.map((title) => {
        const name = title.name_cn || title.name;
        const extras = [];
        if (title.season_label) extras.push(title.season_label);
        if (title.score != null) extras.push(`score ${Number(title.score).toFixed(2)}`);
        if (title.rating_total != null) extras.push(`rating total ${title.rating_total}`);
        if (title.gap != null) extras.push(`gap ${Number(title.gap).toFixed(2)}`);
        return `
            <article class="title-card">
                ${title.image_url ? `<img src="${title.image_url}" alt="${name}">` : ""}
                <div class="title-card-body">
                    <div class="title-card-title">${name}</div>
                    <div class="title-card-meta">${extras.join(" · ")}</div>
                </div>
            </article>
        `;
    }).join("");

    return `<div class="chat-title-grid">${cards}</div>`;
}

function appendChatMessage(role, text, evidence = [], titles = []) {
    const thread = document.getElementById("chatThread");
    const wrapper = document.createElement("div");
    wrapper.className = `chat-message ${role === "user" ? "user-message" : "assistant-message"}`;

    const roleLabel = role === "user" ? "You" : "Analyst Copilot";
    const evidenceHtml = evidence.length > 0
        ? `<ul class="chat-evidence">${evidence.map((item) => `<li>${item}</li>`).join("")}</ul>`
        : "";

    wrapper.innerHTML = `
        <div class="chat-role">${roleLabel}</div>
        <div class="chat-bubble">
            <div>${text}</div>
            ${evidenceHtml}
            ${renderTitleCards(titles)}
        </div>
    `;

    thread.appendChild(wrapper);
    thread.scrollTop = thread.scrollHeight;
}

async function submitChatQuestion() {
    const input = document.getElementById("chatInput");
    const chatButton = document.getElementById("chatButton");
    const message = input.value.trim();

    if (!message) {
        return;
    }

    appendChatMessage("user", message);
    input.value = "";
    chatButton.disabled = true;
    chatButton.innerText = "Asking...";

    try {
        const res = await fetch("/api/v1/chat/season-gap", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message,
                current_request: buildRequestBody(),
            }),
        });

        const data = await res.json();
        if (!res.ok) {
            appendChatMessage("assistant", `Request failed (${res.status}).`, [JSON.stringify(data, null, 2)]);
            return;
        }

        appendChatMessage("assistant", data.answer || "N/A", data.evidence || [], data.suggested_titles || []);
    } catch (error) {
        appendChatMessage("assistant", "The chat request failed.", [String(error)]);
    } finally {
        chatButton.disabled = false;
        chatButton.innerText = "Ask";
    }
}

async function runAnalysis() {
    const runButton = document.getElementById("runButton");
    const mode = document.getElementById("mode").value;
    const summaryEl = document.getElementById("summary");
    const hypothesisEl = document.getElementById("hypothesis");
    const criticEl = document.getElementById("critic");
    const criticVerdictEl = document.getElementById("criticVerdict");

    updateHeaderState();

    const url = mode === "agent"
        ? "/api/v1/agent/season-gap"
        : "/api/v1/analysis/season-gap";

    const body = buildRequestBody();

    runButton.disabled = true;
    runButton.innerText = "Running...";
    summaryEl.innerText = "Loading...";
    hypothesisEl.innerText = "Loading...";
    criticEl.innerText = "Loading...";
    criticVerdictEl.className = "critic-verdict muted";
    criticVerdictEl.innerText = "Loading...";
    resetAgentSecondary();
    document.getElementById("artifacts").innerHTML = "";

    try {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        const data = await res.json();

        if (!res.ok) {
            const detail = data?.detail ? JSON.stringify(data.detail, null, 2) : JSON.stringify(data, null, 2);
            summaryEl.innerText = `Request failed (${res.status})`;
            hypothesisEl.innerText = "N/A";
            criticVerdictEl.className = "critic-verdict unknown";
            criticVerdictEl.innerText = "Verdict: ERROR";
            criticEl.innerText = detail;
            renderArtifacts(null);
            return;
        }

        if (mode === "agent") {
            renderAgentOutput(data);
        } else {
            renderDeterministicOutput(data);
        }
    } catch (error) {
        summaryEl.innerText = "Request failed.";
        hypothesisEl.innerText = "N/A";
        criticVerdictEl.className = "critic-verdict unknown";
        criticVerdictEl.innerText = "Verdict: ERROR";
        criticEl.innerText = String(error);
        renderArtifacts(null);
    } finally {
        runButton.disabled = false;
        runButton.innerText = "Run Analysis";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    updateHeaderState();
    updateQuestionTemplates();

    document.getElementById("yearA").addEventListener("change", updateHeaderState);
    document.getElementById("seasonA").addEventListener("change", updateHeaderState);
    document.getElementById("yearB").addEventListener("change", updateHeaderState);
    document.getElementById("seasonB").addEventListener("change", updateHeaderState);
    document.getElementById("mode").addEventListener("change", updateHeaderState);
    document.getElementById("questionYear").addEventListener("input", updateQuestionTemplates);
    document.getElementById("questionSeason").addEventListener("change", updateQuestionTemplates);

    document.getElementById("chatInput").addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submitChatQuestion();
        }
    });
});
