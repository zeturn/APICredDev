import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import api from "../api/client";
import LoadingScreen from "../pages/LoadingScreen";

const RequireAuth = () => {
  const location = useLocation();
  const [state, setState] = useState<"checking" | "ok" | "unauthorized">("checking");

  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        await api.get("/auth/me");
        if (active) {
          setState("ok");
        }
      } catch {
        if (active) {
          setState("unauthorized");
        }
      }
    };
    check();
    return () => {
      active = false;
    };
  }, [location.pathname]);

  if (state === "checking") {
    return <LoadingScreen />;
  }

  if (state !== "ok") {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
};

export default RequireAuth;
