import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listDocuments, uploadDocument } from "../api/documents";
import Header from "../components/Header";

const ACCEPTED_TYPES = ".pdf,.docx";
const IN_PROGRESS_STATUSES = ["uploaded", "processing"];
const POLL_INTERVAL_MS = 2000;

function truncate(text, max = 600) {
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function Documents() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    refreshDocuments();
  }, []);

  // While any document is still uploaded/processing, poll quietly in the
  // background (no loading spinner) so status badges move to
  // processed/failed on their own — no manual reload needed.
  useEffect(() => {
    const hasInProgress = documents.some((doc) =>
      IN_PROGRESS_STATUSES.includes(doc.status)
    );
    if (!hasInProgress) return;

    const timer = setInterval(async () => {
      try {
        const data = await listDocuments();
        setDocuments(data);
      } catch {
        // Silent — the next successful poll will recover the view.
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [documents]);

  async function refreshDocuments() {
    setLoading(true);
    try {
      const data = await listDocuments();
      setDocuments(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't load documents.");
    } finally {
      setLoading(false);
    }
  }

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setError("");
    setUploading(true);
    try {
      const doc = await uploadDocument(file);
      setDocuments((prev) => [doc, ...prev]);
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <div className="dash-page">
      <div className="dash-shell">
        <Header />

        <p className="doc-back">
          <Link to="/dashboard">← Dashboard</Link>
        </p>

        <h1>Documents</h1>
        <p className="lede">
          Upload a contract as a PDF or Word file. Once it's processed,
          open it to chat with it or get a plain-language summary.
        </p>

        <label className="upload-drop" htmlFor="doc-upload">
          <input
            id="doc-upload"
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES}
            onChange={handleFileChange}
            disabled={uploading}
            hidden
          />
          <span className="upload-drop-title">
            {uploading ? "Uploading…" : "Choose a file to upload"}
          </span>
          <span className="upload-drop-hint">PDF or DOCX, up to 20MB</span>
        </label>

        {error && <p className="form-error">{error}</p>}

        {loading ? (
          <p className="doc-status-text">Loading your documents…</p>
        ) : documents.length === 0 ? (
          <div className="empty-tray">
            <p>Nothing uploaded yet. Your files will show up here once added.</p>
          </div>
        ) : (
          <ul className="doc-list">
            {documents.map((doc) => {
              const isProcessed = doc.status === "processed";
              const isFailed = doc.status === "failed";
              const isOpen = expandedId === doc.id;

              function handleClick() {
                if (isProcessed) {
                  navigate(`/documents/${doc.id}`);
                } else if (isFailed) {
                  setExpandedId(isOpen ? null : doc.id);
                }
              }

              return (
                <li key={doc.id} className="doc-row-wrap">
                  <button
                    type="button"
                    className="doc-row doc-row-btn"
                    disabled={!isProcessed && !isFailed}
                    onClick={handleClick}
                  >
                    <div className="doc-row-main">
                      <p className="doc-name">{doc.original_filename}</p>
                      <p className="doc-meta">
                        {formatSize(doc.size_bytes)} · {formatDate(doc.uploaded_at)}
                      </p>
                    </div>
                    <span className={`doc-badge doc-badge-${doc.status}`}>
                      {doc.status === "processing" || doc.status === "uploaded"
                        ? "processing…"
                        : doc.status}
                    </span>
                  </button>

                  {isOpen && isFailed && (
                    <div className="doc-preview doc-preview-error">
                      <p className="doc-preview-label">Extraction failed</p>
                      <p className="doc-preview-text">
                        {doc.error_message || "Unknown error."}
                      </p>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
