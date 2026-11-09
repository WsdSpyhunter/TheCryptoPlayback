// Cloudflare Worker: starts the newsletter draft jobs on time.
// GitHub's own schedule is best-effort and often hours late. This Worker runs on Cloudflare cron triggers
// (UTC) at 11:30-14:30 UTC on Mon/Wed/Fri/Sat and, when the clock in Chicago is 6:30-9:30 AM, asks GitHub to
// start the matching workflow (daily.yml Mon/Wed/Fri, weekly.yml Sat). The workflow's guard job
// (scripts/should_run.py) lets only one start per day actually generate an issue, so the later triggers are
// harmless backups. Secret: GITHUB_TOKEN (fine-grained, Actions read/write on this repo only).
const REPO = "WsdSpyhunter/TheCryptoPlayback";
const WORKFLOW = { Mon: "daily.yml", Wed: "daily.yml", Fri: "daily.yml", Sat: "weekly.yml" };

function chicagoNow(date) {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Chicago", weekday: "short", hour: "numeric", minute: "numeric", hour12: false,
  }).formatToParts(date).map((x) => [x.type, x.value]));
  return { weekday: p.weekday, hour: parseInt(p.hour, 10) % 24, minute: parseInt(p.minute, 10) };
}

async function dispatch(env, workflow) {
  const res = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "cryptoplayback-timer",
    },
    body: JSON.stringify({ ref: "main", inputs: { from_timer: "true" } }),
  });
  return `${workflow}: HTTP ${res.status}`;
}

export default {
  async scheduled(event, env, ctx) {
    const t = chicagoNow(new Date(event.scheduledTime));
    const workflow = WORKFLOW[t.weekday];
    // 6:30, 7:30, 8:30, 9:30 Central only (the UTC cron list is wider because of daylight saving)
    const inWindow = t.hour >= 6 && t.hour <= 9 && t.minute >= 25 && t.minute <= 40;
    if (!workflow || !inWindow) { console.log(`skip ${t.weekday} ${t.hour}:${t.minute}`); return; }
    console.log(await dispatch(env, workflow));
  },
  // Visiting the worker address only reports that it is alive; it never starts anything.
  async fetch() { return new Response("cryptoplayback timer: alive\n"); },
};
