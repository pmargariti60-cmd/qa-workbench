const picker = document.querySelector("#profile");
const start = document.querySelector("#run");
const notice = document.querySelector("#notice");
const details = document.querySelector("#details");
const history = document.querySelector("#runs");
let profiles = [];

async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error);
  return data;
}

function element(tag, text, className) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

function link(text, href) {
  const node = element("a", text);
  node.href = href;
  node.target = "_blank";
  node.rel = "noopener noreferrer";
  return node;
}

function showProfile() {
  const profile = profiles.find((item) => item.name === picker.value);
  const target = document.querySelector("#target");
  target.replaceChildren(link(profile.url, profile.url));
  const source = document.querySelector("#source");
  source.hidden = !profile.repository;
  source.replaceChildren();
  if (profile.repository) {
    source.append(link("GitHub repository", profile.repository));
    if (profile.revision) source.append(" · " + profile.revision);
  }
}

function showRun(run) {
  const heading = element("h3", run.profile.name);
  const state = element("span", run.status.toUpperCase(), "status " + run.status);
  const time = new Date(run.started_at).toLocaleString();
  const metadata = element("p", [time, run.browser, run.profile.url].filter(Boolean).join(" · "), "metadata");
  details.replaceChildren(heading, state, metadata);
  if (run.profile.repository) {
    const source = element("p", "");
    source.append(link("GitHub repository", run.profile.repository));
    if (run.profile.revision) source.append(" · " + run.profile.revision);
    details.append(source);
  }
  if (run.error) details.append(element("pre", run.error));
  const checks = element("ul", "", "checks");
  for (const check of run.checks) {
    const row = element("li", "");
    row.append(element("span", check.status.toUpperCase(), "status " + check.status), check.name);
    if (check.detail) {
      const assertion = element("details", "");
      assertion.append(element("summary", "View assertion"), element("pre", check.detail));
      row.append(assertion);
    }
    if (check.screenshot) row.append(link("Open screenshot", "/evidence/" + run.id + "/" + check.screenshot));
    checks.append(row);
  }
  details.append(checks);
}

async function refreshHistory() {
  const runs = await api("/api/runs");
  document.querySelector("#empty").hidden = runs.length > 0;
  history.replaceChildren();
  for (const run of runs) {
    const entry = element("li", "");
    const label = [run.environment, run.status, run.passed + "/" + run.total,
      new Date(run.started_at).toLocaleString()].join(" · ");
    const button = element("button", label);
    button.addEventListener("click", async () => {
      try {
        showRun(await api("/api/runs/" + run.id));
        details.scrollIntoView({ block: "nearest" });
      } catch (error) {
        notice.textContent = error.message;
      }
    });
    entry.append(button);
    history.append(entry);
  }
  return runs;
}

picker.addEventListener("change", showProfile);
document.querySelector("#run-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  start.disabled = picker.disabled = true;
  notice.textContent = "Running browser checks…";
  try {
    const run = await api("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile: picker.value }),
    });
    showRun(run);
    notice.textContent = "Run complete.";
    await refreshHistory();
  } catch (error) {
    notice.textContent = error.message;
  } finally {
    start.disabled = picker.disabled = false;
  }
});

async function initialize() {
  const [loaded, runs] = await Promise.allSettled([api("/api/profiles"), refreshHistory()]);
  if (loaded.status === "fulfilled") {
    profiles = loaded.value;
    for (const profile of profiles) {
      const option = element("option", profile.name);
      option.value = profile.name;
      picker.append(option);
    }
    showProfile();
    picker.disabled = start.disabled = false;
  } else {
    notice.textContent = loaded.reason.message;
  }
  if (runs.status === "rejected" && !notice.textContent) {
    notice.textContent = runs.reason.message;
  }
}

initialize().catch((error) => { notice.textContent = error.message; });
