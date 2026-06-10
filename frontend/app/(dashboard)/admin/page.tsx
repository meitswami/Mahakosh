import { Settings, Users, Shield, Plug } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const adminSections = [
  { title: "User Management", description: "Manage users, roles, and permissions", icon: Users },
  { title: "Roles & RBAC", description: "Configure role-based access control", icon: Shield },
  { title: "System Settings", description: "Tenant configuration and preferences", icon: Settings },
  { title: "Connectors", description: "MCP connectors and Tally integration", icon: Plug },
];

export default function AdminPage() {
  return (
    <>
      <Header title="Administration" description="Manage users, roles, and system configuration" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl">
          <div className="grid gap-4 sm:grid-cols-2">
            {adminSections.map((section) => {
              const Icon = section.icon;
              return (
                <Card key={section.title} className="cursor-pointer transition-shadow hover:shadow-md">
                  <CardHeader className="flex flex-row items-center gap-4 space-y-0">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                      <Icon className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-base">{section.title}</CardTitle>
                      <p className="text-sm text-muted-foreground">{section.description}</p>
                    </div>
                  </CardHeader>
                  <CardContent />
                </Card>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
