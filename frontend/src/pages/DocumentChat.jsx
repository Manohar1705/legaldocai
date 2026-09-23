import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import {
  getDocument,
  getChatHistory,
  sendChatMessage,
  getSummary,
} from "../api/documents";
import Header from "../components/Header";

export default function DocumentChat() {
  const { id } = useParams();
  const [document, setDocument] = useState(null);
  const [tab, setTab] = useState("chat");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  // Summary tab state — kept separate from chat's error/loading so
  // switching tabs never clobbers the other tab's state.
  const [summary, setSummary] = useState(null);
  const [summarizedAt, setSummarizedAt] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    loadDocument();
  }, [id]);

  useEffect(() => {
    // Fetch the summary lazily, the first time the tab is opened — no
    // point paying for an LLM call before the user asks to see it.
    // The backend caches the result, so this is cheap on repeat visits.
    if (tab === "summary" && summary === null && !summaryLoading && document?.status === "processed") {
      loadSummary();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, document]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadDocument() {
    setLoading(true);
    setError("");
    try {
      const doc = await getDocument(id);
      setDocument(doc);
      if (doc.summary) {
        setSummary(doc.summary);
        setSummarizedAt(doc.summarized_at);
      }
      if (doc.status === "processed") {
        const history = await getChatHistory(id);
        setMessages(history);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't load this document.");
    } finally {
      setLoading(false);
    }
  }

  async function loadSummary({ force = false } = {}) {
    setSummaryError("");
    setSummaryLoading(true);
    try {
      const doc = await getSummary(id, { force });
      setSummary(doc.summary);
      setSummarizedAt(doc.summarized_at);
    } catch (err) {
      setSummaryError(err.response?.data?.detail || "Couldn't generate a summary.");
    } finally {
      setSummaryLoading(false);
    }
  }

  async function handleSend(e) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    setError("");
    setSending(true);
    // Optimistically show the user's message right away.
    const optimisticUser = {
      id: `pending-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    setMessages((prev) => [...prev, optimisticUser]);
    setInput("");

    try {
      const assistantMessage = await sendChatMessage(id, trimmed);
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err.response?.data?.detail || "The assistant couldn't respond. Try again.");
      // Roll back the optimistic message so the input can be retried cleanly.
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
      setInput(trimmed);
    } finally {
      setSending(false);
    }
  }

  if (loading) {
    return (
      <div className="dash-page">
        <div className="dash-shell">
          <p className="doc-status-text">Loading…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dash-page">
      <div className="dash-shell">
        <Header />

        <p className="doc-back">
          <Link to="/documents">← Documents</Link>
        </p>

        <h1>{document?.original_filename || "Document"}</h1>

        {document && document.status !== "processed" && (
          <p className="doc-status-text">
            {document.status === "failed"
              ? `Processing failed: ${document.error_message || "unknown error"}`
              : "Still processing this document — chat will be available once it's done."}
          </p>
        )}

        {error && <p className="form-error">{error}</p>}

        {document?.status === "processed" && (
          <div className="doc-tabs">
            <button
              className={`doc-tab ${tab === "chat" ? "active" : ""}`}
              onClick={() => setTab("chat")}
            >
              Chat
            </button>
            <button
              className={`doc-tab ${tab === "summary" ? "active" : ""}`}
              onClick={() => setTab("summary")}
            >
              Summary
            </button>
          </div>
        )}

        {document?.status === "processed" && tab === "summary" && (
          <div className="summary-panel">
            {summaryError && <p className="form-error">{summaryError}</p>}

            {summaryLoading && !summary && (
              <p className="doc-status-text">Generating a summary — this can take a few seconds…</p>
            )}

            {summary && (
              <>
                <div className="summary-meta">
                  {summarizedAt && (
                    <span className="summary-timestamp">
                      Generated {new Date(summarizedAt).toLocaleString()}
                    </span>
                  )}
                  <button
                    className="summary-regen-btn"
                    onClick={() => loadSummary({ force: true })}
                    disabled={summaryLoading}
                  >
                    {summaryLoading ? "Regenerating…" : "Regenerate"}
                  </button>
                </div>
                <div className="summary-body">
                  <ReactMarkdown>{summary}</ReactMarkdown>
                </div>
              </>
            )}

            {!summary && !summaryLoading && !summaryError && (
              <p className="doc-status-text">No summary yet.</p>
            )}
          </div>
        )}

        {document?.status === "processed" && tab === "chat" && (
          <>
            <div className="chat-thread">
              {messages.length === 0 ? (
                <p className="doc-status-text">
                  Ask anything about this document — payment terms, dates,
                  obligations, or what a clause actually means.
                </p>
              ) : (
                messages.map((m) => (
                  <div key={m.id} className={`chat-bubble chat-bubble-${m.role}`}>
                    <div className="chat-bubble-text">
                      <ReactMarkdown>{m.content}</ReactMarkdown>
                    </div>
                  </div>
                ))
              )}
              {sending && (
                <div className="chat-bubble chat-bubble-assistant">
                  <p className="chat-bubble-text chat-bubble-typing">Thinking…</p>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            <form className="chat-input-row" onSubmit={handleSend}>
              <input
                type="text"
                className="chat-input"
                placeholder="Ask about this document…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={sending}
              />
              <button type="submit" className="chat-send-btn" disabled={sending || !input.trim()}>
                Send
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
