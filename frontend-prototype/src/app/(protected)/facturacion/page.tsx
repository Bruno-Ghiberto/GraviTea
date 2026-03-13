"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { CredentialsTab } from "@/components/facturacion/credentials-tab";
import { PuntosVentaTab } from "@/components/facturacion/puntos-venta-tab";
import { ComprobantesTab } from "@/components/facturacion/comprobantes-tab";
import { CAEATab } from "@/components/facturacion/caea-tab";

export default function FacturacionPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Invoicing (ARCA)</h1>
      <Separator />
      <Tabs defaultValue="comprobantes">
        <TabsList className="flex-wrap">
          <TabsTrigger value="comprobantes">Comprobantes</TabsTrigger>
          <TabsTrigger value="credentials">Credentials</TabsTrigger>
          <TabsTrigger value="puntos-venta">Puntos de Venta</TabsTrigger>
          <TabsTrigger value="caea">CAEA</TabsTrigger>
        </TabsList>
        <TabsContent value="comprobantes" className="mt-4">
          <ComprobantesTab />
        </TabsContent>
        <TabsContent value="credentials" className="mt-4">
          <CredentialsTab />
        </TabsContent>
        <TabsContent value="puntos-venta" className="mt-4">
          <PuntosVentaTab />
        </TabsContent>
        <TabsContent value="caea" className="mt-4">
          <CAEATab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
