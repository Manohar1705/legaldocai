import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Header from "../components/Header";

export default function Dashboard() {
  const { user } = useAuth();
  const firstName = user?.full_name?.split(" ")[0];

  return (
    <div className="dash-page">
      <div className="dash-shell">
        <Header />

        <h1>Welcome back{firstName ? `, ${firstName}` : ""}.</h1>
        <p className="lede">
          Upload a contract to get a plain-language summary and ask it
          questions grounded in the document's actual text.
        </p>

        <div className="empty-tray">
          <p>
            Nothing here yet. <Link to="/documents">Upload a contract</Link> to
            get started.
          </p>
        </div>
      </div>
    </div>
  );
}
