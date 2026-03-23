import { Navigate, Route, Routes } from "react-router-dom";
import AdminLayout from "./layouts/AdminLayout";
import AuthLayout from "./layouts/AuthLayout";
import UserLayout from "./layouts/UserLayout";
import LoginPage from "./pages/Login";
import ConsolePage from "./pages/ConsolePage";
import RequireAuth from "./routes/RequireAuth";
import { adminConsoleRoutes, userConsoleRoutes } from "./navigation/consoleRoutes";

const App = () => {
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
      </Route>

      <Route element={<RequireAuth />}>
        <Route path="/dashboard" element={<Navigate to="/workspace/dashboard" replace />} />
        <Route path="/tokens" element={<Navigate to="/workspace/tokens" replace />} />
        <Route path="/models" element={<Navigate to="/workspace/models" replace />} />
        <Route path="/topup" element={<Navigate to="/workspace/topup" replace />} />

        <Route element={<UserLayout />}>
          <Route path="/" element={<Navigate to="/workspace/dashboard" replace />} />
          {userConsoleRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={<ConsolePage />} />
          ))}
        </Route>

        <Route element={<AdminLayout />}>
          {adminConsoleRoutes.map((route) => (
            <Route key={route.path} path={route.path} element={<ConsolePage />} />
          ))}
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/workspace/dashboard" replace />} />
    </Routes>
  );
};

export default App;

