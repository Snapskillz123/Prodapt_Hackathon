import React, { useState } from "react";
import {
  ArrowUpRight,
  CalendarDays,
  LoaderCircle,
  SlidersHorizontal,
} from "lucide-react";

const interests = [
  "Beaches",
  "Food",
  "Adventure",
  "Culture",
  "Nature",
  "Shopping",
  "Nightlife",
  "Relaxation",
];
function localDate() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export default function TripForm({ onSubmit, busy, error }) {
  const [values, setValues] = useState({
    destination: "",
    startDate: "",
    endDate: "",
    travellers: 2,
    totalBudget: 20000,
    interests: ["Culture", "Food"],
    style: "Balanced",
    requirements: "",
  });
  const [validation, setValidation] = useState("");
  const update = (key, value) => {
    setValues((current) => ({ ...current, [key]: value }));
    setValidation("");
  };
  const days =
    values.startDate && values.endDate
      ? Math.round(
          (Date.parse(values.endDate) - Date.parse(values.startDate)) /
            86400000,
        ) + 1
      : 0;
  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    if (days < 2 || days > 7)
      return setValidation(
        "Choose an end date after your start date, for a trip of 2–7 days.",
      );
    if (!values.interests.length)
      return setValidation("Choose at least one interest.");
    if (values.destination.trim().length < 2)
      return setValidation("Enter a destination with at least two characters.");
    setValidation("");
    await onSubmit({ ...values, destination: values.destination.trim() });
  }
  return (
    <form className="trip-form" onSubmit={submit} aria-label="Trip preferences">
      <div className="trip-form-heading">
        <span className="form-emblem">
          <SlidersHorizontal size={22} />
        </span>
        <div>
          <span className="eyebrow green">
            A FEW DETAILS. YOUR KIND OF TRIP.
          </span>
          <h2>Make room for adventure.</h2>
        </div>
      </div>
      <p className="form-description">
        Set the essentials here. Fine-tune everything with Roam in the chat.
      </p>
      <fieldset disabled={busy}>
        <div className="form-grid">
          <label className="form-wide">
            Where are you headed?
            <input
              name="destination"
              required
              minLength={2}
              maxLength={100}
              placeholder="City and country, e.g. Jaipur, India"
              value={values.destination}
              onChange={(e) => update("destination", e.target.value)}
            />
          </label>
          <label>
            Departure date
            <input
              type="date"
              required
              min={localDate()}
              value={values.startDate}
              onChange={(e) => update("startDate", e.target.value)}
            />
          </label>
          <label>
            Last day of your trip
            <input
              type="date"
              required
              min={values.startDate || localDate()}
              value={values.endDate}
              onChange={(e) => update("endDate", e.target.value)}
            />
          </label>
          <label>
            Travelers
            <input
              type="number"
              required
              min={1}
              max={12}
              step={1}
              value={values.travellers}
              onChange={(e) =>
                update(
                  "travellers",
                  e.target.value === "" ? "" : Number(e.target.value),
                )
              }
            />
          </label>
          <label>
            Total group budget (INR)
            <input
              type="number"
              required
              min={1000}
              max={10000000}
              step={100}
              value={values.totalBudget}
              onChange={(e) =>
                update(
                  "totalBudget",
                  e.target.value === "" ? "" : Number(e.target.value),
                )
              }
            />
          </label>
        </div>
        <p className="form-hint">
          <CalendarDays size={14} />
          {days >= 2 && days <= 7
            ? `${days} days · ${days - 1} nights`
            : "Plan 2–7 days, including your first and last day."}
          <span>Budget excludes travel to your destination.</span>
        </p>
        <fieldset className="interest-field">
          <legend>What makes a trip yours?</legend>
          <div className="interest-options">
            {interests.map((interest) => (
              <button
                type="button"
                key={interest}
                aria-pressed={values.interests.includes(interest)}
                onClick={() =>
                  update(
                    "interests",
                    values.interests.includes(interest)
                      ? values.interests.filter((item) => item !== interest)
                      : [...values.interests, interest],
                  )
                }
              >
                {interest}
              </button>
            ))}
          </div>
        </fieldset>
        <fieldset className="pace-field">
          <legend>Find your pace</legend>
          <div className="pace-options">
            {[
              ["Relaxed", "Space to linger"],
              ["Balanced", "A little of everything"],
              ["Packed", "Make the most of it"],
            ].map(([style, detail]) => (
              <label
                key={style}
                className={values.style === style ? "selected" : ""}
              >
                <input
                  type="radio"
                  name="style"
                  value={style}
                  checked={values.style === style}
                  onChange={() => update("style", style)}
                />
                <strong>{style}</strong>
                <span>{detail}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <label className="requirements-label">
          Anything else? <span>Optional</span>
          <textarea
            rows={3}
            maxLength={1500}
            value={values.requirements}
            placeholder="Prefer shorter walks, quiet mornings, or time for shopping? Avoid sharing sensitive personal details."
            onChange={(e) => update("requirements", e.target.value)}
          />
        </label>
        {(validation || error) && (
          <p className="error" role="alert">
            {validation || error}
          </p>
        )}
        <div className="form-submit">
          <span>
            Real places. AI suggestions.
            <br />
            Prices are estimates, not bookings.
          </span>
          <button className="primary" type="submit">
            {busy ? (
              <>
                <LoaderCircle className="spin" size={18} /> Planning your trip…
              </>
            ) : (
              <>
                Create my itinerary <ArrowUpRight size={18} />
              </>
            )}
          </button>
        </div>
      </fieldset>
    </form>
  );
}
