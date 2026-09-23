import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";

function initialsFor(user) {
  const source = user?.full_name || user?.email || "?";
  const parts = source.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return source.slice(0, 2).toUpperCase();
}

export default function Header() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    function handleEscape(e) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  return (
    <header className="dash-header">
      <p className="wordmark">LegalDocAI</p>

      <div className="profile-menu" ref={menuRef}>
        <button
          type="button"
          className="profile-avatar"
          onClick={() => setOpen((v) => !v)}
          aria-haspopup="true"
          aria-expanded={open}
        >
          {initialsFor(user)}
        </button>

        {open && (
          <div className="profile-dropdown" role="menu">
            <div className="profile-dropdown-info">
              <p className="profile-dropdown-name">
                {user?.full_name || "Account"}
              </p>
              <p className="profile-dropdown-email">{user?.email}</p>
            </div>
            <button
              type="button"
              className="profile-dropdown-item"
              onClick={logout}
              role="menuitem"
            >
              Log out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
