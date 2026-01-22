import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Upload, Sparkles, Loader2, X, Check } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { supabase } from "@/integrations/supabase/client";
import { useCurrentOrg } from "@/hooks/useOrgData";
import type { Json } from "@/integrations/supabase/types";

interface ExtractedRequirements {
  skills: string[];
  experience: string[];
  qualifications: string[];
  responsibilities: string[];
  interviewQuestions: string[];
}

interface ScoringWeight {
  dimension: string;
  label: string;
  description: string;
  weight: number;
}

const NewRole = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { data: orgData, isLoading: orgLoading } = useCurrentOrg();
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractedRequirements, setExtractedRequirements] = useState<ExtractedRequirements | null>(null);
  
  // Form state
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [workType, setWorkType] = useState("");
  const [location, setLocation] = useState("");
  const [salaryMin, setSalaryMin] = useState("");
  const [salaryMax, setSalaryMax] = useState("");
  const [description, setDescription] = useState("");
  
  const [scoringWeights, setScoringWeights] = useState<ScoringWeight[]>([
    { dimension: "technical_skills", label: "Technical Skills", description: "Relevant experience and expertise", weight: 30 },
    { dimension: "culture_fit", label: "Culture Fit", description: "Alignment with company values", weight: 25 },
    { dimension: "motivation", label: "Motivation & Passion", description: "Enthusiasm for the role", weight: 20 },
    { dimension: "communication", label: "Communication", description: "Clarity and articulation", weight: 15 },
    { dimension: "salary_alignment", label: "Salary Alignment", description: "Expectations match budget", weight: 10 },
  ]);

  const handleExtractRequirements = async () => {
    if (!description.trim()) {
      toast({
        title: "Description Required",
        description: "Please enter a job description to extract requirements.",
        variant: "destructive",
      });
      return;
    }

    setIsExtracting(true);
    try {
      const { data, error } = await supabase.functions.invoke("extract-requirements", {
        body: { jobDescription: description, jobTitle: title },
      });

      if (error) throw error;
      
      if (data.requirements) {
        setExtractedRequirements(data.requirements);
        toast({
          title: "Requirements Extracted",
          description: "AI has analyzed your job description and extracted key requirements.",
        });
      }
    } catch (error: any) {
      console.error("Extraction error:", error);
      toast({
        title: "Extraction Failed",
        description: error.message || "Failed to extract requirements. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsExtracting(false);
    }
  };

  const updateWeight = (index: number, value: number) => {
    setScoringWeights(prev => 
      prev.map((w, i) => i === index ? { ...w, weight: value } : w)
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!orgData?.organisation) {
      toast({
        title: "No Organisation",
        description: "Please set up your organisation first.",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    
    try {
      // Build requirements JSON - cast to plain object for Json type compatibility
      const requirementsJson = JSON.parse(JSON.stringify(extractedRequirements || {
        skills: [],
        experience: [],
        qualifications: [],
        responsibilities: [],
        interviewQuestions: [],
      }));

      // Build scoring rubric JSON
      const scoringRubricJson = scoringWeights.reduce((acc, w) => {
        acc[w.dimension] = { weight: w.weight / 100, label: w.label };
        return acc;
      }, {} as Record<string, { weight: number; label: string }>);

      const { data: { user } } = await supabase.auth.getUser();
      
      const roleData: {
        organisation_id: string;
        created_by: string | null;
        title: string;
        department: string | null;
        work_type: string | null;
        location: string | null;
        salary_range_min: number | null;
        salary_range_max: number | null;
        description: string | null;
        requirements: Json;
        scoring_rubric: Json;
        interview_structure: Json;
        status: "active" | "closed" | "draft";
      } = {
        organisation_id: orgData.organisation.id,
        created_by: user?.id || null,
        title,
        department: department || null,
        work_type: workType || null,
        location: location || null,
        salary_range_min: salaryMin ? parseInt(salaryMin) : null,
        salary_range_max: salaryMax ? parseInt(salaryMax) : null,
        description: description || null,
        requirements: requirementsJson,
        scoring_rubric: scoringRubricJson,
        interview_structure: {
          questions: extractedRequirements?.interviewQuestions || [],
          duration_minutes: 15,
        } as Json,
        status: "active",
      };

      const { data: role, error } = await supabase
        .from("job_roles")
        .insert(roleData)
        .select()
        .single();

      if (error) throw error;

      toast({
        title: "Role Created!",
        description: "You can now upload candidate resumes and send interview invitations.",
      });
      
      navigate(`/org/role/${role.id}`);
    } catch (error: any) {
      console.error("Create role error:", error);
      toast({
        title: "Failed to Create Role",
        description: error.message || "An error occurred while creating the role.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (orgLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
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

      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Create New Role</h1>
          <p className="text-muted-foreground">Set up a new position and define screening criteria</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">Role Details</h2>
            
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="title">Job Title *</Label>
                  <Input 
                    id="title" 
                    placeholder="e.g., Senior Frontend Developer" 
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required 
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="department">Department</Label>
                  <Select value={department} onValueChange={setDepartment}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select department" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="engineering">Engineering</SelectItem>
                      <SelectItem value="product">Product</SelectItem>
                      <SelectItem value="design">Design</SelectItem>
                      <SelectItem value="marketing">Marketing</SelectItem>
                      <SelectItem value="sales">Sales</SelectItem>
                      <SelectItem value="operations">Operations</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="workType">Work Type</Label>
                  <Select value={workType} onValueChange={setWorkType}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select work type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="remote">Remote</SelectItem>
                      <SelectItem value="hybrid">Hybrid</SelectItem>
                      <SelectItem value="onsite">On-site</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="location">Location</Label>
                  <Input 
                    id="location" 
                    placeholder="e.g., Sydney, Australia"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="salaryMin">Salary Range (Min)</Label>
                  <Input 
                    id="salaryMin" 
                    type="number" 
                    placeholder="e.g., 100000"
                    value={salaryMin}
                    onChange={(e) => setSalaryMin(e.target.value)}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="salaryMax">Salary Range (Max)</Label>
                  <Input 
                    id="salaryMax" 
                    type="number" 
                    placeholder="e.g., 150000"
                    value={salaryMax}
                    onChange={(e) => setSalaryMax(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="description">Job Description *</Label>
                  <Button 
                    type="button" 
                    variant="outline" 
                    size="sm"
                    onClick={handleExtractRequirements}
                    disabled={isExtracting || !description.trim()}
                  >
                    {isExtracting ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Extracting...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4 mr-2" />
                        Extract with AI
                      </>
                    )}
                  </Button>
                </div>
                <Textarea 
                  id="description" 
                  rows={8}
                  placeholder="Describe the role, responsibilities, and requirements..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="jobDescFile">Or Upload Job Description</Label>
                <div className="flex items-center gap-4">
                  <Button type="button" variant="outline" className="w-full">
                    <Upload className="w-4 h-4 mr-2" />
                    Upload PDF or DOCX
                  </Button>
                </div>
              </div>
            </div>
          </Card>

          {/* AI Extracted Requirements */}
          {extractedRequirements && (
            <Card className="p-6 border-primary/20 bg-primary/5">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-5 h-5 text-primary" />
                <h2 className="text-xl font-semibold">AI-Extracted Requirements</h2>
                <Button 
                  type="button" 
                  variant="ghost" 
                  size="sm" 
                  className="ml-auto"
                  onClick={() => setExtractedRequirements(null)}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
              
              <div className="space-y-4">
                {extractedRequirements.skills.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Skills</p>
                    <div className="flex flex-wrap gap-2">
                      {extractedRequirements.skills.map((skill, i) => (
                        <Badge key={i} variant="secondary">{skill}</Badge>
                      ))}
                    </div>
                  </div>
                )}

                {extractedRequirements.experience.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Experience</p>
                    <ul className="text-sm text-muted-foreground space-y-1">
                      {extractedRequirements.experience.map((exp, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <Check className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                          {exp}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {extractedRequirements.responsibilities.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Key Responsibilities</p>
                    <ul className="text-sm text-muted-foreground space-y-1">
                      {extractedRequirements.responsibilities.slice(0, 5).map((resp, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <Check className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                          {resp}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {extractedRequirements.interviewQuestions.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Suggested Interview Questions</p>
                    <ol className="text-sm text-muted-foreground space-y-1 list-decimal list-inside">
                      {extractedRequirements.interviewQuestions.map((q, i) => (
                        <li key={i}>{q}</li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            </Card>
          )}

          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">Screening Criteria</h2>
            <p className="text-sm text-muted-foreground mb-4">
              Customize how candidates will be evaluated (you can adjust weightings later)
            </p>
            
            <div className="space-y-4">
              {scoringWeights.map((weight, index) => (
                <div key={weight.dimension} className="flex items-center justify-between p-3 rounded-lg border border-border">
                  <div>
                    <p className="font-medium">{weight.label}</p>
                    <p className="text-sm text-muted-foreground">{weight.description}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input 
                      type="number" 
                      className="w-20" 
                      value={weight.weight}
                      onChange={(e) => updateWeight(index, parseInt(e.target.value) || 0)}
                      min="0" 
                      max="100" 
                    />
                    <span className="text-sm text-muted-foreground">%</span>
                  </div>
                </div>
              ))}
              
              <div className="text-sm text-muted-foreground text-right">
                Total: {scoringWeights.reduce((sum, w) => sum + w.weight, 0)}%
                {scoringWeights.reduce((sum, w) => sum + w.weight, 0) !== 100 && (
                  <span className="text-destructive ml-2">(should equal 100%)</span>
                )}
              </div>
            </div>
          </Card>

          <div className="flex gap-4">
            <Button type="button" variant="outline" className="flex-1" asChild>
              <Link to="/org">Cancel</Link>
            </Button>
            <Button type="submit" className="flex-1" disabled={isSubmitting || !title.trim()}>
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                "Create Role"
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default NewRole;
