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

function formatDeterministicSummary(data) {
    const payload = {
        cohorts: data.cohorts ?? [],
        comparison: data.comparison ?? {},
        artifacts: data.artifacts ?? {},
    };
    return JSON.stringify(payload, null, 2);
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

async function runAnalysis() {
    const runButton = document.getElementById("runButton");
    const mode = document.getElementById("mode").value;
    const summaryEl = document.getElementById("summary");
    const hypothesisEl = document.getElementById("hypothesis");
    const criticEl = document.getElementById("critic");
    const criticVerdictEl = document.getElementById("criticVerdict");

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
            criticVerdictEl.innerText = `Verdict: ERROR`;
            criticEl.innerText = detail;
            renderArtifacts(null);
            return;
        }

        if (mode === "agent") {
            renderAgentOutput(data);
        } else {
            summaryEl.innerText = formatDeterministicSummary(data);
            hypothesisEl.innerText = data?.comparison?.hypothesis || "N/A";
            criticVerdictEl.className = "critic-verdict muted";
            criticVerdictEl.innerText = "N/A";
            criticEl.innerText = "N/A";
            resetAgentSecondary();
            renderArtifacts(data.artifacts || null);
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
        runButton.innerText = "Run";
    }
}
