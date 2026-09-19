import React, { useState, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  Compass,
  Plus,
  LogOut,
  MapPin,
  ChevronRight,
  Menu,
  X,
  MessageCircle,
  Leaf,
  ArrowUpRight,
  ArrowUp,
  LoaderCircle,
  CheckCheck,
  Trash2,
} from "lucide-react";
import Auth from "./components/Auth";
import Plan from "./components/Plan";
import TripForm from "./components/TripForm";
import { api, money } from "./lib/api";
import "./style.css";

const welcome =
  "Tell me where you’re dreaming of going. We’ll work out the details together.";

function App() {
  const [user, setUser] = useState(undefined),
    [chats, setChats] = useState([]),
    [chat, setChat] = useState(null),
    [draft, setDraft] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [mobile, setMobile] = useState(false),
    [tab, setTab] = useState("itinerary"),
    [checked, setChecked] = useState({}),
    [pending, setPending] = useState("");
  const [showForm, setShowForm] = useState(false);
  const bottom = useRef(null);
  useEffect(() => {
    api("/auth/me")
      .then((d) => setUser(d.user))
      .catch((e) => {
        setUser(null);
        setError(e.message);
      });
  }, []);
  async function refresh() {
    setChats(await api("/chats"));
  }
  useEffect(() => {
    if (user) refresh().catch((e) => setError(e.message));
  }, [user]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [chat?.messages, busy]);
  async function selectChat(id) {
    if (busy) return;
    setError("");
    try {
      setChat(await api("/chats/" + id));
      setShowForm(false);
      setChecked({});
      setMobile(false);
    } catch (e) {
      setError(e.message);
    }
  }
  async function send(e, text) {
    e?.preventDefault();
    const message = (text || draft).trim();
    if (!message || busy) return;
    setError("");
    setPending(message);
    setDraft("");
    setBusy(true);
    try {
      let current = chat;
      if (!current) {
        current = await api("/chats", { method: "POST" });
        setChat(current);
      }
      const result = await api("/chats/" + current.id + "/messages", {
        method: "POST",
        body: JSON.stringify({ message }),
      });
      setChat(result);
      setChecked({});
      await refresh();
    } catch (e) {
      setError(e.message);
      setDraft(message);
    } finally {
      setPending("");
      setBusy(false);
    }
  }
  async function submitPreferences(preferences) {
    if (busy) return;
    setError("");
    setBusy(true);
    setPending(
      `Planning your ${preferences.style.toLowerCase()} trip to ${preferences.destination}…`,
    );
    try {
      const current = chat || (await api("/chats", { method: "POST" }));
      setChat(current);
      const result = await api("/chats/" + current.id + "/preferences", {
        method: "POST",
        body: JSON.stringify(preferences),
      });
      setChat(result);
      setChecked({});
      setTab("itinerary");
      setShowForm(false);
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
      setPending("");
    }
  }
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
      setUser(null);
      setChat(null);
      setChats([]);
    } catch (e) {
      setError(e.message);
    }
  }
  async function removeChat() {
    if (
      !chat ||
      busy ||
      !window.confirm("Delete this conversation and its saved plan?")
    )
      return;
    try {
      await api("/chats/" + chat.id, { method: "DELETE" });
      setChat(null);
      await refresh();
    } catch (e) {
      setError(e.message);
    }
  }
  async function removeAccount() {
    if (
      !window.confirm(
        "Delete your account and all of your saved conversations permanently?",
      )
    )
      return;
    try {
      await api("/auth/me", { method: "DELETE" });
      setUser(null);
      setChat(null);
      setChats([]);
    } catch (e) {
      setError(e.message);
    }
  }
  if (user === undefined)
    return (
      <div className="loading-screen">
        <Compass size={40} />
        <p>Finding your next chapter…</p>
      </div>
    );
  if (!user) return <Auth onAuth={setUser} />;
  const plan = chat?.plan;
  const suggestions = [
    "A relaxed 3-day escape to Jaipur",
    "A food-filled weekend in Bengaluru",
    "Help me plan a family trip to Goa",
  ];
  return (
    <div className="app-shell">
      <aside className={"sidebar " + (mobile ? "open" : "")}>
        <div className="sidebar-top">
          <a
            className="brand"
            href="/"
            onClick={(e) => {
              e.preventDefault();
              if (!busy) {
                setChat(null);
                setShowForm(false);
              }
            }}
          >
            <Compass size={30} /> roam<span>®</span>
          </a>
          <button
            aria-label="Close navigation"
            className="icon mobile-only"
            onClick={() => setMobile(false)}
          >
            <X />
          </button>
        </div>
        <button
          className="new-chat"
          disabled={busy}
          onClick={() => {
            setChat(null);
            setDraft("");
            setError("");
            setMobile(false);
            setShowForm(false);
          }}
        >
          <Plus size={18} /> Plan a new adventure
        </button>
        <div className="sidebar-label">
          YOUR JOURNEYS <span>{chats.length}</span>
        </div>
        <nav className="chat-list">
          {chats.map((c) => (
            <button
              disabled={busy}
              onClick={() => selectChat(c.id)}
              key={c.id}
              className={"chat-item " + (chat?.id === c.id ? "active" : "")}
            >
              <MessageCircle size={16} />
              <span>{c.title}</span>
              <ChevronRight size={14} />
            </button>
          ))}
          {!chats.length && (
            <p className="sidebar-empty">
              Your next great story
              <br />
              starts right here.
            </p>
          )}
        </nav>
        <div className="sidebar-tip">
          <Leaf size={21} />
          <strong>Take the scenic route.</strong>
          <p>Ask for a slower pace, hidden gems, or more time outdoors.</p>
        </div>
        <div className="user-block">
          <span className="avatar">{user.name[0].toUpperCase()}</span>
          <div>
            <strong>{user.name}</strong>
            <span>Your personal space</span>
          </div>
          <button
            className="icon"
            aria-label="Sign out"
            disabled={busy}
            onClick={logout}
          >
            <LogOut size={17} />
          </button>
        </div>
        <button
          className="delete-account"
          disabled={busy}
          onClick={removeAccount}
        >
          Delete my account & data
        </button>
      </aside>
      <main className="workspace">
        <header className="topbar">
          <div>
            <button
              className="icon mobile-only"
              aria-label="Open navigation"
              onClick={() => setMobile(true)}
            >
              <Menu />
            </button>
            <span className="breadcrumb">YOUR TRAVEL COMPANION</span>
            <span className="topbar-sub">
              A little inspiration. A plan that’s yours.
            </span>
          </div>
          <span className="status">
            <i /> Powered by curiosity & AI
          </span>
        </header>
        <div className={"content " + (plan ? "with-plan" : "")}>
          <section className="conversation">
            <div className="conversation-scroll">
              {showForm ? (
                <div className="form-page">
                  <button
                    className="form-back"
                    disabled={busy}
                    onClick={() => setShowForm(false)}
                  >
                    ← Back to conversation
                  </button>
                  <TripForm
                    onSubmit={submitPreferences}
                    busy={busy}
                    error={error}
                  />
                  {busy && (
                    <p className="form-progress" role="status">
                      Looking up places and weather, then building and
                      validating your itinerary. This can take a minute.
                    </p>
                  )}
                </div>
              ) : !chat?.messages?.length && !busy ? (
                <div className="welcome">
                  <span className="eyebrow">
                    GO SOMEWHERE THAT STAYS WITH YOU
                  </span>
                  <h1>
                    Where to next,
                    <br />
                    <em>{user.name.split(" ")[0]}?</em>
                  </h1>
                  <p>
                    Big adventures. Quiet weekends. A change of scenery.
                    <br />
                    Tell me what you have in mind, and we’ll make a plan.
                  </p>
                  <div className="planning-choice">
                    <button
                      className="primary"
                      onClick={() => {
                        setError("");
                        setShowForm(true);
                      }}
                    >
                      Start with trip details <ArrowUpRight size={17} />
                    </button>
                    <span>or simply chat below</span>
                  </div>
                  <div className="destination-art">
                    <div className="art-label">
                      <span>THE WORLD IS WAITING</span>
                      <strong>
                        Find your kind
                        <br />
                        of elsewhere.
                      </strong>
                    </div>
                    <div className="art-sun" />
                    <div className="art-hill hill-back" />
                    <div className="art-hill hill-front" />
                    <div className="art-road" />
                    <span className="art-stamp">
                      <Compass size={22} /> ROAM FREE
                    </span>
                  </div>
                  <div className="suggestions">
                    {suggestions.map((s, i) => (
                      <button key={s} onClick={() => send(null, s)}>
                        <span>{["✧", "☕", "☀"][i]}</span>
                        {s}
                        <ArrowUpRight size={16} />
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="messages">
                  <div className="assistant-intro">
                    <Compass size={23} />
                    <p>{welcome}</p>
                  </div>
                  {chat?.messages?.map((m, i) => (
                    <div className={"message " + m.role} key={i}>
                      {m.role === "assistant" && (
                        <span className="bot-avatar">
                          <Compass size={18} />
                        </span>
                      )}
                      <div>
                        <span className="message-author">
                          {m.role === "assistant"
                            ? "ROAM"
                            : user.name.toUpperCase()}
                        </span>
                        <p>{m.content}</p>
                      </div>
                    </div>
                  ))}
                  {busy && (
                    <>
                      <div className="message user">
                        <div>
                          <span className="message-author">
                            {user.name.toUpperCase()}
                          </span>
                          <p>{pending}</p>
                        </div>
                      </div>
                      <div className="message assistant">
                        <span className="bot-avatar">
                          <Compass size={18} />
                        </span>
                        <div>
                          <span className="message-author">ROAM</span>
                          <p className="thinking">
                            <span />
                            <span />
                            <span /> Exploring the possibilities…
                          </p>
                          <small className="muted">
                            Checking preferences, places, and weather. This may
                            take a minute.
                          </small>
                        </div>
                      </div>
                    </>
                  )}
                  {plan && (
                    <div className="plan-ready">
                      <CheckCheck size={18} /> Your itinerary is ready. Ask me
                      to adjust it.
                      <button
                        className="mobile-only"
                        onClick={() =>
                          document
                            .querySelector(".plan-panel")
                            ?.scrollIntoView({ behavior: "smooth" })
                        }
                      >
                        View plan ↓
                      </button>
                    </div>
                  )}
                  <div ref={bottom} />
                </div>
              )}
            </div>
            {!showForm && (
              <div className="composer-wrap">
                {error && (
                  <div className="error" role="alert">
                    {error}
                  </div>
                )}
                {chat?.profile?.destination && (
                  <div className="profile-chips">
                    <span>
                      <MapPin size={12} />
                      {chat.profile.destination}
                    </span>
                    {chat.profile.days && <span>{chat.profile.days} days</span>}
                    {chat.profile.style && (
                      <span>{chat.profile.style} pace</span>
                    )}
                    {chat.profile.budget && (
                      <span>
                        {money(chat.profile.budget, chat.profile.currency)}
                      </span>
                    )}
                  </div>
                )}
                {plan && (
                  <div
                    className="revision-actions"
                    aria-label="Suggested itinerary revisions"
                  >
                    {[
                      "Make it cheaper",
                      "A more relaxed pace",
                      "Add more local culture",
                    ].map((text) => (
                      <button
                        key={text}
                        disabled={busy}
                        onClick={() => send(null, text)}
                      >
                        {text}
                      </button>
                    ))}
                  </div>
                )}
                <form className="composer" onSubmit={send}>
                  <textarea
                    aria-label="Message Roam"
                    placeholder="A weekend away? A big adventure? Let’s talk…"
                    value={draft}
                    maxLength={3000}
                    rows={2}
                    disabled={busy}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        send(e);
                      }
                    }}
                  />
                  <div className="composer-bottom">
                    <span>
                      <Compass size={13} /> YOUR PLANS, YOUR PACE
                    </span>
                    <button
                      aria-label="Send message"
                      disabled={busy || !draft.trim()}
                    >
                      {busy ? (
                        <LoaderCircle size={18} className="spin" />
                      ) : (
                        <ArrowUp size={19} />
                      )}
                    </button>
                  </div>
                </form>
                <div className="composer-footer">
                  <span>
                    AI can make mistakes. Confirm prices and opening hours
                    before travel.
                  </span>
                  {chat && (
                    <button
                      aria-label="Delete conversation"
                      disabled={busy}
                      onClick={removeChat}
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              </div>
            )}
          </section>
          {plan && (
            <Plan
              plan={plan}
              tab={tab}
              setTab={setTab}
              checked={checked}
              setChecked={setChecked}
            />
          )}
        </div>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
