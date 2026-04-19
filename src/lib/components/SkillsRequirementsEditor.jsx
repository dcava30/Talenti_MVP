import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { X, Plus, RefreshCw, Save } from "lucide-react";

const SkillsRequirementsEditor = ({ jobProfile, onUpdate, onReparse, onSave, isReparsing = false }) => {
  const [expectations, setExpectations] = useState(jobProfile?.expectations || []);

  const updateExpectation = (index, field, value) => {
    const updated = expectations.map((exp, i) =>
      i === index ? { ...exp, [field]: value } : exp
    );
    setExpectations(updated);
    onUpdate?.({ ...jobProfile, expectations: updated });
  };

  const removeExpectation = (index) => {
    const updated = expectations.filter((_, i) => i !== index);
    setExpectations(updated);
    onUpdate?.({ ...jobProfile, expectations: updated });
  };

  const addExpectation = () => {
    const newExp = {
      competency: "",
      level: "nice",
      min_years: 0,
      keywords: [],
      threshold: 0.60,
    };
    const updated = [...expectations, newExp];
    setExpectations(updated);
    onUpdate?.({ ...jobProfile, expectations: updated });
  };

  // Sync when parent updates jobProfile (e.g. after re-parse)
  if (jobProfile?.expectations && jobProfile.expectations !== expectations && jobProfile.expectations.length !== expectations.length) {
    setExpectations(jobProfile.expectations);
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold">Skills Requirements</h2>
          <p className="text-sm text-muted-foreground">
            {jobProfile?.role_title || "Role"} — {jobProfile?.seniority || "mid"} level
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {expectations.map((exp, index) => (
          <div
            key={`${exp.competency}-${index}`}
            className="p-4 rounded-lg border border-border space-y-3"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Input
                  className="w-48 font-medium"
                  value={exp.competency}
                  onChange={(e) => updateExpectation(index, "competency", e.target.value)}
                  placeholder="Competency name"
                />
                <Select
                  value={exp.level}
                  onValueChange={(val) => updateExpectation(index, "level", val)}
                >
                  <SelectTrigger className="w-28">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="must">Must-have</SelectItem>
                    <SelectItem value="nice">Nice-to-have</SelectItem>
                  </SelectContent>
                </Select>
                <Badge variant={exp.level === "must" ? "destructive" : "secondary"}>
                  {exp.level === "must" ? "Required" : "Preferred"}
                </Badge>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => removeExpectation(index)}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Min. Years</Label>
                <Input
                  type="number"
                  min="0"
                  step="0.5"
                  value={exp.min_years}
                  onChange={(e) =>
                    updateExpectation(index, "min_years", parseFloat(e.target.value) || 0)
                  }
                  className="w-24"
                />
              </div>

              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">
                  Threshold: {Math.round((exp.threshold || 0.65) * 100)}%
                </Label>
                <Slider
                  value={[Math.round((exp.threshold || 0.65) * 100)]}
                  onValueChange={([val]) =>
                    updateExpectation(index, "threshold", val / 100)
                  }
                  min={50}
                  max={100}
                  step={5}
                  className="w-full"
                />
              </div>

              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Keywords</Label>
                <div className="flex flex-wrap gap-1">
                  {(exp.keywords || []).slice(0, 6).map((kw, ki) => (
                    <Badge key={ki} variant="outline" className="text-xs">
                      {kw}
                    </Badge>
                  ))}
                  {(exp.keywords || []).length > 6 && (
                    <Badge variant="outline" className="text-xs">
                      +{exp.keywords.length - 6}
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-3 mt-4">
        <Button type="button" variant="outline" size="sm" onClick={addExpectation}>
          <Plus className="w-4 h-4 mr-1" />
          Add Competency
        </Button>
        {onReparse && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onReparse}
            disabled={isReparsing}
          >
            <RefreshCw className={`w-4 h-4 mr-1 ${isReparsing ? "animate-spin" : ""}`} />
            Re-parse from JD
          </Button>
        )}
        {onSave && (
          <Button type="button" size="sm" onClick={() => onSave({ ...jobProfile, expectations })}>
            <Save className="w-4 h-4 mr-1" />
            Save
          </Button>
        )}
      </div>
    </Card>
  );
};

export default SkillsRequirementsEditor;
