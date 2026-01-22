import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Link } from "react-router-dom";
import { ArrowLeft, Building2, Shield, Bell, Loader2, Database } from "lucide-react";
import { useCurrentOrg } from "@/hooks/useOrgData";
import { AuditTrailViewer } from "@/components/AuditTrailViewer";
import { OrgDataRetentionSettings } from "@/components/OrgDataRetentionSettings";

const OrgSettings = () => {
  const { data: orgUser, isLoading } = useCurrentOrg();
  const organisation = orgUser?.organisation as { id: string; name: string; description?: string; industry?: string; website?: string; recording_retention_days?: number | null } | null;
  const [activeTab, setActiveTab] = useState("audit");

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!organisation) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="p-8 max-w-md text-center">
          <h2 className="text-xl font-semibold mb-4">No Organisation Found</h2>
          <p className="text-muted-foreground mb-6">
            You're not part of any organisation yet.
          </p>
          <Button asChild>
            <Link to="/org/onboarding">Create Organisation</Link>
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/org">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Link>
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold">T</span>
            </div>
            <span className="text-xl font-bold">Talenti</span>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Organisation Settings</h1>
          <p className="text-muted-foreground">
            Manage your organisation settings, security, and audit trail
          </p>
        </div>

        {/* Settings Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full max-w-xl grid-cols-4">
            <TabsTrigger value="general" className="gap-2">
              <Building2 className="w-4 h-4" />
              General
            </TabsTrigger>
            <TabsTrigger value="retention" className="gap-2">
              <Database className="w-4 h-4" />
              Data Retention
            </TabsTrigger>
            <TabsTrigger value="audit" className="gap-2">
              <Shield className="w-4 h-4" />
              Audit Trail
            </TabsTrigger>
            <TabsTrigger value="notifications" className="gap-2">
              <Bell className="w-4 h-4" />
              Notifications
            </TabsTrigger>
          </TabsList>

          {/* General Settings Tab */}
          <TabsContent value="general">
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-6">Organisation Details</h2>
              
              <div className="space-y-4 max-w-lg">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Organisation Name
                  </label>
                  <p className="text-lg font-medium mt-1">{organisation.name}</p>
                </div>
                
                {organisation.industry && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Industry
                    </label>
                    <p className="mt-1">{organisation.industry}</p>
                  </div>
                )}
                
                {organisation.website && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Website
                    </label>
                    <p className="mt-1">
                      <a 
                        href={organisation.website} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        {organisation.website}
                      </a>
                    </p>
                  </div>
                )}
                
                {organisation.description && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Description
                    </label>
                    <p className="mt-1 text-muted-foreground">{organisation.description}</p>
                  </div>
                )}

                <div className="pt-4">
                  <Button variant="outline" disabled>
                    Edit Organisation (Coming Soon)
                  </Button>
                </div>
              </div>
            </Card>
          </TabsContent>

          {/* Data Retention Tab */}
          <TabsContent value="retention">
            <OrgDataRetentionSettings
              organisationId={organisation.id}
              currentRetentionDays={organisation.recording_retention_days ?? 60}
            />
          </TabsContent>

          {/* Audit Trail Tab */}
          <TabsContent value="audit">
            <AuditTrailViewer organisationId={organisation.id} />
          </TabsContent>

          {/* Notifications Tab */}
          <TabsContent value="notifications">
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-6">Notification Preferences</h2>
              
              <div className="space-y-6">
                <div className="flex items-center justify-between p-4 rounded-lg border border-border">
                  <div>
                    <p className="font-medium">Interview Completed</p>
                    <p className="text-sm text-muted-foreground">
                      Get notified when a candidate completes their interview
                    </p>
                  </div>
                  <Button variant="outline" size="sm" disabled>
                    Coming Soon
                  </Button>
                </div>
                
                <div className="flex items-center justify-between p-4 rounded-lg border border-border">
                  <div>
                    <p className="font-medium">New Application</p>
                    <p className="text-sm text-muted-foreground">
                      Get notified when a new candidate applies to a role
                    </p>
                  </div>
                  <Button variant="outline" size="sm" disabled>
                    Coming Soon
                  </Button>
                </div>
                
                <div className="flex items-center justify-between p-4 rounded-lg border border-border">
                  <div>
                    <p className="font-medium">Weekly Summary</p>
                    <p className="text-sm text-muted-foreground">
                      Receive a weekly summary of recruitment activity
                    </p>
                  </div>
                  <Button variant="outline" size="sm" disabled>
                    Coming Soon
                  </Button>
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default OrgSettings;
