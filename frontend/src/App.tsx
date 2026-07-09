import { Navigate, Route, Routes } from "react-router-dom";
import AdminLayout from "./layouts/AdminLayout";
import AuthLayout from "./layouts/AuthLayout";
import UserLayout from "./layouts/UserLayout";
import RequireAuth from "./routes/RequireAuth";
import { lazy, Suspense } from "react";
import LoadingScreen from "./pages/LoadingScreen";

const LoginPage = lazy(() => import("./pages/Login"));
const DashboardPage = lazy(() => import("./pages/Dashboard"));
const ProfilePage = lazy(() => import("./pages/Profile"));
const ModelsPage = lazy(() => import("./pages/Models"));
const TokensPage = lazy(() => import("./pages/Tokens"));
const TopupPage = lazy(() => import("./pages/Topup"));
const UsagePage = lazy(() => import("./pages/Usage"));
const AdminOverviewPage = lazy(() => import("./pages/admin/AdminOverview"));
const AdminUsersPage = lazy(() => import("./pages/admin/AdminUsers"));
const AdminUsagePage = lazy(() => import("./pages/admin/AdminUsage"));
const AdminProviderHealthPage = lazy(() => import("./pages/admin/AdminProviderHealth"));
const AdminUsageDashboardPage = lazy(() => import("./pages/admin/AdminUsageDashboard"));
const AdminApiModelsPage = lazy(() => import("./pages/admin/AdminApiModels"));

const AdminBrandDetailPage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminBrandDetailPage })));
const AdminBrandCreatePage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminBrandCreatePage })));
const AdminBrandsPage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminBrandsPage })));
const AdminModelRouteCreatePage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminModelRouteCreatePage })));
const AdminModelRouteDetailPage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminModelRouteDetailPage })));
const AdminModelRoutesPage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminModelRoutesPage })));
const AdminProviderCredentialCreatePage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminProviderCredentialCreatePage })));
const AdminProviderCredentialDetailPage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminProviderCredentialDetailPage })));
const AdminProviderCredentialsPage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminProviderCredentialsPage })));
const AdminProviderCreatePage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminProviderCreatePage })));
const AdminProviderDetailPage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminProviderDetailPage })));
const AdminProviderEndpointCreatePage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminProviderEndpointCreatePage })));
const AdminProviderEndpointDetailPage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminProviderEndpointDetailPage })));
const AdminProviderEndpointsPage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminProviderEndpointsPage })));
const AdminProvidersPage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminProvidersPage })));
const AdminPublicModelCreatePage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminPublicModelCreatePage })));
const AdminPublicModelDetailPage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminPublicModelDetailPage })));
const AdminPublicModelsPage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminPublicModelsPage })));
const AdminUpstreamModelCreatePage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminUpstreamModelCreatePage })));
const AdminUpstreamModelDetailPage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminUpstreamModelDetailPage })));
const AdminUpstreamModelsPage = lazy(() => import("./pages/admin/AdminCatalogPages").then(m => ({ default: m.AdminUpstreamModelsPage })));

const App = () => {
  return (
    <Suspense fallback={<LoadingScreen />}>
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
            <Route path="/admin/brands/new" element={<AdminBrandCreatePage />} />
            <Route path="/admin/brands/:id" element={<AdminBrandDetailPage />} />
            <Route path="/admin/public-models" element={<AdminPublicModelsPage />} />
            <Route path="/admin/public-models/new" element={<AdminPublicModelCreatePage />} />
            <Route path="/admin/public-models/:id" element={<AdminPublicModelDetailPage />} />
            <Route path="/admin/upstream-models" element={<AdminUpstreamModelsPage />} />
            <Route path="/admin/upstream-models/new" element={<AdminUpstreamModelCreatePage />} />
            <Route path="/admin/upstream-models/:id" element={<AdminUpstreamModelDetailPage />} />
            <Route path="/admin/providers" element={<AdminProvidersPage />} />
            <Route path="/admin/providers/new" element={<AdminProviderCreatePage />} />
            <Route path="/admin/providers/:id" element={<AdminProviderDetailPage />} />
            <Route path="/admin/provider-endpoints" element={<AdminProviderEndpointsPage />} />
            <Route path="/admin/provider-endpoints/new" element={<AdminProviderEndpointCreatePage />} />
            <Route path="/admin/provider-endpoints/:id" element={<AdminProviderEndpointDetailPage />} />
            <Route path="/admin/provider-credentials" element={<AdminProviderCredentialsPage />} />
            <Route path="/admin/provider-credentials/new" element={<AdminProviderCredentialCreatePage />} />
            <Route path="/admin/provider-credentials/:id" element={<AdminProviderCredentialDetailPage />} />
            <Route path="/admin/model-routes" element={<AdminModelRoutesPage />} />
            <Route path="/admin/model-routes/new" element={<AdminModelRouteCreatePage />} />
            <Route path="/admin/model-routes/:id" element={<AdminModelRouteDetailPage />} />
            <Route path="/admin/api-models" element={<AdminApiModelsPage />} />
            <Route path="/admin/usage" element={<AdminUsagePage />} />
            <Route path="/admin/provider-health" element={<AdminProviderHealthPage />} />
            <Route path="/admin/usage-dashboard" element={<AdminUsageDashboardPage />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/workspace/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
};

export default App;
