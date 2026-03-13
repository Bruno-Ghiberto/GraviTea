import { ReactNode } from "react"
import {
  SidebarProvider,
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarInset,
  SidebarTrigger,
} from "@/components/layout/sidebar"
import Link from "next/link"

type AppShellProps = { children: ReactNode }

const nav = [
  { href: "/inventory", label: "Inventario" },
  { href: "/sales", label: "Ventas", disabled: true },
  { href: "/clients", label: "Clientes", disabled: true },
  { href: "/settings", label: "Configuración", disabled: true },
]

export function AppShell({ children }: AppShellProps) {
  return (
    <SidebarProvider>
      <Sidebar>
        <SidebarHeader className="p-4">
          <div className="space-y-1">
            <div className="text-sm font-semibold leading-none">GraviTea</div>
            <div className="text-xs text-muted-foreground">ERP • MVP</div>
          </div>
        </SidebarHeader>

        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>General</SidebarGroupLabel>
            <SidebarMenu>
              {nav.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton asChild disabled={item.disabled}>
                    <Link href={item.href}>{item.label}</Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter className="p-4">
          <div className="text-xs text-muted-foreground">
            <div className="font-medium text-foreground">Usuario</div>
            <div>Admin (provisorio)</div>
          </div>
        </SidebarFooter>
      </Sidebar>

      <SidebarInset>
        <header className="h-14 border-b flex items-center px-4 gap-2 bg-background/80 backdrop-blur sticky top-0 z-10">
          <SidebarTrigger />
          <div className="text-sm text-muted-foreground">Área de trabajo</div>
        </header>

        <main className="p-6">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  )
}
