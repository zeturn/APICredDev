---
id: beancs-deployment
title: BeanCS 云端部署教程
slug: /beancs-deployment
---

本文说明 APICred 在 BeanCS k3s 集群上的当前部署逻辑。生产入口为：

- APICred: `https://apicred.beancs.hollowdata.com`
- BasaltPass: `https://auth.beancs.hollowdata.com`
- Tenant: `hollowdata`
- Kubernetes namespace: `apicred`
- 镜像仓库: `registry.beancs.hollowdata.com/hollowdata`
- GitOps 仓库: `HollowData/gitops-manifests-beancs`
- 应用源码仓库: `zeturn/APICredDev`

## 1. 总体逻辑

APICred 的云端发布分成两条线：

1. `APICredDev` 保存应用源码、RBAC 定义、前后端镜像构建上下文。
2. `gitops-manifests-beancs` 保存 Kubernetes 期望状态，由 ArgoCD 同步到 k3s。

发布时不要直接在集群里长期手改 Deployment。正确流程是：

1. 在 APICred 源码仓库提交代码。
2. 构建 backend/frontend 镜像并推送到 Harbor。
3. 在 GitOps 仓库更新镜像 tag、环境变量、Ingress、Secret 引用或依赖配置。
4. 推送 GitOps 仓库。
5. ArgoCD 自动同步，或手动 sync。
6. 通过域名、Pod 状态、Ingress、日志做验收。

## 2. BasaltPass 应用注册

在 `https://auth.beancs.hollowdata.com` 的 `hollowdata` tenant 中注册 APICred 应用。

建议应用配置：

- 应用名称: `APICred`
- 应用域名: `https://apicred.beancs.hollowdata.com`
- OAuth 回调地址:
  - `https://apicred.beancs.hollowdata.com/v1/auth/basalt/callback`
  - `https://apicred.beancs.hollowdata.com/v1/auth/basalt/oauth/<provider>/callback`
- OAuth scopes: `openid profile email`
- OAuth grant types: `authorization_code`, `refresh_token`
- S2S grant type: `client_credentials`
- PKCE: 开启

然后导入 APICred 仓库里的 RBAC 定义：

```bash
APICredDev/.basalt/rbac.json
```

这个文件应包含用户控制台、管理员控制台和 APICred 资源权限，例如：

- `user_console`
- `admin_console`
- `apicred.read`
- `apicred.write`
- `apicred.admin`

管理员账号至少需要以下任一组合：

- 角色包含 `apicred_admin`
- 或权限包含 `admin_console` 和 `apicred.admin`

普通用户进入用户控制台至少需要 `user_console`。

## 3. 依赖资源

APICred 依赖 PostgreSQL 和 Redis。当前生产推荐由 GitOps 创建依赖应用：

- `apicred-postgres`
- `apicred-redis`

APICred backend 只通过环境变量连接依赖，不在代码中写死连接信息。

常见 Secret：

- `apicred-postgres-credentials`
- `apicred-redis-credentials`
- `app-env-vars-apicred-backend`
- `beancs-registry-pull`

Secret 中只保存值，GitOps manifest 中只保存引用。

## 4. 后端环境变量

生产环境至少需要：

```env
PRODUCTION_MODE=true
APP_ENV=prod
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
APP_SECRET=...
TOKEN_SALT=...
ENCRYPTION_KEY=...

BASALT_BASE_URL=https://auth.beancs.hollowdata.com
BASALT_INTERNAL_BASE_URL=https://auth.beancs.hollowdata.com
BASALT_OAUTH_CLIENT_ID=...
BASALT_OAUTH_CLIENT_SECRET=...
BASALT_S2S_CLIENT_ID=...
BASALT_S2S_CLIENT_SECRET=...
BASALT_DEFAULT_TENANT_ID=2
BASALT_TENANT_ADMIN_ROLE_CODES=tenant,owner,admin,tenant_admin,aadmin,apicred_admin
BASALT_ADMIN_PERMISSION_CODES=admin_console,apicred.admin

APICRED_PUBLIC_BASE_URL=https://apicred.beancs.hollowdata.com
FRONTEND_BASE_URL=https://apicred.beancs.hollowdata.com
CORS_ORIGINS=["https://apicred.beancs.hollowdata.com"]
STARTUP_BOOTSTRAP_ENABLED=false
```

注意事项：

- `STARTUP_BOOTSTRAP_ENABLED=false`：生产环境不要靠启动脚本长期写入默认资源。
- `BASALT_TENANT_ADMIN_ROLE_CODES` 必须包含 `apicred_admin`，否则管理员可能看到 `missing admin role`。
- `BASALT_ADMIN_PERMISSION_CODES` 必须包含 `admin_console,apicred.admin`。
- 不要把任何 secret value 提交到 Git。

## 5. 前端构建变量

前端构建时需要把 API 和 BasaltPass 地址写入静态包：

```env
VITE_API_BASE_URL=https://apicred.beancs.hollowdata.com/v1
VITE_BASALTPASS_BASE_URL=https://auth.beancs.hollowdata.com
```

如果用户刷新 `/admin/overview`、`/admin/brands/new` 等前端路由返回 404，说明前端 Nginx 没有 SPA fallback。生产 Nginx 配置必须包含：

```nginx
try_files $uri $uri/ /index.html;
```

当前 GitOps 中通过 ConfigMap 挂载 Nginx 配置解决这个问题。

## 6. 构建并推送镜像

先确认当前 commit：

```bash
git -C APICredDev rev-parse --short HEAD
```

后端镜像：

```bash
docker build `
  -t registry.beancs.hollowdata.com/hollowdata/apicred-backend:beancs-<sha> `
  -f APICredDev/backend/Dockerfile `
  APICredDev/backend

docker push registry.beancs.hollowdata.com/hollowdata/apicred-backend:beancs-<sha>
```

前端镜像：

```bash
cd APICredDev/frontend
npm ci
$env:VITE_API_BASE_URL="https://apicred.beancs.hollowdata.com/v1"
$env:VITE_BASALTPASS_BASE_URL="https://auth.beancs.hollowdata.com"
npm run build
cd ../..

docker build `
  -t registry.beancs.hollowdata.com/hollowdata/apicred-frontend:beancs-<sha> `
  -f APICredDev/frontend/Dockerfile.static `
  APICredDev/frontend

docker push registry.beancs.hollowdata.com/hollowdata/apicred-frontend:beancs-<sha>
```

`Dockerfile.static` 使用已经生成好的 `dist` 目录，适合在本机或 CI 已经完成前端构建后打静态镜像。

## 7. GitOps 配置

在 `gitops-manifests-beancs` 中维护 APICred 的 Kubernetes 配置。典型结构：

```text
apps/apicred/
  application.yaml
  base/
    deployment-backend.yaml
    deployment-frontend.yaml
    service-backend.yaml
    service-frontend.yaml
    ingress.yaml
    configmap-frontend-nginx.yaml
  dependencies/
    postgres/application.yaml
    redis/application.yaml
  overlays/
    prod/kustomization.yaml
```

每次发布应用版本时，更新 overlay 或 deployment 中的镜像 tag：

```yaml
images:
  - name: registry.beancs.hollowdata.com/hollowdata/apicred-backend
    newTag: beancs-<sha>
  - name: registry.beancs.hollowdata.com/hollowdata/apicred-frontend
    newTag: beancs-<sha>
```

然后提交并推送：

```bash
git -C gitops-manifests-beancs status
git -C gitops-manifests-beancs add apps/apicred
git -C gitops-manifests-beancs commit -m "beancs: deploy apicred <change>"
git -C gitops-manifests-beancs push
```

## 8. ArgoCD 同步

如果 APICred ArgoCD Application 已存在，推送 GitOps 后等待自动同步即可。

首次接入时可以应用 Application：

```bash
kubectl apply -f gitops-manifests-beancs/apps/apicred/dependencies/postgres/application.yaml
kubectl apply -f gitops-manifests-beancs/apps/apicred/dependencies/redis/application.yaml
kubectl apply -f gitops-manifests-beancs/apps/apicred/application.yaml
```

查看同步状态：

```bash
kubectl -n argocd get applications apicred apicred-postgres apicred-redis
```

ArgoCD 可能显示 `Synced / Progressing`，需要结合实际资源判断。只要 Pod、Service、Ingress 正常，域名可访问，就可以继续验收。

## 9. DNS、TLS 和 Ingress

Cloudflare 中需要有：

```text
apicred.beancs.hollowdata.com -> 15.204.119.110
```

证书由 cert-manager 签发，Ingress 通常需要：

```yaml
metadata:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
```

HTTP-01 验证要求域名能解析到集群入口。如果证书长时间 pending，先查 DNS，再查 cert-manager challenge。

## 10. 节点调度

当前 APICred 镜像按 `amd64` 构建。若集群同时有 `arm64` 节点，需要在 Deployment 中限制调度：

```yaml
nodeSelector:
  kubernetes.io/arch: amd64
```

如果某个节点磁盘压力导致 Pod 被 Evicted，可以临时 pin 到稳定节点，例如：

```yaml
nodeSelector:
  kubernetes.io/hostname: hdtbcs-ovh1
```

长期方案是清理节点 ephemeral storage、设置合理 requests/limits，或构建多架构镜像。

## 11. 数据库迁移

Backend Deployment 的 initContainer 应在主容器启动前运行：

```bash
alembic upgrade head
```

迁移注意事项：

- Alembic revision id 长度不要超过数据库字段限制。
- 删除字段或索引时尽量写成 idempotent migration。
- 生产 schema 只能通过 migration 演进，不要手动改表后忘记回写 migration。

## 12. 验收命令

```bash
kubectl -n apicred get pods,svc,ingress
kubectl -n apicred rollout status deployment/apicred-backend
kubectl -n apicred rollout status deployment/apicred-frontend
kubectl -n argocd get applications apicred apicred-postgres apicred-redis
```

HTTP 验收：

```bash
curl -I https://apicred.beancs.hollowdata.com/
curl -I https://apicred.beancs.hollowdata.com/admin/overview
curl https://apicred.beancs.hollowdata.com/health
```

功能验收：

1. 普通用户可以通过 BasaltPass 登录。
2. 拥有 `user_console` 的用户可以进入用户控制台。
3. 拥有 `apicred_admin` 或 `admin_console,apicred.admin` 的用户可以进入 admin。
4. admin 可以创建 provider、endpoint、credential、public model、upstream model、route。
5. 刷新任意前端路由不会 404。

## 13. 常见问题

### `missing permission: user_console`

原因通常是 RBAC 没导入、用户没有绑定 APICred 应用角色，或 tenant 选错。

处理：

1. 重新导入 `APICredDev/.basalt/rbac.json`。
2. 确认用户在 `hollowdata` tenant 下。
3. 给用户分配包含 `user_console` 的 APICred 角色。

### `admin_unauthorized: missing admin role`

原因通常是 APICred 后端只认默认管理员角色，没有把 `apicred_admin` 当作管理员。

处理：

```env
BASALT_TENANT_ADMIN_ROLE_CODES=tenant,owner,admin,tenant_admin,aadmin,apicred_admin
BASALT_ADMIN_PERMISSION_CODES=admin_console,apicred.admin
```

更新 GitOps 后重启 backend。

### 刷新 `/admin/overview` 返回 404

原因是 Nginx 按真实文件查找前端路由。

处理：给前端 Nginx 加 SPA fallback：

```nginx
try_files $uri $uri/ /index.html;
```

### Pod 报镜像平台不匹配

如果错误类似 `no match for platform in manifest`，说明 `arm64` 节点拉了 `amd64` 镜像。

处理：

- 临时：Deployment 加 `nodeSelector: kubernetes.io/arch: amd64`。
- 长期：构建并推送 multi-arch 镜像。

### Pod 被 Evicted

通常是节点 ephemeral storage 不足。

处理：

1. 查看节点磁盘和 kubelet eviction 信息。
2. 清理无用镜像、日志和临时文件。
3. 给 APICred Pod 设置 requests/limits。
4. 必要时 pin 到磁盘更稳定的节点。

### 证书 pending

处理顺序：

1. 确认 Cloudflare DNS 解析正确。
2. 确认 HTTP-01 challenge 能从公网访问。
3. 查看 cert-manager 日志和 challenge 状态。

### 生产启动拒绝 bootstrap

生产环境应关闭启动期 bootstrap：

```env
STARTUP_BOOTSTRAP_ENABLED=false
```

模型、provider、credential、route 应通过 admin 控制台创建和维护。

## 14. 安全要求

- 不要提交 BasaltPass、Harbor、数据库、Redis 的 secret value。
- GitOps 只提交 Secret 引用，不提交 Secret 明文。
- 如果凭据曾在聊天、日志或命令输出中暴露，应立即轮换。
- 管理员权限优先用 APICred app role 授权，不要给用户全局超权。
- Provider credentials 只能通过 admin 页面录入并加密存库。
