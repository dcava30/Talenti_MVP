import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Users, Briefcase, TrendingUp, FileText, LogOut, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useCurrentOrg, useJobRoles, useOrgStats } from "@/hooks/useOrgData";
import { supabase } from "@/integrations/supabase/client";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";

const OrgDashboard = () => {
  const navigate = useNavigate();
  const { data: orgUser, isLoading: orgLoading } = useCurrentOrg();
  const organisation = orgUser?.organisation as { id: string; name: string } | null;
  
  const { data: jobRoles, isLoading: rolesLoading } = useJobRoles(organisation?.id);
  const { data: stats, isLoading: statsLoading } = useOrgStats(organisation?.id);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    toast.success("Signed out successfully");
    navigate("/auth");
  };

  const isLoading = orgLoading || rolesLoading || statsLoading;

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
            You're not part of any organisation yet. Create one to get started.
          </p>
          <Button asChild>
            <Link to="/org/onboarding">Create Organisation</Link>
          </Button>
        </Card>
      </div>
    );
  }

  const statsData = [
    { 
      label: "Active Roles", 
      value: stats?.activeRoles?.toString() || "0", 
      icon: Briefcase, 
      change: "Open positions" 
    },
    { 
      label: "Total Candidates", 
      value: stats?.totalCandidates?.toString() || "0", 
      icon: Users, 
      change: "Across all roles" 
    },
    { 
      label: "Interviews Completed", 
      value: stats?.completedInterviews?.toString() || "0", 
      icon: FileText, 
      change: "AI interviews" 
    },
    { 
      label: "Avg Match Score", 
      value: stats?.avgMatchScore ? `${stats.avgMatchScore}%` : "—", 
      icon: TrendingUp, 
      change: "Overall average" 
    },
  ];

  const getStatusVariant = (status: string): "default" | "secondary" | "outline" => {
    switch (status) {
      case "active":
        return "default";
      case "paused":
        return "secondary";
      case "closed":
        return "outline";
      default:
        return "secondary";
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold">T</span>
            </div>
            <span className="text-xl font-bold">{organisation.name}</span>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/org/settings">Settings</Link>
            </Button>
            <Button size="sm" asChild>
              <Link to="/org/new-role">
                <Plus className="w-4 h-4 mr-2" />
                New Role
              </Link>
            </Button>
            <Button variant="ghost" size="sm" onClick={handleSignOut}>
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Welcome back</h1>
          <p className="text-muted-foreground">Here's what's happening with your recruitment pipeline</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {statsData.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <Card key={index} className="p-6 hover:shadow-lg transition-shadow">
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                    <Icon className="w-6 h-6 text-primary" />
                  </div>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                  <p className="text-3xl font-bold">{stat.value}</p>
                  <p className="text-xs text-muted-foreground">{stat.change}</p>
                </div>
              </Card>
            );
          })}
        </div>

        {/* Roles List */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-semibold mb-1">Job Roles</h2>
              <p className="text-sm text-muted-foreground">Manage your open positions and candidates</p>
            </div>
            <Button variant="outline" asChild>
              <Link to="/org/new-role">
                <Plus className="w-4 h-4 mr-2" />
                Create Role
              </Link>
            </Button>
          </div>

          {jobRoles && jobRoles.length > 0 ? (
            <div className="space-y-4">
              {jobRoles.map((role) => (
                <div
                  key={role.id}
                  className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors cursor-pointer"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold">{role.title}</h3>
                      <Badge variant={getStatusVariant(role.status)}>
                        {role.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      {role.department && <span>{role.department}</span>}
                      {role.department && <span>•</span>}
                      {role.location && <span>{role.location}</span>}
                      {role.location && <span>•</span>}
                      <span>Created {formatDistanceToNow(new Date(role.created_at), { addSuffix: true })}</span>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" asChild>
                    <Link to={`/org/role/${role.id}`}>View Details</Link>
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <Briefcase className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4" />
              <h3 className="text-lg font-medium mb-2">No roles yet</h3>
              <p className="text-muted-foreground mb-4">Create your first job role to start receiving candidates</p>
              <Button asChild>
                <Link to="/org/new-role">
                  <Plus className="w-4 h-4 mr-2" />
                  Create Your First Role
                </Link>
              </Button>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default OrgDashboard;
