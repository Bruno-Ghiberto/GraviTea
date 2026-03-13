"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { SessionsTab } from "@/components/sync/sessions-tab";
import { OperationsTab } from "@/components/sync/operations-tab";
import { StatusTab } from "@/components/sync/status-tab";

export default function SyncPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Sync</h1>
      <Separator />
      <Tabs defaultValue="sessions">
        <TabsList>
          <TabsTrigger value="sessions">Sessions</TabsTrigger>
          <TabsTrigger value="operations">Push / Pull</TabsTrigger>
          <TabsTrigger value="status">Device Status</TabsTrigger>
        </TabsList>
        <TabsContent value="sessions" className="mt-4">
          <SessionsTab />
        </TabsContent>
        <TabsContent value="operations" className="mt-4">
          <OperationsTab />
        </TabsContent>
        <TabsContent value="status" className="mt-4">
          <StatusTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
