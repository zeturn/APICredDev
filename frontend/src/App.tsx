import { Navigate, Route, Routes } from "react-router-dom";
import AdminLayout from "./layouts/AdminLayout";
import AuthLayout from "./layouts/AuthLayout";
import UserLayout from "./layouts/UserLayout";
import LoginPage from "./pages/Login";
import DashboardPage from "./pages/Dashboard";
import ModelsPage from "./pages/Models";
import TokensPage from "./pages/Tokens";
import TopupPage from "./pages/Topup";
import UsagePage from "./pages/Usage";
import AdminOverviewPage from "./pages/admin/AdminOverview";
import AdminUsersPage from "./pages/admin/AdminUsers";
import AdminModelsPage from "./pages/admin/AdminModels";
import AdminProvidersPage from "./pages/admin/AdminProviders";
import AdminProviderKeyDetailPage from "./pages/admin/AdminProviderKeyDetail";
import AdminUsagePage from "./pages/admin/AdminUsage";
import AdminApiModelsPage from "./pages/admin/AdminApiModels";
import RequireAuth from "./routes/RequireAuth";

const App = () => {
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
      </Route>

      <Route element={<RequireAuth />}>
        <Route path="/dashboard" element={<Navigate to="/workspace/dashboard" replace />} />
        <Route path="/usage" element={<Navigate to="/workspace/usage" replace />} />
        <Route path="/tokens" element={<Navigate to="/workspace/tokens" replace />} />
        <Route path="/models" element={<Navigate to="/workspace/models" replace />} />
        <Route path="/topup" element={<Navigate to="/workspace/topup" replace />} />
        <Route path="/admin" element={<Navigate to="/admin/overview" replace />} />

        <Route element={<UserLayout />}>
          <Route path="/" element={<Navigate to="/workspace/dashboard" replace />} />
          <Route path="/workspace/dashboard" element={<DashboardPage />} />
          <Route path="/workspace/usage" element={<UsagePage />} />
          <Route path="/workspace/tokens" element={<TokensPage />} />
          <Route path="/workspace/models" element={<ModelsPage />} />
          <Route path="/workspace/topup" element={<TopupPage />} />
        </Route>

        <Route element={<AdminLayout />}>
          <Route path="/admin/overview" element={<AdminOverviewPage />} />
          <Route path="/admin/users" element={<AdminUsersPage />} />
          <Route path="/admin/models" element={<AdminModelsPage />} />
          <Route path="/admin/providers" element={<AdminProvidersPage />} />
          <Route path="/admin/providers/:providerKeyId" element={<AdminProviderKeyDetailPage />} />
          <Route path="/admin/api-models" element={<AdminApiModelsPage />} />
          <Route path="/admin/usage" element={<AdminUsagePage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/workspace/dashboard" replace />} />
    </Routes>
  );
};

export default App;

