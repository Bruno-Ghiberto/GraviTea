"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { ProductsTab } from "@/components/inventario/products-tab";
import { CategoriesTab } from "@/components/inventario/categories-tab";
import { SuppliersTab } from "@/components/inventario/suppliers-tab";
import { MovementsTab } from "@/components/inventario/movements-tab";
import { PriceListsTab } from "@/components/inventario/price-lists-tab";
import { PriceHistoryTab, CostHistoryTab } from "@/components/inventario/history-tabs";

export default function InventarioPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Inventory</h1>
      <Separator />
      <Tabs defaultValue="products">
        <TabsList className="flex-wrap">
          <TabsTrigger value="products">Products</TabsTrigger>
          <TabsTrigger value="categories">Categories</TabsTrigger>
          <TabsTrigger value="suppliers">Suppliers</TabsTrigger>
          <TabsTrigger value="movements">Movements</TabsTrigger>
          <TabsTrigger value="price-lists">Price Lists</TabsTrigger>
          <TabsTrigger value="price-history">Price History</TabsTrigger>
          <TabsTrigger value="cost-history">Cost History</TabsTrigger>
        </TabsList>
        <TabsContent value="products" className="mt-4">
          <ProductsTab />
        </TabsContent>
        <TabsContent value="categories" className="mt-4">
          <CategoriesTab />
        </TabsContent>
        <TabsContent value="suppliers" className="mt-4">
          <SuppliersTab />
        </TabsContent>
        <TabsContent value="movements" className="mt-4">
          <MovementsTab />
        </TabsContent>
        <TabsContent value="price-lists" className="mt-4">
          <PriceListsTab />
        </TabsContent>
        <TabsContent value="price-history" className="mt-4">
          <PriceHistoryTab />
        </TabsContent>
        <TabsContent value="cost-history" className="mt-4">
          <CostHistoryTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
