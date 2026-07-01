import { Navigate, Route, Routes } from "react-router-dom";
import AdminLayout from "./layouts/AdminLayout";
import AuthLayout from "./layouts/AuthLayout";
import UserLayout from "./layouts/UserLayout";
import LoginPage from "./pages/Login";
import DashboardPage from "./pages/Dashboard";
import ProfilePage from "./pages/Profile";
import ModelsPage from "./pages/Models";
import TokensPage from "./pages/Tokens";
import TopupPage from "./pages/Topup";
import UsagePage from "./pages/Usage";
import AdminOverviewPage from "./pages/admin/AdminOverview";
import AdminUsersPage from "./pages/admin/AdminUsers";
import AdminUsagePage from "./pages/admin/AdminUsage";
import AdminApiModelsPage from "./pages/admin/AdminApiModels";
import {
  AdminBrandDetailPage,
  AdminBrandsPage,
  AdminModelRouteDetailPage,
  AdminModelRoutesPage,
  AdminProviderCredentialDetailPage,
  AdminProviderCredentialsPage,
  AdminProviderDetailPage,
  AdminProviderEndpointDetailPage,
  AdminProviderEndpointsPage,
  AdminProvidersPage,
  AdminPublicModelDetailPage,
  AdminPublicModelsPage,
  AdminUpstreamModelDetailPage,
  AdminUpstreamModelsPage,
} from "./pages/admin/AdminCatalogPages";
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
        <Route path="/profile" element={<Navigate to="/workspace/profile" replace />} />
        <Route path="/admin" element={<Navigate to="/admin/overview" replace />} />

        <Route element={<UserLayout />}>
          <Route path="/" element={<Navigate to="/workspace/dashboard" replace />} />
          <Route path="/workspace/dashboard" element={<DashboardPage />} />
          <Route path="/workspace/usage" element={<UsagePage />} />
          <Route path="/workspace/tokens" element={<TokensPage />} />
          <Route path="/workspace/models" element={<ModelsPage />} />
          <Route path="/workspace/topup" element={<TopupPage />} />
          <Route path="/workspace/profile" element={<ProfilePage />} />
        </Route>

        <Route element={<AdminLayout />}>
          <Route path="/admin/overview" element={<AdminOverviewPage />} />
          <Route path="/admin/users" element={<AdminUsersPage />} />
          <Route path="/admin/models" element={<Navigate to="/admin/public-models" replace />} />
          <Route path="/admin/brands" element={<AdminBrandsPage />} />
          <Route path="/admin/brands/:id" element={<AdminBrandDetailPage />} />
          <Route path="/admin/public-models" element={<AdminPublicModelsPage />} />
          <Route path="/admin/public-models/:id" element={<AdminPublicModelDetailPage />} />
          <Route path="/admin/upstream-models" element={<AdminUpstreamModelsPage />} />
          <Route path="/admin/upstream-models/:id" element={<AdminUpstreamModelDetailPage />} />
          <Route path="/admin/providers" element={<AdminProvidersPage />} />
          <Route path="/admin/providers/:id" element={<AdminProviderDetailPage />} />
          <Route path="/admin/provider-endpoints" element={<AdminProviderEndpointsPage />} />
          <Route path="/admin/provider-endpoints/:id" element={<AdminProviderEndpointDetailPage />} />
          <Route path="/admin/provider-credentials" element={<AdminProviderCredentialsPage />} />
          <Route path="/admin/provider-credentials/:id" element={<AdminProviderCredentialDetailPage />} />
          <Route path="/admin/model-routes" element={<AdminModelRoutesPage />} />
          <Route path="/admin/model-routes/:id" element={<AdminModelRouteDetailPage />} />
          <Route path="/admin/api-models" element={<AdminApiModelsPage />} />
          <Route path="/admin/usage" element={<AdminUsagePage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/workspace/dashboard" replace />} />
    </Routes>
  );
};

export default App;

