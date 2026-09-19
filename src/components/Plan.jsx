import React from "react";
import {
  CalendarDays,
  Users,
  Download,
  CloudSun,
  ArrowUpRight,
  ShieldCheck,
  Leaf,
} from "lucide-react";
import { money } from "../lib/api";

export default function Plan({ plan, tab, setTab, checked, setChecked }) {
  const p = plan.profile;
  const packed = plan.packing.filter((_, index) => checked[index]).length;
  function download() {
    const blob = new Blob([JSON.stringify(plan, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "roam-itinerary.json";
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <aside className="plan-panel">
      <div className="plan-heading">
        <div>
          <span className="eyebrow green">YOUR NEXT CHAPTER</span>
          <h2>{p.destination}</h2>
        </div>
        <button
          className="icon"
          onClick={download}
          title="Download itinerary"
          aria-label="Download itinerary"
        >
          <Download size={19} />
        </button>
      </div>
      <div className="plan-meta">
        <span>
          <CalendarDays size={14} />
          {p.startDate} · {p.days} days
        </span>
        <span>
          <Users size={14} />
          {p.travelers} travelers
        </span>
      </div>
      <div
        className="plan-tabs"
        role="tablist"
        aria-label="Travel plan sections"
      >
        {["itinerary", "budget", "packing"].map((t) => (
          <button
            role="tab"
            aria-selected={tab === t}
            key={t}
            className={tab === t ? "active" : ""}
            id={`plan-tab-${t}`}
            aria-controls="plan-content"
            tabIndex={tab === t ? 0 : -1}
            onKeyDown={(event) => {
              const tabs = ["itinerary", "budget", "packing"];
              const index = tabs.indexOf(t);
              const next =
                event.key === "ArrowRight"
                  ? (index + 1) % 3
                  : event.key === "ArrowLeft"
                    ? (index + 2) % 3
                    : event.key === "Home"
                      ? 0
                      : event.key === "End"
                        ? 2
                        : null;
              if (next !== null) {
                event.preventDefault();
                setTab(tabs[next]);
                document.getElementById(`plan-tab-${tabs[next]}`)?.focus();
              }
            }}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>
      <div
        className="plan-body"
        id="plan-content"
        role="tabpanel"
        aria-labelledby={`plan-tab-${tab}`}
      >
        {plan.warnings.map((warning, i) => (
          <p className="notice" key={i}>
            {warning}
          </p>
        ))}
        {tab === "itinerary" && (
          <>
            {plan.weather.length > 0 && (
              <div className="weather">
                <CloudSun size={26} />
                <div>
                  <strong>Weather along the way</strong>
                  <span>
                    {Math.min(...plan.weather.map((w) => w.low))}–
                    {Math.max(...plan.weather.map((w) => w.high))}°C · max rain
                    chance {Math.max(...plan.weather.map((w) => w.rain))}%
                  </span>
                  <small>
                    Forecast coverage: {plan.weather[0].date} to{" "}
                    {plan.weather.at(-1).date}
                  </small>
                </div>
              </div>
            )}
            {plan.days.map((day) => (
              <section className="day" key={day.day}>
                <div className="day-heading">
                  <span>{String(day.day).padStart(2, "0")}</span>
                  <div>
                    <small>DAY {day.day}</small>
                    <h3>{day.title}</h3>
                  </div>
                </div>
                <div className="activities">
                  {day.activities.map((a, i) => (
                    <article className="activity" key={i}>
                      <div className="timeline-dot" />
                      <span className="activity-time">
                        {a.time} · {a.duration}
                      </span>
                      <h4>{a.place.name}</h4>
                      <p>{a.description}</p>
                      <small>{a.place.address}</small>
                      <div className="activity-footer">
                        <span>
                          {money(a.cost, p.currency)}{" "}
                          <small>est. / group</small>
                        </span>
                        <a
                          href={
                            "https://www.google.com/maps/search/?api=1&query=" +
                            encodeURIComponent(a.place.name) +
                            "&query_place_id=" +
                            encodeURIComponent(a.place.id)
                          }
                          target="_blank"
                          rel="noreferrer"
                        >
                          View map <ArrowUpRight size={13} />
                        </a>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            ))}
            <p className="source-line">
              Place information: Google Maps. Weather:{" "}
              <a
                href="https://open-meteo.com/"
                target="_blank"
                rel="noreferrer"
              >
                Open-Meteo
              </a>
              . Suggested times are not verified opening hours or route
              calculations.
            </p>
          </>
        )}
        {tab === "budget" && (
          <>
            <div className="budget-hero">
              <span>ESTIMATED GROUP TOTAL</span>
              <h2>{money(plan.budget.total, p.currency)}</h2>
              <p>of {money(p.budget, p.currency)} planned</p>
              <div className="budget-track">
                <div
                  style={{
                    width:
                      Math.min(100, (plan.budget.total / p.budget) * 100) + "%",
                    background:
                      plan.budget.remaining < 0 ? "#b5543d" : undefined,
                  }}
                />
              </div>
              <strong className={plan.budget.remaining < 0 ? "over" : ""}>
                {plan.budget.remaining >= 0
                  ? money(plan.budget.remaining, p.currency) +
                    " left in your budget"
                  : money(-plan.budget.remaining, p.currency) + " over budget"}
              </strong>
            </div>
            <p className="notice">
              Planning estimates, not quotes. Includes the whole group; excludes
              travel to and from your destination. Ask Roam to revise an
              over-budget plan.
            </p>
            {[
              ["accommodation", "Accommodation"],
              ["food", "Food & drinks"],
              ["localTransport", "Local transport"],
              ["activities", "Activities & admission"],
              ["contingency", "Contingency"],
            ].map(([key, label]) => (
              <div className="budget-row" key={key}>
                <span>{label}</span>
                <strong>{money(plan.budget[key], p.currency)}</strong>
              </div>
            ))}
          </>
        )}
        {tab === "packing" && (
          <>
            <div className="packing-heading">
              <Leaf size={25} />
              <h3>
                A little preparation,
                <br />a lot more freedom.
              </h3>
            </div>
            <p className="muted small">
              Suggested for your activities and available weather. Checklist
              ticks last while this plan is open.
            </p>
            <div className="packing-progress">
              <span role="status">
                {packed === plan.packing.length
                  ? "All packed. Adventure awaits!"
                  : `${packed} of ${plan.packing.length} packed`}
              </span>
              <progress
                aria-label="Packing progress"
                value={packed}
                max={Math.max(1, plan.packing.length)}
              />
            </div>
            {plan.packing.map((item, i) => (
              <label
                className={"packing-item " + (checked[i] ? "checked" : "")}
                key={i}
              >
                <input
                  type="checkbox"
                  checked={!!checked[i]}
                  onChange={() => setChecked({ ...checked, [i]: !checked[i] })}
                />
                <span>{item}</span>
              </label>
            ))}
          </>
        )}
        {plan.notes.length > 0 && (
          <details className="notes">
            <summary>Good to know</summary>
            {plan.notes.map((n, i) => (
              <p key={i}>{n}</p>
            ))}
          </details>
        )}
        <div className="plan-disclaimer">
          <ShieldCheck size={15} />
          <span>
            Places retrieved from Google. Costs and visit durations are AI
            estimates. No reservations have been made.
          </span>
        </div>
      </div>
    </aside>
  );
}
