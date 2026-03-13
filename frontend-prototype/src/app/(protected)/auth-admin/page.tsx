"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { OperationsTab } from "@/components/auth/operations-tab";
import { UsersTab } from "@/components/auth/users-tab";
import { BranchesTab } from "@/components/auth/branches-tab";
import { RolesTab } from "@/components/auth/roles-tab";

export default function AuthAdminPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Auth Admin</h1>
      <Separator />
      <Tabs defaultValue="users">
        <TabsList>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="branches">Branches</TabsTrigger>
          <TabsTrigger value="roles">Roles</TabsTrigger>
          <TabsTrigger value="operations">Operations</TabsTrigger>
        </TabsList>
        <TabsContent value="users" className="mt-4">
          <UsersTab />
        </TabsContent>
        <TabsContent value="branches" className="mt-4">
          <BranchesTab />
        </TabsContent>
        <TabsContent value="roles" className="mt-4">
          <RolesTab />
        </TabsContent>
        <TabsContent value="operations" className="mt-4">
          <OperationsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
