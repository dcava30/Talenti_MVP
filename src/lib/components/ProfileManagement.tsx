import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/hooks/use-toast";
import { useNavigate } from "react-router-dom";
import {
  Pause,
  Play,
  Trash2,
  Eye,
  EyeOff,
  AlertTriangle,
  Shield,
  Loader2,
} from "lucide-react";

interface VisibilitySettings {
  name: boolean;
  email: boolean;
  phone: boolean;
  location: boolean;
  education: boolean;
  employment: boolean;
  skills: boolean;
  portfolio: boolean;
  linkedin: boolean;
}

const defaultVisibilitySettings: VisibilitySettings = {
  name: true,
  email: false,
  phone: false,
  location: true,
  education: true,
  employment: true,
  skills: true,
  portfolio: true,
  linkedin: true,
};

interface ProfileManagementProps {
  userId: string;
}

const ProfileManagement = ({ userId }: ProfileManagementProps) => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isPausing, setIsPausing] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [settings, setSettings] = useState<VisibilitySettings>(defaultVisibilitySettings);
  const [isSavingVisibility, setIsSavingVisibility] = useState(false);

  useEffect(() => {
    loadProfileSettings();
  }, [userId]);

  const loadProfileSettings = async () => {
    setIsLoading(true);
    try {
      const { data } = await supabase
        .from("candidate_profiles")
        .select("paused_at, visibility_settings")
        .eq("user_id", userId)
        .maybeSingle();

      if (data) {
        setIsPaused(!!data.paused_at);
        if (data.visibility_settings && typeof data.visibility_settings === "object" && !Array.isArray(data.visibility_settings)) {
          setSettings({ ...defaultVisibilitySettings, ...(data.visibility_settings as unknown as Partial<VisibilitySettings>) });
        }
      }
    } catch (error) {
      console.error("Error loading profile settings:", error);
    }
    setIsLoading(false);
  };

  const handlePauseProfile = async () => {
    setIsPausing(true);
    try {
      const newPausedState = !isPaused;
      const { error } = await supabase
        .from("candidate_profiles")
        .update({
          profile_visibility: newPausedState ? "hidden" : "visible",
          paused_at: newPausedState ? new Date().toISOString() : null,
        })
        .eq("user_id", userId);

      if (error) throw error;

      setIsPaused(newPausedState);
      toast({
        title: newPausedState ? "Profile Paused" : "Profile Unpaused",
        description: newPausedState
          ? "Your profile is hidden from new job matching."
          : "Your profile is now visible to employers.",
      });
    } catch (error) {
      console.error("Error pausing profile:", error);
      toast({
        title: "Error",
        description: "Failed to update profile visibility.",
        variant: "destructive",
      });
    }
    setIsPausing(false);
  };

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    try {
      // Delete all related data
      await Promise.all([
        supabase.from("candidate_skills").delete().eq("user_id", userId),
        supabase.from("employment_history").delete().eq("user_id", userId),
        supabase.from("education").delete().eq("user_id", userId),
        supabase.from("candidate_dei").delete().eq("user_id", userId),
        supabase.from("practice_interviews").delete().eq("user_id", userId),
      ]);

      // Delete profile
      await supabase.from("candidate_profiles").delete().eq("user_id", userId);

      // Sign out
      await supabase.auth.signOut();

      toast({
        title: "Account Deleted",
        description: "Your account has been permanently deleted.",
      });
      navigate("/");
    } catch (error) {
      console.error("Error deleting account:", error);
      toast({
        title: "Error",
        description: "Failed to delete account. Please try again or contact support.",
        variant: "destructive",
      });
    }
    setIsDeleting(false);
  };

  const handleVisibilityChange = async (field: keyof VisibilitySettings, value: boolean) => {
    const newSettings = { ...settings, [field]: value };
    setSettings(newSettings);
    
    setIsSavingVisibility(true);
    try {
      const { error } = await supabase
        .from("candidate_profiles")
        .update({ visibility_settings: newSettings })
        .eq("user_id", userId);

      if (error) throw error;
    } catch (error) {
      console.error("Error updating visibility:", error);
      setSettings(settings); // Revert on error
    }
    setIsSavingVisibility(false);
  };

  const visibilityFields: { key: keyof VisibilitySettings; label: string; description: string }[] = [
    { key: "name", label: "Full Name", description: "Your first and last name" },
    { key: "email", label: "Email Address", description: "Your contact email" },
    { key: "phone", label: "Phone Number", description: "Your phone number" },
    { key: "location", label: "Location", description: "Your suburb, state, and postcode" },
    { key: "education", label: "Education", description: "Your education history" },
    { key: "employment", label: "Work Experience", description: "Your employment history" },
    { key: "skills", label: "Skills", description: "Your listed skills" },
    { key: "portfolio", label: "Portfolio URL", description: "Link to your portfolio" },
    { key: "linkedin", label: "LinkedIn URL", description: "Link to your LinkedIn profile" },
  ];

  if (isLoading) {
    return (
      <Card className="p-6 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Profile Status */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold">Profile Status</h3>
            <p className="text-sm text-muted-foreground">
              Control whether employers can discover your profile
            </p>
          </div>
          <Badge variant={isPaused ? "secondary" : "default"}>
            {isPaused ? "Paused" : "Active"}
          </Badge>
        </div>

        <Button
          variant={isPaused ? "default" : "outline"}
          onClick={handlePauseProfile}
          disabled={isPausing}
        >
          {isPausing ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : isPaused ? (
            <Play className="w-4 h-4 mr-2" />
          ) : (
            <Pause className="w-4 h-4 mr-2" />
          )}
          {isPaused ? "Unpause Profile" : "Pause Profile"}
        </Button>

        {isPaused && (
          <p className="text-sm text-muted-foreground mt-3">
            Your profile is hidden from new job matching. Existing applications are not affected.
          </p>
        )}
      </Card>

      {/* Visibility Controls */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Visibility Controls</h3>
          {isSavingVisibility && (
            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
          )}
        </div>
        <p className="text-sm text-muted-foreground mb-6">
          Control which fields employers can see when viewing your profile
        </p>

        <div className="space-y-4">
          {visibilityFields.map((field) => (
            <div
              key={field.key}
              className="flex items-center justify-between py-2 border-b border-border last:border-0"
            >
              <div className="flex items-center gap-3">
                {settings[field.key] ? (
                  <Eye className="w-4 h-4 text-green-500" />
                ) : (
                  <EyeOff className="w-4 h-4 text-muted-foreground" />
                )}
                <div>
                  <Label className="font-medium">{field.label}</Label>
                  <p className="text-xs text-muted-foreground">{field.description}</p>
                </div>
              </div>
              <Switch
                checked={settings[field.key]}
                onCheckedChange={(checked) => handleVisibilityChange(field.key, checked)}
              />
            </div>
          ))}
        </div>
      </Card>

      {/* Delete Account */}
      <Card className="p-6 border-destructive/20">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="w-5 h-5 text-destructive" />
          <h3 className="font-semibold text-destructive">Danger Zone</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Permanently delete your account and all associated data. This action cannot be undone.
        </p>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive" disabled={isDeleting}>
              {isDeleting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Trash2 className="w-4 h-4 mr-2" />
              )}
              Delete Account
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. This will permanently delete your account and remove
                all your data including:
                <ul className="list-disc list-inside mt-2 space-y-1">
                  <li>Your profile information</li>
                  <li>Employment and education history</li>
                  <li>All applications and interview records</li>
                  <li>Uploaded documents and CV</li>
                </ul>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDeleteAccount}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                Yes, delete my account
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </Card>
    </div>
  );
};

export default ProfileManagement;