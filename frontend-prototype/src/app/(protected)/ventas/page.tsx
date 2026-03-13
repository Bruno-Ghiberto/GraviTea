"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { CustomersTab } from "@/components/ventas/customers-tab";
import { OrdersTab } from "@/components/ventas/orders-tab";

export default function VentasPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Sales</h1>
      <Separator />
      <Tabs defaultValue="customers">
        <TabsList>
          <TabsTrigger value="customers">Customers</TabsTrigger>
          <TabsTrigger value="orders">Orders</TabsTrigger>
        </TabsList>
        <TabsContent value="customers" className="mt-4">
          <CustomersTab />
        </TabsContent>
        <TabsContent value="orders" className="mt-4">
          <OrdersTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
