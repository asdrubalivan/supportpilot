"use client";

import { AlertTriangle, ArrowRight, Loader2, PackageSearch } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import {
  API_URL,
  CLOTHS,
  CUSTOMERS,
  ChatResult,
  Passage,
  TOOL_LABELS,
  clothFor,
  sectionSlug,
  splitCitations,
} from "./lib";

const EXAMPLES: Record<number, string[]> = {
  1: [
    "Can I return order 1234?",
    "I returned 1 book from my 5-book order 1236, why is my refund smaller?",
    "Does the 20% Jules Verne discount apply to a signed copy?",
    "What is the status of order 1238?",
  ],
  2: [
    "What is the status of order 1238?",
    "Do you ship to Canada?",
    "Can I return a signed copy?",
    "Do you sell e-books?",
  ],
};

// Spine height follows retrieval rank on a fixed ramp: the shelf is data, not ornament.
const RANK_RAMP = [100, 92, 85, 79, 74, 70, 67, 65];

type Status = "idle" | "loading" | "done" | "error";

export default function HelpDesk() {
  const [customerId, setCustomerId] = useState(1);
  const [question, setQuestion] = useState("");
  const [asked, setAsked] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<ChatResult | null>(null);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  // null on touch devices, where there is no keyboard shortcut to advertise.
  const [modKey, setModKey] = useState<string | null>("Ctrl");
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (window.matchMedia("(hover: none)").matches) setModKey(null);
    else if (/Mac/.test(navigator.userAgent)) setModKey("⌘");
  }, []);

  useEffect(() => {
    if (status !== "loading") return;
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.round((Date.now() - started) / 1000)), 500);
    return () => clearInterval(timer);
  }, [status]);

  function revealPanel() {
    // In the single-column layout the answer sits below the examples; bring it into view.
    if (!window.matchMedia("(max-width: 52rem)").matches) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    panelRef.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  }

  async function ask(text: string) {
    const message = text.trim();
    if (!message || status === "loading") return;
    setAsked(message);
    setStatus("loading");
    setElapsed(0);
    setError("");
    requestAnimationFrame(revealPanel);
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, customer_id: customerId }),
      });
      if (!response.ok) throw new Error(`The help desk answered with status ${response.status}.`);
      const data: ChatResult = await response.json();
      setResult(data);
      setOpenId(data.citations.find((c) => !data.invalid_citations.includes(c)) ?? null);
      setStatus("done");
    } catch (e) {
      setError(
        e instanceof TypeError
          ? `Couldn't reach the help desk at ${API_URL}. Start the backend with "uv run uvicorn supportpilot.api:app" and try again.`
          : e instanceof Error
            ? e.message
            : "Something went wrong.",
      );
      setStatus("error");
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    ask(question);
  }

  function switchCustomer(id: number) {
    setCustomerId(id);
    setResult(null);
    setStatus("idle");
    setOpenId(null);
  }

  const customer = CUSTOMERS.find((c) => c.id === customerId)!;

  return (
    <div className="page">
      <header className="rail">
        <div className="brand">
          <span className="brand-name">Old Pages Books</span>
          <span className="brand-desk">Help desk</span>
        </div>
        <div className="customer-switch" role="radiogroup" aria-label="Customer (demo)">
          <span className="switch-label">Customer · demo</span>
          {CUSTOMERS.map((c) => (
            <button
              key={c.id}
              type="button"
              role="radio"
              aria-checked={c.id === customerId}
              className="library-card"
              onClick={() => switchCustomer(c.id)}
            >
              <span className="card-no">No. {c.id}</span>
              <span className="card-name">{c.name}</span>
            </button>
          ))}
        </div>
      </header>

      <main className="desk">
        <section className="ask" aria-labelledby="ask-heading">
          <h1 id="ask-heading">Ask about returns, shipping, promotions, or your orders</h1>
          <p className="ask-note">
            Signed in as <strong>{customer.name}</strong>, who owns order{customer.orders.includes("–") ? "s" : ""}{" "}
            <span className="num">{customer.orders}</span>. Orders of other customers stay hidden.
          </p>

          <form onSubmit={onSubmit} className="ask-form">
            <label htmlFor="question" className="visually-hidden">
              Your question
            </label>
            <textarea
              id="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) ask(question);
              }}
              placeholder="e.g. Can I still return a book I got 40 days ago?"
              rows={4}
            />
            <div className="ask-actions">
              {modKey ? <span className="hint">{modKey} + Enter to ask</span> : <span />}
              <button type="submit" className="ask-button" disabled={!question.trim() || status === "loading"}>
                {status === "loading" ? <Loader2 className="spin" size={18} aria-hidden /> : null}
                {status === "loading" ? "Asking…" : "Ask"}
                {status === "loading" ? null : <ArrowRight size={18} aria-hidden />}
              </button>
            </div>
          </form>

          <div className="examples">
            <h2>Try one of these</h2>
            <ul>
              {EXAMPLES[customerId].map((example) => (
                <li key={example}>
                  <button
                    type="button"
                    disabled={status === "loading"}
                    onClick={() => {
                      setQuestion(example);
                      ask(example);
                    }}
                  >
                    {example}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section ref={panelRef} className="answer-panel" aria-live="polite" aria-busy={status === "loading"}>
          {status === "idle" && <EmptyState />}
          {status === "loading" && <LoadingState question={asked} elapsed={elapsed} />}
          {status === "error" && (
            <div className="error" role="alert">
              <AlertTriangle size={20} aria-hidden />
              <div>
                <h2>No answer this time</h2>
                <p>{error}</p>
              </div>
            </div>
          )}
          {status === "done" && result && (
            <Answer question={asked} result={result} openId={openId} onOpen={setOpenId} />
          )}
        </section>
      </main>

      <footer className="colophon">
        Old Pages Books is a fictional store. SupportPilot answers with a local 8B model and can be wrong; check the
        cited passage.
      </footer>
    </div>
  );
}

function EmptyState() {
  // The four volumes at rest: the shelf itself is the legend.
  const volumes = Object.entries(CLOTHS);
  return (
    <div className="empty">
      <div className="shelf shelf-rest" role="list" aria-label="Policy volumes">
        {volumes.map(([file, cloth], i) => (
          <div key={file} role="listitem" className={`spine is-rest ${cloth.className}`} style={{ height: `${RANK_RAMP[i]}%` }}>
            <span className="spine-title">{cloth.name}</span>
          </div>
        ))}
        <div className="shelf-board" />
      </div>
      <h2>The answer and its sources will appear here</h2>
      <p>
        Each volume on this shelf is one of the store&apos;s policy documents. When you ask, the agent pulls passages
        from them, and every policy claim in the answer carries the number of the passage that supports it.
      </p>
    </div>
  );
}

function LoadingState({ question, elapsed }: { question: string; elapsed: number }) {
  return (
    <div className="loading">
      <p className="asked">“{question}”</p>
      <div className="shelf shelf-loading" aria-hidden>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="spine spine-ghost" style={{ height: `${RANK_RAMP[i]}%`, animationDelay: `${i * 120}ms` }} />
        ))}
        <div className="shelf-board" />
      </div>
      <p className="loading-status">
        Reading the policies and checking your orders · <span className="num">{elapsed}</span> s
      </p>
      <p className="loading-note">A local model usually takes 10–20 seconds.</p>
    </div>
  );
}

function Answer({
  question,
  result,
  openId,
  onOpen,
}: {
  question: string;
  result: ChatResult;
  openId: string | null;
  onOpen: (id: string) => void;
}) {
  const cited = new Set(result.citations);
  const rankOf = new Map(result.passages.map((p, i) => [p.id, i + 1]));
  const openPassage = result.passages.find((p) => p.id === openId) ?? null;
  const citedCount = result.citations.length - result.invalid_citations.length;

  return (
    <article className="answer">
      <p className="asked">“{question}”</p>
      <div className="answer-text">
        {splitCitations(result.answer).map((part, i) =>
          "text" in part ? (
            // Punctuation right after a label stays glued to it instead of wrapping alone.
            <span key={i}>{/^[.,;:]/.test(part.text) ? "⁠" : ""}{part.text}</span>
          ) : (
            <CallNumber
              key={i}
              id={part.cite}
              rank={rankOf.get(part.cite)}
              invalid={result.invalid_citations.includes(part.cite)}
              active={part.cite === openId}
              onOpen={onOpen}
            />
          ),
        )}
      </div>

      {result.invalid_citations.length > 0 && (
        <p className="warning">
          <AlertTriangle size={16} aria-hidden /> Some claims point to passages the agent never retrieved. Treat them as
          unverified.
        </p>
      )}

      {result.tools_called.length > 0 && (
        <ul className="tools">
          {[...new Set(result.tools_called)].map((tool) => (
            <li key={tool}>
              <PackageSearch size={16} aria-hidden /> {TOOL_LABELS[tool] ?? tool}
            </li>
          ))}
        </ul>
      )}

      <div className="shelf-section">
        <div className="shelf-head">
          <h2>Passages the agent pulled</h2>
          <span className="shelf-count">
            <span className="num">{result.passages.length}</span> retrieved · <span className="num">{citedCount}</span>{" "}
            cited
          </span>
        </div>
        <div className="shelf" role="list">
          {result.passages.map((p, i) => (
            <button
              key={p.id}
              type="button"
              role="listitem"
              className={`spine ${clothFor(p.id).className}${cited.has(p.id) ? " is-cited" : ""}${p.id === openId ? " is-open" : ""}`}
              style={{ height: `${RANK_RAMP[i] ?? 65}%`, animationDelay: `${i * 70}ms` }}
              onClick={() => onOpen(p.id)}
              aria-pressed={p.id === openId}
              aria-label={`Passage ${i + 1}: ${p.document}, ${p.section}${cited.has(p.id) ? ", cited" : ""}`}
            >
              <span className="spine-title">{sectionSlug(p.id)}</span>
              <span className="spine-call num">{i + 1}</span>
            </button>
          ))}
          <div className="shelf-board" />
        </div>

        <ul className="legend" aria-label="Volumes on this shelf">
          {[...new Set(result.passages.map((p) => p.id.split("#")[0]))].map((file) => {
            const cloth = clothFor(file);
            return (
              <li key={file}>
                <span className={`swatch ${cloth.className}`} aria-hidden />
                {cloth.name}
              </li>
            );
          })}
        </ul>

        {openPassage ? <OpenedPassage passage={openPassage} rank={rankOf.get(openPassage.id)!} cited={cited.has(openPassage.id)} /> : (
          <p className="passage-hint">Open a volume to read its passage.</p>
        )}
      </div>
    </article>
  );
}

function OpenedPassage({ passage, rank, cited }: { passage: Passage; rank: number; cited: boolean }) {
  return (
    <div className={`passage ${clothFor(passage.id).className}`}>
      <h3>
        <span className="passage-call num">{rank}</span> {passage.section}
      </h3>
      <p>{passage.text}</p>
      <p className="passage-meta">
        <code>{passage.id}</code> · {cited ? "cited in the answer" : "retrieved, not cited"}
      </p>
    </div>
  );
}

function CallNumber({
  id,
  rank,
  invalid,
  active,
  onOpen,
}: {
  id: string;
  rank: number | undefined;
  invalid: boolean;
  active: boolean;
  onOpen: (id: string) => void;
}) {
  const cloth = clothFor(id);
  const label = invalid ? `Unverified source ${id}` : `Source ${rank}: ${cloth.name}, ${sectionSlug(id)}`;
  return (
    <button
      type="button"
      className={`call-number ${cloth.className}${invalid ? " is-invalid" : ""}${active ? " is-active" : ""}`}
      onClick={() => !invalid && onOpen(id)}
      aria-disabled={invalid}
      aria-label={label}
      title={invalid ? `${id} was not among the retrieved passages` : id}
    >
      {invalid ? "?" : rank}
    </button>
  );
}
