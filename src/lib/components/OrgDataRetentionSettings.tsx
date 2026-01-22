import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { supabase } from "@/integrations/supabase/client";
import { toast } from "sonner";
import { Loader2, HardDrive, Clock } from "lucide-react";

interface OrgDataRetentionSettingsProps {
  organisationId: string;
  currentRetentionDays: number | null;
}

export const OrgDataRetentionSettings = ({
  organisationId,
  currentRetentionDays,
}: OrgDataRetentionSettingsProps) => {
  const [retentionDays, setRetentionDays] = useState(currentRetentionDays ?? 60);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const { error } = await supabase
        .from("organisations")
        .update({ recording_retention_days: retentionDays })
        .eq("id", organisationId);

      if (error) throw error;

      toast.success("Data retention settings updated successfully");
    } catch (error) {
      console.error("Error updating retention settings:", error);
      toast.error("Failed to update data retention settings");
    } finally {
      setIsSaving(false);
    }
  };

  const hasChanges = retentionDays !== (currentRetentionDays ?? 60);

  return (
    <Card className="p-6">
      <h2 className="text-xl font-semibold mb-6">Data Retention Settings</h2>

      <div className="space-y-8 max-w-lg">
        {/* Recording Retention Period */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <HardDrive className="w-5 h-5 text-muted-foreground" />
            <Label className="text-base font-medium">
              Interview Recording Retention
            </Label>
          </div>
          
          <p className="text-sm text-muted-foreground">
            Interview recordings will be automatically deleted after the specified
            number of days. Transcripts and scores are retained separately.
          </p>

          <div className="space-y-4 pt-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">30 days</span>
              <span className="text-2xl font-bold text-primary">
                {retentionDays} days
              </span>
              <span className="text-sm text-muted-foreground">60 days</span>
            </div>
            
            <Slider
              value={[retentionDays]}
              onValueChange={(value) => setRetentionDays(value[0])}
              min={30}
              max={60}
              step={1}
              className="w-full"
            />
          </div>
        </div>

        {/* Info Box */}
        <div className="flex items-start gap-3 p-4 rounded-lg bg-muted/50 border border-border">
          <Clock className="w-5 h-5 text-muted-foreground mt-0.5" />
          <div className="space-y-1">
            <p className="text-sm font-medium">Automatic Cleanup</p>
            <p className="text-sm text-muted-foreground">
              Recordings older than {retentionDays} days will be automatically
              removed during the daily cleanup process. This helps maintain
              compliance with data retention policies.
            </p>
          </div>
        </div>

        {/* Save Button */}
        <Button
          onClick={handleSave}
          disabled={isSaving || !hasChanges}
          className="w-full sm:w-auto"
        >
          {isSaving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
          Save Changes
        </Button>
      </div>
    </Card>
  );
};
