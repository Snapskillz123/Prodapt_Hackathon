import React, { useState } from "react";
import { Compass, ShieldCheck, ArrowUpRight, LoaderCircle } from "lucide-react";
import { api } from "../lib/api";

export default function Auth({ onAuth }) {
  const [signup, setSignup] = useState(true),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const values = Object.fromEntries(new FormData(e.target));
      const data = await api("/auth/" + (signup ? "register" : "login"), {
        method: "POST",
        body: JSON.stringify(values),
      });
      onAuth(data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-page">
      <section className="auth-story">
        <a className="brand" href="/" aria-label="Roam home">
          <Compass size={32} /> roam<span>®</span>
        </a>
        <div className="auth-art">
          <div className="sun" />
          <div className="mountain m1" />
          <div className="mountain m2" />
          <div className="mountain m3" />
          <div className="trail" />
          <span className="coordinate">26°55′ N · 75°49′ E</span>
        </div>
        <div className="auth-caption">
          <span className="eyebrow">LESS PLANNING. MORE LIVING.</span>
          <h1>
            The best trips start
            <br />
            with a little curiosity.
          </h1>
          <p>A thoughtful travel companion for wherever life takes you next.</p>
        </div>
        <div className="auth-foot">
          <span>Made for the way you travel.</span>
          <span>✦ &nbsp; EXPLORE A LITTLE FURTHER</span>
        </div>
      </section>
      <section className="auth-form">
        <div className="auth-form-inner">
          <span className="eyebrow green">YOUR NEXT CHAPTER</span>
          <h2>
            {signup ? "A world of possibilities." : "Welcome back, explorer."}
          </h2>
          <p className="muted">
            {signup
              ? "Create your space. Start your next adventure."
              : "Your conversations and travel plans are waiting."}
          </p>
          <div className="auth-toggle">
            <button
              className={signup ? "selected" : ""}
              onClick={() => {
                setSignup(true);
                setError("");
              }}
            >
              Create account
            </button>
            <button
              className={!signup ? "selected" : ""}
              onClick={() => {
                setSignup(false);
                setError("");
              }}
            >
              Sign in
            </button>
          </div>
          <form onSubmit={submit}>
            {signup && (
              <label>
                Your name
                <input
                  name="name"
                  autoComplete="name"
                  placeholder="How should we call you?"
                  required
                  maxLength={60}
                />
              </label>
            )}
            <label>
              Email address
              <input
                name="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                required
                maxLength={254}
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete={signup ? "new-password" : "current-password"}
                placeholder={
                  signup ? "At least 10 characters" : "Enter your password"
                }
                minLength={signup ? 10 : 1}
                maxLength={128}
                required
              />
            </label>
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <button className="primary full" disabled={busy}>
              {busy ? (
                <LoaderCircle className="spin" size={18} />
              ) : signup ? (
                "Let’s explore"
              ) : (
                "Sign in"
              )}{" "}
              {!busy && <ArrowUpRight size={18} />}
            </button>
          </form>
          <p className="privacy-note">
            <ShieldCheck size={16} /> Passwords are hashed. Your saved trips
            stay on this computer.
          </p>
          <p className="small muted">
            Trip messages are sent to Gemini to generate suggestions. Location
            queries go to Google Places and Open-Meteo. Your login details are
            never included in AI prompts. No email verification or password
            recovery in this local demo.
          </p>
        </div>
      </section>
    </div>
  );
}
