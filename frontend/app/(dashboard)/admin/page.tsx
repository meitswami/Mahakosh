import Link from "next/link";
import { Settings, Users, Shield, Plug } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const adminSections = [
  { title: "User Management", description: "Manage users, roles, and permissions", icon: Users, href: "/admin" },
  { title: "Compliance Center", description: "Audit, retention, security events", icon: Shield, href: "/admin/compliance" },
  { title: "Roles & RBAC", description: "Configure role-based access control", icon: Shield, href: "/admin" },
  { title: "System Settings", description: "Tenant configuration and preferences", icon: Settings, href: "/admin" },
  { title: "Platform Control", description: "Multi-tenant super admin portal", icon: Plug, href: "/platform" },
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
                <Link key={section.title} href={section.href}>
                <Card className="cursor-pointer transition-shadow hover:shadow-md">
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
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
