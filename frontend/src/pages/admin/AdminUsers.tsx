import { Badge, Button, Card, Table, TableBody, TableCell, TableHead, TableRow } from "../../lib/watercolor";
import { useEffect, useState } from "react";
import adminApi from "../../api/adminClient";
import { AdminPageIntro } from "./adminCommon";

const AdminUsersPage = () => {
  const [users, setUsers] = useState<any[]>([]);
  const adminToken = localStorage.getItem("admin_token") ?? "";

  const load = async () => {
    if (!adminToken) {
      setUsers([]);
      return;
    }
    const resp = await adminApi.get("/admin/users");
    setUsers(resp.data);
  };

  useEffect(() => {
    load();
  }, [adminToken]);

  const updateStatus = async (userId: string, status: string) => {
    await adminApi.post(`/admin/users/${userId}/status`, { status });
    await load();
  };

  return (
    <div className="space-y-6">
      <AdminPageIntro title="用户管理" description="查看用户余额、使用情况，并启用或禁用账号。" />
      <Card className="p-6">
        <div className="flex items-center justify-between gap-3">
          <div className="text-lg font-semibold text-slate-900">用户列表</div>
          <Badge variant="warning">{users.length}</Badge>
        </div>
        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableCell>邮箱</TableCell>
              <TableCell>状态</TableCell>
              <TableCell align="right">余额</TableCell>
              <TableCell align="right">已使用</TableCell>
              <TableCell align="right">调用次数</TableCell>
              <TableCell align="right">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {users.map((item) => (
              <TableRow key={item.id}>
                <TableCell>{item.email}</TableCell>
                <TableCell>{item.status}</TableCell>
                <TableCell align="right">{item.balance_credits}</TableCell>
                <TableCell align="right">{item.used_credits}</TableCell>
                <TableCell align="right">{item.usage_sessions}</TableCell>
                <TableCell align="right">
                  <div className="flex justify-end gap-2">
                    <Button buttonStyle="text" variant="secondary" onClick={() => updateStatus(item.id, "active")}>启用</Button>
                    <Button buttonStyle="text" variant="error" onClick={() => updateStatus(item.id, "disabled")}>禁用</Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {users.length === 0 && (
              <TableRow>
                <TableCell colSpan={6}>暂无用户数据</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
};

export default AdminUsersPage;
