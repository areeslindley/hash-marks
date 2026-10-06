const LIVE_SEASON = 2026;
const HOLDOUT_SEASON = 2025;

let metaCache = null;
let liveGamesCache = null;
let currentSection = "home";
let matchesPage = 1;

function isStaticMode() {
    return Boolean(window.STATIC_META_URL);
}

async function fetchJson(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`${url} (${response.status})`);
    }
    return response.json();
}

async function ensureMeta() {
    if (metaCache) {
        return metaCache;
    }
    metaCache = isStaticMode()
        ? await fetchJson(window.STATIC_META_URL)
        : await fetchJson("/api/meta");
    return metaCache;
}

async function ensureLiveGames() {
    if (liveGamesCache) {
        return liveGamesCache;
    }
    if (isStaticMode()) {
        liveGamesCache = await fetchJson(window.STATIC_LIVE_GAMES_URL);
    }
    return liveGamesCache;
}

function fmt(value, digits = 0) {
    if (value == null || Number.isNaN(Number(value))) {
        return "—";
    }
    return Number(value).toFixed(digits);
}

function kpiHtml(label, value, sub) {
    return `<div class="col-6 col-md-3"><div class="kpi"><span class="kpi-label">${label}</span><span class="kpi-value">${value}</span><span class="kpi-sub">${sub || ""}</span></div></div>`;
}

function scoreLine(row) {
    if (row.home_points == null || row.away_points == null) {
        return "—";
    }
    return `<span class="score-line">${row.away_points}<span class="score-sep">–</span>${row.home_points}</span>`;
}

function statusPill(status) {
    const klass = status === "Finished" ? "finished" : "scheduled";
    return `<span class="status-pill ${klass}">${status}</span>`;
}

function gameRow(row) {
    const line = row.spread_line == null ? "—" : (Number(row.spread_line) > 0 ? `+${fmt(row.spread_line, 1)}` : fmt(row.spread_line, 1));
    return `<tr class="match-row">
        <td>${row.gameday || "—"}</td>
        <td>W${row.week ?? "—"}</td>
        <td>${row.away_team} at ${row.home_team}</td>
        <td>${scoreLine(row)}</td>
        <td>${line}</td>
        <td>${statusPill(row.status)}</td>
    </tr>`;
}

function gameTable(rows) {
    if (!rows.length) {
        return '<p class="coverage-note mb-0">No games in this cut.</p>';
    }
    return `<div class="table-responsive"><table class="table"><thead><tr><th>Date</th><th>Wk</th><th>Match</th><th>Score</th><th>Spread</th><th></th></tr></thead><tbody>${rows.map(gameRow).join("")}</tbody></table></div>`;
}

function showSection(name) {
    document.querySelectorAll(".content-section").forEach((node) => {
        node.style.display = node.id === name ? "" : "none";
    });
    document.querySelectorAll("[data-section]").forEach((link) => {
        link.classList.toggle("active", link.getAttribute("data-section") === name);
    });
    currentSection = name;
}

function filterStaticGames(games, filters) {
    return games.filter((row) => {
        if (filters.season && Number(row.season) !== Number(filters.season)) {
            return false;
        }
        if (filters.week && Number(row.week) !== Number(filters.week)) {
            return false;
        }
        if (filters.status && row.status !== filters.status) {
            return false;
        }
        if (filters.q) {
            const blob = `${row.away_team} ${row.home_team} ${row.venue || ""}`.toLowerCase();
            if (!blob.includes(filters.q.toLowerCase())) {
                return false;
            }
        }
        return true;
    });
}

async function loadHome() {
    const meta = await ensureMeta();
    const c0 = meta.c0 || {};
    document.getElementById("home-kpis").innerHTML = [
        kpiHtml("Games", fmt(meta.n_games, 0), `${meta.season_min}–${meta.season_max} private`),
        kpiHtml("Public window", fmt(meta.n_pages_games, 0), `${(meta.pages_game_seasons || []).join("–")}`),
        kpiHtml("Live", String(meta.live_season), meta.hosting ? "FBS only" : ""),
        kpiHtml("C0 n", c0.n != null ? fmt(c0.n, 0) : "—", c0.registered ? "registered" : "probe only"),
    ].join("");
    const c0Note = document.getElementById("home-c0-note");
    if (c0.home_cover_rate != null) {
        c0Note.textContent = `Probe ATS (home) ${fmt(c0.home_cover_rate * 100, 1)}% on ${c0.n_decided} both-FBS games. MAE ${fmt(c0.mae, 2)}. Not a ledger test.`;
    }
}

async function loadSeason() {
    const meta = await ensureMeta();
    const payload = isStaticMode()
        ? await fetchJson(window.STATIC_SEASON_LIVE_URL)
        : await fetchJson(`/api/season/${meta.live_season}`);
    document.getElementById("season-lede").textContent =
        `${payload.season} · ${payload.era} · ${payload.teams} FBS teams`;
    document.getElementById("season-kpis").innerHTML = [
        kpiHtml("Games", fmt(payload.n, 0), `${payload.finished} finished`),
        kpiHtml("Scheduled", fmt(payload.scheduled, 0), payload.min_date || ""),
        kpiHtml("Mean total", payload.mean_total != null ? fmt(payload.mean_total, 1) : "—", "finished"),
        kpiHtml("Postseason", fmt(payload.post, 0), `${payload.reg} regular`),
    ].join("");
    const weeks = payload.weeks || [];
    document.getElementById("season-weeks").innerHTML = weeks.length
        ? `<div class="table-responsive"><table class="table"><thead><tr><th>Week</th><th>Games</th><th>Finished</th><th>Pts/G</th></tr></thead><tbody>${weeks.map((week) => `<tr><td>W${week.week}</td><td>${week.n}</td><td>${week.finished}</td><td>${week.points_per_game ?? "—"}</td></tr>`).join("")}</tbody></table></div>`
        : '<p class="coverage-note mb-0">No weeks yet.</p>';
    document.getElementById("season-latest").innerHTML = gameTable(payload.latest || []);
    document.getElementById("season-upcoming").innerHTML = gameTable(payload.upcoming || []);
}

async function loadMatches() {
    const meta = await ensureMeta();
    const seasonSelect = document.getElementById("filter-season");
    if (!seasonSelect.options.length) {
        const seasons = isStaticMode()
            ? (meta.pages_game_seasons || [HOLDOUT_SEASON, LIVE_SEASON])
            : (meta.seasons || []).slice().reverse();
        seasonSelect.innerHTML = seasons.map((season) =>
            `<option value="${season}" ${Number(season) === Number(meta.live_season) ? "selected" : ""}>${season}</option>`
        ).join("");
    }
    const filters = {
        season: seasonSelect.value,
        week: document.getElementById("filter-week").value,
        status: document.getElementById("filter-status").value,
        q: document.getElementById("filter-q").value,
    };
    let rows;
    let pagination = { page: 1, pages: 1, total: 0 };
    if (isStaticMode()) {
        const all = filterStaticGames(await ensureLiveGames(), filters).reverse();
        const perPage = 25;
        pagination.total = all.length;
        pagination.pages = Math.max(1, Math.ceil(all.length / perPage));
        pagination.page = Math.min(matchesPage, pagination.pages);
        const start = (pagination.page - 1) * perPage;
        rows = all.slice(start, start + perPage);
        document.getElementById("matches-lede").textContent =
            `Public snapshot: ${meta.pages_game_seasons.join(" and ")} only. Open Flask for 2001–present.`;
    } else {
        const params = new URLSearchParams({ page: String(matchesPage), per_page: "25" });
        if (filters.season) params.set("season", filters.season);
        if (filters.week) params.set("week", filters.week);
        if (filters.status) params.set("status", filters.status);
        if (filters.q) params.set("q", filters.q);
        const payload = await fetchJson(`/api/games?${params}`);
        rows = payload.data;
        pagination = payload.pagination;
    }
    document.getElementById("matches-table").innerHTML =
        `${gameTable(rows)}<p class="coverage-note mt-3 mb-0">Page ${pagination.page} of ${pagination.pages} · ${pagination.total} games</p>`;
}

async function loadTeams() {
    const meta = await ensureMeta();
    const select = document.getElementById("teams-season");
    if (!select.options.length) {
        const seasons = isStaticMode()
            ? (meta.pages_game_seasons || [])
            : (meta.seasons || []).slice().reverse();
        select.innerHTML = seasons.map((season) =>
            `<option value="${season}" ${Number(season) === Number(meta.live_season) ? "selected" : ""}>${season}</option>`
        ).join("");
    }
    const season = Number(select.value || meta.live_season);
    let teams;
    if (isStaticMode()) {
        const games = (await ensureLiveGames()).filter((row) => Number(row.season) === season);
        const byTeam = new Map();
        for (const row of games) {
            for (const side of [
                { name: row.home_team, conference: row.home_conference, division: row.home_division, scored: row.home_points, allowed: row.away_points },
                { name: row.away_team, conference: row.away_conference, division: row.away_division, scored: row.away_points, allowed: row.home_points },
            ]) {
                if ((side.division || "").toLowerCase() !== "fbs") {
                    continue;
                }
                const item = byTeam.get(side.name) || { name: side.name, conference: side.conference, wins: 0, losses: 0, ties: 0, n: 0 };
                item.n += 1;
                if (side.scored != null && side.allowed != null) {
                    if (side.scored > side.allowed) item.wins += 1;
                    else if (side.scored < side.allowed) item.losses += 1;
                    else item.ties += 1;
                }
                byTeam.set(side.name, item);
            }
        }
        teams = Array.from(byTeam.values());
    } else {
        teams = (await fetchJson(`/api/teams?season=${season}`)).teams;
    }
    const grouped = new Map();
    for (const team of teams) {
        const key = team.conference || "Independent";
        if (!grouped.has(key)) grouped.set(key, []);
        grouped.get(key).push(team);
    }
    document.getElementById("teams-grid").innerHTML = Array.from(grouped.entries()).map(([conference, members]) => `
        <div class="division-block">
            <h3>${conference}</h3>
            <div class="row g-2">${members.map((team) => `
                <div class="col-md-3 col-sm-6">
                    <div class="team-tile">
                        <strong>${team.name}</strong>
                        <span class="record">${team.record || `${team.wins}-${team.losses}-${team.ties || 0}`}</span>
                    </div>
                </div>`).join("")}
            </div>
        </div>`).join("");
}

async function loadStructure() {
    const payload = isStaticMode()
        ? await fetchJson(window.STATIC_STRUCTURE_URL)
        : await fetchJson("/api/structure");
    document.getElementById("structure-tree").innerHTML = (payload.conferences || []).map((conference) => `
        <section class="cfb-conf">
            <h3>${conference.conference} <span class="era-pill">${conference.n}</span></h3>
            ${(conference.teams || []).map((team) => `<div class="tree-team mb-1"><span class="tree-team-name">${team.name}</span><span class="tree-team-record">${team.record}</span></div>`).join("")}
        </section>`).join("");
}

async function loadYears() {
    const rows = isStaticMode()
        ? await fetchJson(window.STATIC_SEASONS_URL)
        : await fetchJson("/api/years");
    document.getElementById("years-table").innerHTML = `<div class="table-responsive"><table class="table"><thead><tr><th>Season</th><th>Era</th><th>Games</th><th>Finished</th><th>Reg</th><th>Post</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${row.season}</td><td>${row.era}</td><td>${row.n}</td><td>${row.finished}</td><td>${row.reg}</td><td>${row.post}</td></tr>`).join("")}</tbody></table></div>`;
}

async function loadSection(name) {
    showSection(name);
    if (name === "home") await loadHome();
    if (name === "dashboard") await loadSeason();
    if (name === "matches") await loadMatches();
    if (name === "teams") await loadTeams();
    if (name === "structure") await loadStructure();
    if (name === "years") await loadYears();
}

document.addEventListener("click", (event) => {
    const link = event.target.closest("[data-section]");
    if (!link) {
        return;
    }
    event.preventDefault();
    matchesPage = 1;
    loadSection(link.getAttribute("data-section"));
});

document.addEventListener("DOMContentLoaded", () => {
    const go = document.getElementById("filter-go");
    if (go) {
        go.addEventListener("click", () => {
            matchesPage = 1;
            loadMatches();
        });
    }
    const teamsSeason = document.getElementById("teams-season");
    if (teamsSeason) {
        teamsSeason.addEventListener("change", loadTeams);
    }
    loadSection("home");
});
