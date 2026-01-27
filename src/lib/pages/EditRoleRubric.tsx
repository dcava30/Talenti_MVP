import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Save, Loader2, Scale, RotateCcw } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { rolesApi } from "@/api/roles";
import { useCurrentOrg } from "@/hooks/useOrgData";
import { logAuditEvent } from "@/lib/auditLog";

interface ScoringDimension {
  dimension: string;
  label: string;
  description: string;
  weight: number;
}

const DEFAULT_DIMENSIONS: ScoringDimension[] = [
  { dimension: "technical_skills", label: "Technical Skills", description: "Relevant experience and domain expertise", weight: 20 },
  { dimension: "domain_knowledge", label: "Domain Knowledge", description: "Understanding of industry concepts", weight: 15 },
  { dimension: "communication", label: "Communication", description: "Clarity and articulation", weight: 15 },
  { dimension: "culture_fit", label: "Culture Fit", description: "Alignment with company values", weight: 15 },
  { dimension: "motivation", label: "Motivation", description: "Enthusiasm for the role", weight: 10 },
  { dimension: "experience_depth", label: "Experience Depth", description: "Quality of past experience", weight: 10 },
  { dimension: "confidence", label: "Confidence", description: "Self-assurance and presence", weight: 10 },
  { dimension: "vocabulary", label: "Vocabulary", description: "Language proficiency", weight: 5 },
];

const EditRoleRubric = () => {
  const { roleId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { data: orgUser } = useCurrentOrg();
  const organisation = orgUser?.organisation as { id: string } | null;

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [roleTitle, setRoleTitle] = useState("");
  const [dimensions, setDimensions] = useState<ScoringDimension[]>(DEFAULT_DIMENSIONS);
  const [originalRubric, setOriginalRubric] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    loadRole();
  }, [roleId]);

  const loadRole = async () => {
    if (!roleId) return;
    
    try {
      const data = await rolesApi.getById(roleId);

      setRoleTitle(data.title);

      // Parse existing rubric if available
      if (data.scoring_rubric) {
        const rubric = data.scoring_rubric as Record<string, { weight: number; label: string }>;
        setOriginalRubric(rubric);
        const loadedDimensions = DEFAULT_DIMENSIONS.map(dim => {
          const saved = rubric[dim.dimension];
          return {
            ...dim,
            weight: saved ? saved.weight * 100 : dim.weight,
            label: saved?.label || dim.label,
          };
        });
        setDimensions(loadedDimensions);
      }
    } catch (error) {
      console.error("Error loading role:", error);
      toast({
        title: "Error",
        description: "Failed to load role data.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getTotalWeight = () => dimensions.reduce((sum, d) => sum + d.weight, 0);

  const updateWeight = (index: number, value: number) => {
    setDimensions(prev =>
      prev.map((d, i) => (i === index ? { ...d, weight: value } : d))
    );
  };

  const resetToDefaults = () => {
    setDimensions(DEFAULT_DIMENSIONS);
  };

  const handleSave = async () => {
    const total = getTotalWeight();
    if (total !== 100) {
      toast({
        title: "Invalid Weights",
        description: `Weights must sum to 100%. Currently: ${total}%`,
        variant: "destructive",
      });
      return;
    }

    setIsSaving(true);
    try {
      const scoringRubric: Record<string, { weight: number; label: string }> = {};
      for (const dim of dimensions) {
        scoringRubric[dim.dimension] = {
          weight: dim.weight / 100,
          label: dim.label,
        };
      }

      await rolesApi.updateRubric(roleId, { scoring_rubric: scoringRubric });

      // Log audit event
      if (organisation?.id && roleId) {
        await logAuditEvent({
          action: "rubric_updated",
          entityType: "scoring_rubric",
          entityId: roleId,
          organisationId: organisation.id,
          oldValues: originalRubric || null,
          newValues: scoringRubric,
        });
      }

      toast({
        title: "Rubric Saved",
        description: "Scoring weights have been updated.",
      });
      navigate(`/org/role/${roleId}`);
    } catch (error) {
      console.error("Error saving rubric:", error);
      toast({
        title: "Error",
        description: "Failed to save scoring rubric.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const totalWeight = getTotalWeight();
  const isValid = totalWeight === 100;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border/40 bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link to={`/org/role/${roleId}`}>
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Role
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

      <div className="container mx-auto px-4 py-8 max-w-3xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Edit Scoring Rubric</h1>
          <p className="text-muted-foreground">
            Customize scoring weights for: <strong>{roleTitle}</strong>
          </p>
        </div>

        {/* Weight Summary */}
        <Card className={`p-4 mb-6 ${isValid ? "bg-green-500/10 border-green-500/20" : "bg-destructive/10 border-destructive/20"}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Scale className="w-5 h-5" />
              <span className="font-medium">Total Weight</span>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={isValid ? "default" : "destructive"}>
                {totalWeight}%
              </Badge>
              {!isValid && (
                <span className="text-sm text-destructive">Must equal 100%</span>
              )}
            </div>
          </div>
        </Card>

        {/* Dimensions */}
        <Card className="p-6 mb-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Scoring Dimensions</h2>
            <Button variant="outline" size="sm" onClick={resetToDefaults}>
              <RotateCcw className="w-4 h-4 mr-2" />
              Reset to Defaults
            </Button>
          </div>

          <div className="space-y-6">
            {dimensions.map((dim, index) => (
              <div key={dim.dimension} className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="font-medium">{dim.label}</Label>
                    <p className="text-xs text-muted-foreground">{dim.description}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      className="w-20 text-right"
                      value={dim.weight}
                      onChange={(e) => updateWeight(index, parseInt(e.target.value) || 0)}
                      min={0}
                      max={100}
                    />
                    <span className="text-sm text-muted-foreground">%</span>
                  </div>
                </div>
                <Slider
                  value={[dim.weight]}
                  onValueChange={([value]) => updateWeight(index, value)}
                  max={100}
                  step={5}
                />
              </div>
            ))}
          </div>
        </Card>

        {/* Actions */}
        <div className="flex gap-4">
          <Button
            onClick={handleSave}
            disabled={!isValid || isSaving}
            className="flex-1"
          >
            {isSaving ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Save className="w-4 h-4 mr-2" />
            )}
            Save Rubric
          </Button>
          <Button variant="outline" asChild>
            <Link to={`/org/role/${roleId}`}>Cancel</Link>
          </Button>
        </div>
      </div>
    </div>
  );
};

export default EditRoleRubric;
