import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/hooks/use-toast";
import ProfileManagement from "@/components/ProfileManagement";
import {
  User,
  FileText,
  Briefcase,
  GraduationCap,
  Wrench,
  Shield,
  Upload,
  Plus,
  Trash2,
  Edit2,
  Save,
  ArrowLeft,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
} from "lucide-react";

interface Profile {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  suburb: string;
  postcode: string;
  state: string;
  country: string;
  work_rights: string;
  availability: string;
  work_mode: string;
  gpa_wam: number | null;
  portfolio_url: string;
  linkedin_url: string;
  cv_file_path: string;
  profile_visibility: string;
}

interface Employment {
  id?: string;
  job_title: string;
  company_name: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  description: string;
}

interface Education {
  id?: string;
  institution: string;
  degree: string;
  field_of_study: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
}

interface Skill {
  id?: string;
  skill_name: string;
  skill_type: "hard" | "soft";
  proficiency_level: string;
}

const CandidateProfile = () => {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);

  const [profile, setProfile] = useState<Profile>({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    suburb: "",
    postcode: "",
    state: "",
    country: "Australia",
    work_rights: "",
    availability: "",
    work_mode: "",
    gpa_wam: null,
    portfolio_url: "",
    linkedin_url: "",
    cv_file_path: "",
    profile_visibility: "visible",
  });

  const [employmentHistory, setEmploymentHistory] = useState<Employment[]>([]);
  const [education, setEducation] = useState<Education[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);

  const [newSkill, setNewSkill] = useState("");
  const [newSkillType, setNewSkillType] = useState<"hard" | "soft">("hard");
  const [isUploadingCV, setIsUploadingCV] = useState(false);
  const [isParsingCV, setIsParsingCV] = useState(false);

  const [editingEmployment, setEditingEmployment] = useState<Employment | null>(null);
  const [editingEducation, setEditingEducation] = useState<Education | null>(null);
  const [showEmploymentDialog, setShowEmploymentDialog] = useState(false);
  const [showEducationDialog, setShowEducationDialog] = useState(false);

  // Calculate profile completion
  const calculateCompletion = useCallback(() => {
    let completed = 0;
    const total = 10;

    if (profile.first_name && profile.last_name) completed++;
    if (profile.email) completed++;
    if (profile.phone) completed++;
    if (profile.suburb && profile.state) completed++;
    if (profile.work_rights) completed++;
    if (profile.availability) completed++;
    if (profile.work_mode) completed++;
    if (profile.cv_file_path) completed++;
    if (employmentHistory.length > 0) completed++;
    if (skills.length > 0) completed++;

    return Math.round((completed / total) * 100);
  }, [profile, employmentHistory, skills]);

  const profileCompletion = calculateCompletion();

  useEffect(() => {
    checkAuthAndLoadData();
  }, []);

  const checkAuthAndLoadData = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    
    if (!session?.user) {
      navigate("/auth?type=candidate");
      return;
    }

    setUserId(session.user.id);
    await loadProfileData(session.user.id);
  };

  const loadProfileData = async (uid: string) => {
    setIsLoading(true);

    try {
      // Load profile
      const { data: profileData } = await supabase
        .from("candidate_profiles")
        .select("*")
        .eq("user_id", uid)
        .maybeSingle();

      if (profileData) {
        setProfile({
          first_name: profileData.first_name || "",
          last_name: profileData.last_name || "",
          email: profileData.email || "",
          phone: profileData.phone || "",
          suburb: profileData.suburb || "",
          postcode: profileData.postcode || "",
          state: profileData.state || "",
          country: profileData.country || "Australia",
          work_rights: profileData.work_rights || "",
          availability: profileData.availability || "",
          work_mode: profileData.work_mode || "",
          gpa_wam: profileData.gpa_wam,
          portfolio_url: profileData.portfolio_url || "",
          linkedin_url: profileData.linkedin_url || "",
          cv_file_path: profileData.cv_file_path || "",
          profile_visibility: profileData.profile_visibility || "visible",
        });
      }

      // Load employment history
      const { data: employmentData } = await supabase
        .from("employment_history")
        .select("*")
        .eq("user_id", uid)
        .order("start_date", { ascending: false });

      if (employmentData) {
        setEmploymentHistory(employmentData.map(e => ({
          id: e.id,
          job_title: e.job_title,
          company_name: e.company_name,
          start_date: e.start_date,
          end_date: e.end_date || "",
          is_current: e.is_current || false,
          description: e.description || "",
        })));
      }

      // Load education
      const { data: educationData } = await supabase
        .from("education")
        .select("*")
        .eq("user_id", uid)
        .order("start_date", { ascending: false });

      if (educationData) {
        setEducation(educationData.map(e => ({
          id: e.id,
          institution: e.institution,
          degree: e.degree,
          field_of_study: e.field_of_study || "",
          start_date: e.start_date || "",
          end_date: e.end_date || "",
          is_current: e.is_current || false,
        })));
      }

      // Load skills
      const { data: skillsData } = await supabase
        .from("candidate_skills")
        .select("*")
        .eq("user_id", uid);

      if (skillsData) {
        setSkills(skillsData.map(s => ({
          id: s.id,
          skill_name: s.skill_name,
          skill_type: s.skill_type as "hard" | "soft",
          proficiency_level: s.proficiency_level || "",
        })));
      }

    } catch (error) {
      console.error("Error loading profile:", error);
      toast({
        title: "Error",
        description: "Failed to load profile data.",
        variant: "destructive",
      });
    }

    setIsLoading(false);
  };

  const handleSaveProfile = async () => {
    if (!userId) return;

    setIsSaving(true);

    try {
      const { error } = await supabase
        .from("candidate_profiles")
        .upsert({
          user_id: userId,
          ...profile,
        }, { onConflict: "user_id" });

      if (error) throw error;

      toast({
        title: "Profile saved",
        description: "Your profile has been updated successfully.",
      });
    } catch (error) {
      console.error("Error saving profile:", error);
      toast({
        title: "Error",
        description: "Failed to save profile.",
        variant: "destructive",
      });
    }

    setIsSaving(false);
  };

  const handleCVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !userId) return;

    setIsUploadingCV(true);

    try {
      const fileExt = file.name.split(".").pop();
      const filePath = `${userId}/cv.${fileExt}`;

      const { error: uploadError } = await supabase.storage
        .from("candidate-cvs")
        .upload(filePath, file, { upsert: true });

      if (uploadError) throw uploadError;

      setProfile(prev => ({ ...prev, cv_file_path: filePath }));

      // Save the path to profile
      await supabase
        .from("candidate_profiles")
        .upsert({
          user_id: userId,
          cv_file_path: filePath,
          cv_uploaded_at: new Date().toISOString(),
        }, { onConflict: "user_id" });

      toast({
        title: "CV uploaded",
        description: "Your CV has been uploaded. Now parsing with AI...",
      });

      // Parse the resume with AI
      if (fileExt?.toLowerCase() === "pdf") {
        await parseResumeWithAI(filePath);
      }
    } catch (error) {
      console.error("Error uploading CV:", error);
      toast({
        title: "Upload failed",
        description: "Failed to upload CV. Please try again.",
        variant: "destructive",
      });
    }

    setIsUploadingCV(false);
  };

  const parseResumeWithAI = async (filePath: string) => {
    if (!userId) return;

    setIsParsingCV(true);

    try {
      const { data, error } = await supabase.functions.invoke("parse-resume", {
        body: { filePath, userId },
      });

      if (error) throw error;

      if (!data?.success || !data?.data) {
        throw new Error(data?.error || "Failed to parse resume");
      }

      const parsed = data.data;

      // Update profile with parsed personal info
      if (parsed.personal) {
        const updatedProfile = { ...profile };
        if (parsed.personal.first_name) updatedProfile.first_name = parsed.personal.first_name;
        if (parsed.personal.last_name) updatedProfile.last_name = parsed.personal.last_name;
        if (parsed.personal.email) updatedProfile.email = parsed.personal.email;
        if (parsed.personal.phone) updatedProfile.phone = parsed.personal.phone;
        if (parsed.personal.linkedin_url) updatedProfile.linkedin_url = parsed.personal.linkedin_url;
        if (parsed.personal.portfolio_url) updatedProfile.portfolio_url = parsed.personal.portfolio_url;
        if (parsed.personal.location) {
          if (parsed.personal.location.suburb) updatedProfile.suburb = parsed.personal.location.suburb;
          if (parsed.personal.location.state) updatedProfile.state = parsed.personal.location.state;
          if (parsed.personal.location.postcode) updatedProfile.postcode = parsed.personal.location.postcode;
          if (parsed.personal.location.country) updatedProfile.country = parsed.personal.location.country;
        }
        setProfile(updatedProfile);

        // Save to database
        await supabase.from("candidate_profiles").upsert({
          user_id: userId,
          ...updatedProfile,
        }, { onConflict: "user_id" });
      }

      // Add employment history
      if (parsed.employment && parsed.employment.length > 0) {
        for (const emp of parsed.employment) {
          const { data: existingEmp } = await supabase
            .from("employment_history")
            .select("id")
            .eq("user_id", userId)
            .eq("job_title", emp.job_title)
            .eq("company_name", emp.company_name)
            .maybeSingle();

          if (!existingEmp) {
            const { data: newEmp } = await supabase
              .from("employment_history")
              .insert({
                user_id: userId,
                job_title: emp.job_title,
                company_name: emp.company_name,
                start_date: emp.start_date,
                end_date: emp.end_date || null,
                is_current: emp.is_current,
                description: emp.description || "",
              })
              .select()
              .single();

            if (newEmp) {
              setEmploymentHistory(prev => [...prev, {
                id: newEmp.id,
                job_title: newEmp.job_title,
                company_name: newEmp.company_name,
                start_date: newEmp.start_date,
                end_date: newEmp.end_date || "",
                is_current: newEmp.is_current || false,
                description: newEmp.description || "",
              }]);
            }
          }
        }
      }

      // Add education
      if (parsed.education && parsed.education.length > 0) {
        for (const edu of parsed.education) {
          const { data: existingEdu } = await supabase
            .from("education")
            .select("id")
            .eq("user_id", userId)
            .eq("institution", edu.institution)
            .eq("degree", edu.degree)
            .maybeSingle();

          if (!existingEdu) {
            const { data: newEdu } = await supabase
              .from("education")
              .insert({
                user_id: userId,
                institution: edu.institution,
                degree: edu.degree,
                field_of_study: edu.field_of_study || null,
                start_date: edu.start_date || null,
                end_date: edu.end_date || null,
                is_current: edu.is_current || false,
              })
              .select()
              .single();

            if (newEdu) {
              setEducation(prev => [...prev, {
                id: newEdu.id,
                institution: newEdu.institution,
                degree: newEdu.degree,
                field_of_study: newEdu.field_of_study || "",
                start_date: newEdu.start_date || "",
                end_date: newEdu.end_date || "",
                is_current: newEdu.is_current || false,
              }]);
            }
          }
        }
      }

      // Add skills
      if (parsed.skills && parsed.skills.length > 0) {
        for (const skill of parsed.skills) {
          const { data: existingSkill } = await supabase
            .from("candidate_skills")
            .select("id")
            .eq("user_id", userId)
            .eq("skill_name", skill.skill_name)
            .maybeSingle();

          if (!existingSkill) {
            const { data: newSkillData } = await supabase
              .from("candidate_skills")
              .insert({
                user_id: userId,
                skill_name: skill.skill_name,
                skill_type: skill.skill_type,
              })
              .select()
              .single();

            if (newSkillData) {
              setSkills(prev => [...prev, {
                id: newSkillData.id,
                skill_name: newSkillData.skill_name,
                skill_type: newSkillData.skill_type as "hard" | "soft",
                proficiency_level: "",
              }]);
            }
          }
        }
      }

      toast({
        title: "Resume parsed successfully",
        description: "Your profile has been updated with information from your resume.",
      });
    } catch (error) {
      console.error("Error parsing resume:", error);
      toast({
        title: "Parsing notice",
        description: "CV uploaded but could not extract all details. You can fill them in manually.",
        variant: "default",
      });
    }

    setIsParsingCV(false);
  };

  const handleAddSkill = async () => {
    if (!newSkill.trim() || !userId) return;

    try {
      const { data, error } = await supabase
        .from("candidate_skills")
        .insert({
          user_id: userId,
          skill_name: newSkill.trim(),
          skill_type: newSkillType,
        })
        .select()
        .single();

      if (error) throw error;

      setSkills(prev => [...prev, {
        id: data.id,
        skill_name: data.skill_name,
        skill_type: data.skill_type as "hard" | "soft",
        proficiency_level: data.proficiency_level || "",
      }]);

      setNewSkill("");
    } catch (error) {
      console.error("Error adding skill:", error);
      toast({
        title: "Error",
        description: "Failed to add skill.",
        variant: "destructive",
      });
    }
  };

  const handleRemoveSkill = async (skillId: string) => {
    try {
      const { error } = await supabase
        .from("candidate_skills")
        .delete()
        .eq("id", skillId);

      if (error) throw error;

      setSkills(prev => prev.filter(s => s.id !== skillId));
    } catch (error) {
      console.error("Error removing skill:", error);
    }
  };

  const handleSaveEmployment = async (employment: Employment) => {
    if (!userId) return;

    try {
      if (employment.id) {
        // Update existing
        const { error } = await supabase
          .from("employment_history")
          .update({
            job_title: employment.job_title,
            company_name: employment.company_name,
            start_date: employment.start_date,
            end_date: employment.end_date || null,
            is_current: employment.is_current,
            description: employment.description,
          })
          .eq("id", employment.id);

        if (error) throw error;

        setEmploymentHistory(prev =>
          prev.map(e => e.id === employment.id ? employment : e)
        );
      } else {
        // Create new
        const { data, error } = await supabase
          .from("employment_history")
          .insert({
            user_id: userId,
            job_title: employment.job_title,
            company_name: employment.company_name,
            start_date: employment.start_date,
            end_date: employment.end_date || null,
            is_current: employment.is_current,
            description: employment.description,
          })
          .select()
          .single();

        if (error) throw error;

        setEmploymentHistory(prev => [{ ...employment, id: data.id }, ...prev]);
      }

      setShowEmploymentDialog(false);
      setEditingEmployment(null);
    } catch (error) {
      console.error("Error saving employment:", error);
      toast({
        title: "Error",
        description: "Failed to save employment history.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteEmployment = async (id: string) => {
    try {
      const { error } = await supabase
        .from("employment_history")
        .delete()
        .eq("id", id);

      if (error) throw error;

      setEmploymentHistory(prev => prev.filter(e => e.id !== id));
    } catch (error) {
      console.error("Error deleting employment:", error);
    }
  };

  const handleSaveEducation = async (edu: Education) => {
    if (!userId) return;

    try {
      if (edu.id) {
        const { error } = await supabase
          .from("education")
          .update({
            institution: edu.institution,
            degree: edu.degree,
            field_of_study: edu.field_of_study,
            start_date: edu.start_date || null,
            end_date: edu.end_date || null,
            is_current: edu.is_current,
          })
          .eq("id", edu.id);

        if (error) throw error;

        setEducation(prev => prev.map(e => e.id === edu.id ? edu : e));
      } else {
        const { data, error } = await supabase
          .from("education")
          .insert({
            user_id: userId,
            institution: edu.institution,
            degree: edu.degree,
            field_of_study: edu.field_of_study,
            start_date: edu.start_date || null,
            end_date: edu.end_date || null,
            is_current: edu.is_current,
          })
          .select()
          .single();

        if (error) throw error;

        setEducation(prev => [{ ...edu, id: data.id }, ...prev]);
      }

      setShowEducationDialog(false);
      setEditingEducation(null);
    } catch (error) {
      console.error("Error saving education:", error);
      toast({
        title: "Error",
        description: "Failed to save education.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteEducation = async (id: string) => {
    try {
      const { error } = await supabase
        .from("education")
        .delete()
        .eq("id", id);

      if (error) throw error;

      setEducation(prev => prev.filter(e => e.id !== id));
    } catch (error) {
      console.error("Error deleting education:", error);
    }
  };

  if (isLoading) {
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
            <Button variant="ghost" size="icon" onClick={() => navigate("/candidate/portal")}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-xl font-bold">Edit Profile</h1>
              <p className="text-sm text-muted-foreground">Manage your candidate profile</p>
            </div>
          </div>
          <Button onClick={handleSaveProfile} disabled={isSaving}>
            {isSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
            Save Changes
          </Button>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 max-w-5xl">
        {/* Profile Completion Card */}
        <Card className="p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-semibold">Profile Completion</h2>
              <p className="text-sm text-muted-foreground">Complete your profile to increase visibility</p>
            </div>
            <span className="text-3xl font-bold text-primary">{profileCompletion}%</span>
          </div>
          <Progress value={profileCompletion} className="h-3" />
        </Card>

        <Tabs defaultValue="personal" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="personal" className="flex items-center gap-2">
              <User className="w-4 h-4" />
              <span className="hidden sm:inline">Personal</span>
            </TabsTrigger>
            <TabsTrigger value="cv" className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              <span className="hidden sm:inline">CV</span>
            </TabsTrigger>
            <TabsTrigger value="experience" className="flex items-center gap-2">
              <Briefcase className="w-4 h-4" />
              <span className="hidden sm:inline">Experience</span>
            </TabsTrigger>
            <TabsTrigger value="skills" className="flex items-center gap-2">
              <Wrench className="w-4 h-4" />
              <span className="hidden sm:inline">Skills</span>
            </TabsTrigger>
            <TabsTrigger value="privacy" className="flex items-center gap-2">
              <Shield className="w-4 h-4" />
              <span className="hidden sm:inline">Privacy</span>
            </TabsTrigger>
          </TabsList>

          {/* Personal Info Tab */}
          <TabsContent value="personal">
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-6">Personal Information</h2>
              
              <div className="grid md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="firstName">First Name</Label>
                  <Input
                    id="firstName"
                    value={profile.first_name}
                    onChange={(e) => setProfile(p => ({ ...p, first_name: e.target.value }))}
                    placeholder="John"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last Name</Label>
                  <Input
                    id="lastName"
                    value={profile.last_name}
                    onChange={(e) => setProfile(p => ({ ...p, last_name: e.target.value }))}
                    placeholder="Doe"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={profile.email}
                    onChange={(e) => setProfile(p => ({ ...p, email: e.target.value }))}
                    placeholder="john@example.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">Phone</Label>
                  <Input
                    id="phone"
                    value={profile.phone}
                    onChange={(e) => setProfile(p => ({ ...p, phone: e.target.value }))}
                    placeholder="+61 400 000 000"
                  />
                </div>
              </div>

              <Separator className="my-6" />

              <h3 className="font-semibold mb-4">Location</h3>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="suburb">Suburb</Label>
                  <Input
                    id="suburb"
                    value={profile.suburb}
                    onChange={(e) => setProfile(p => ({ ...p, suburb: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="postcode">Postcode</Label>
                  <Input
                    id="postcode"
                    value={profile.postcode}
                    onChange={(e) => setProfile(p => ({ ...p, postcode: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="state">State</Label>
                  <Select
                    value={profile.state}
                    onValueChange={(v) => setProfile(p => ({ ...p, state: v }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select state" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="NSW">NSW</SelectItem>
                      <SelectItem value="VIC">VIC</SelectItem>
                      <SelectItem value="QLD">QLD</SelectItem>
                      <SelectItem value="WA">WA</SelectItem>
                      <SelectItem value="SA">SA</SelectItem>
                      <SelectItem value="TAS">TAS</SelectItem>
                      <SelectItem value="ACT">ACT</SelectItem>
                      <SelectItem value="NT">NT</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Separator className="my-6" />

              <h3 className="font-semibold mb-4">Work Preferences</h3>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Work Rights</Label>
                  <Select
                    value={profile.work_rights}
                    onValueChange={(v) => setProfile(p => ({ ...p, work_rights: v }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="citizen">Citizen</SelectItem>
                      <SelectItem value="permanent_resident">Permanent Resident</SelectItem>
                      <SelectItem value="work_visa">Work Visa</SelectItem>
                      <SelectItem value="student_visa">Student Visa</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Availability</Label>
                  <Select
                    value={profile.availability}
                    onValueChange={(v) => setProfile(p => ({ ...p, availability: v }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="immediate">Immediate</SelectItem>
                      <SelectItem value="2_weeks">2 Weeks</SelectItem>
                      <SelectItem value="1_month">1 Month</SelectItem>
                      <SelectItem value="negotiable">Negotiable</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Work Mode</Label>
                  <Select
                    value={profile.work_mode}
                    onValueChange={(v) => setProfile(p => ({ ...p, work_mode: v }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="onsite">Onsite</SelectItem>
                      <SelectItem value="hybrid">Hybrid</SelectItem>
                      <SelectItem value="remote">Remote</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Separator className="my-6" />

              <h3 className="font-semibold mb-4">Links</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="linkedin">LinkedIn URL</Label>
                  <Input
                    id="linkedin"
                    value={profile.linkedin_url}
                    onChange={(e) => setProfile(p => ({ ...p, linkedin_url: e.target.value }))}
                    placeholder="https://linkedin.com/in/..."
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="portfolio">Portfolio URL</Label>
                  <Input
                    id="portfolio"
                    value={profile.portfolio_url}
                    onChange={(e) => setProfile(p => ({ ...p, portfolio_url: e.target.value }))}
                    placeholder="https://..."
                  />
                </div>
              </div>
            </Card>
          </TabsContent>

          {/* CV Upload Tab */}
          <TabsContent value="cv">
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-2">CV / Resume</h2>
              <p className="text-muted-foreground mb-6">
                Upload your CV to help employers understand your qualifications
              </p>

              <div className="border-2 border-dashed border-border rounded-lg p-8 text-center">
                {profile.cv_file_path ? (
                  <div className="space-y-4">
                    <div className="w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center mx-auto">
                      <CheckCircle2 className="w-8 h-8 text-green-500" />
                    </div>
                    <div>
                      <p className="font-semibold">CV Uploaded</p>
                      <p className="text-sm text-muted-foreground">{profile.cv_file_path.split("/").pop()}</p>
                    </div>
                    <div className="flex gap-4 justify-center">
                      <label htmlFor="cv-upload-replace" className="cursor-pointer">
                        <Button variant="outline" asChild>
                          <span>
                            <Upload className="w-4 h-4 mr-2" />
                            Replace CV
                          </span>
                        </Button>
                        <input
                          type="file"
                          id="cv-upload-replace"
                          accept=".pdf,.doc,.docx"
                          className="hidden"
                          onChange={handleCVUpload}
                        />
                      </label>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="w-16 h-16 rounded-full bg-accent flex items-center justify-center mx-auto">
                      <FileText className="w-8 h-8 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="font-semibold">Upload your CV</p>
                      <p className="text-sm text-muted-foreground">PDF, DOC, or DOCX (max 10MB)</p>
                    </div>
                    <label htmlFor="cv-upload" className="cursor-pointer">
                      <Button disabled={isUploadingCV} asChild>
                        <span>
                          {isUploadingCV ? (
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          ) : (
                            <Upload className="w-4 h-4 mr-2" />
                          )}
                          {isUploadingCV ? "Uploading..." : "Choose File"}
                        </span>
                      </Button>
                      <input
                        type="file"
                        id="cv-upload"
                        accept=".pdf,.doc,.docx"
                        className="hidden"
                        onChange={handleCVUpload}
                      />
                    </label>
                  </div>
                )}
              </div>
            </Card>
          </TabsContent>

          {/* Experience Tab */}
          <TabsContent value="experience">
            <div className="space-y-6">
              {/* Employment History */}
              <Card className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-xl font-semibold">Employment History</h2>
                    <p className="text-sm text-muted-foreground">Add your work experience</p>
                  </div>
                  <Button
                    onClick={() => {
                      setEditingEmployment({
                        job_title: "",
                        company_name: "",
                        start_date: "",
                        end_date: "",
                        is_current: false,
                        description: "",
                      });
                      setShowEmploymentDialog(true);
                    }}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Add Experience
                  </Button>
                </div>

                {employmentHistory.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Briefcase className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No employment history added yet</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {employmentHistory.map((emp) => (
                      <div key={emp.id} className="flex items-start justify-between p-4 rounded-lg border border-border">
                        <div>
                          <h3 className="font-semibold">{emp.job_title}</h3>
                          <p className="text-muted-foreground">{emp.company_name}</p>
                          <p className="text-sm text-muted-foreground">
                            {emp.start_date} - {emp.is_current ? "Present" : emp.end_date}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => {
                              setEditingEmployment(emp);
                              setShowEmploymentDialog(true);
                            }}
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => emp.id && handleDeleteEmployment(emp.id)}
                          >
                            <Trash2 className="w-4 h-4 text-destructive" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              {/* Education */}
              <Card className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-xl font-semibold">Education</h2>
                    <p className="text-sm text-muted-foreground">Add your educational background</p>
                  </div>
                  <Button
                    onClick={() => {
                      setEditingEducation({
                        institution: "",
                        degree: "",
                        field_of_study: "",
                        start_date: "",
                        end_date: "",
                        is_current: false,
                      });
                      setShowEducationDialog(true);
                    }}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Add Education
                  </Button>
                </div>

                {education.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <GraduationCap className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No education added yet</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {education.map((edu) => (
                      <div key={edu.id} className="flex items-start justify-between p-4 rounded-lg border border-border">
                        <div>
                          <h3 className="font-semibold">{edu.degree}</h3>
                          <p className="text-muted-foreground">{edu.institution}</p>
                          {edu.field_of_study && (
                            <p className="text-sm text-muted-foreground">{edu.field_of_study}</p>
                          )}
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => {
                              setEditingEducation(edu);
                              setShowEducationDialog(true);
                            }}
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => edu.id && handleDeleteEducation(edu.id)}
                          >
                            <Trash2 className="w-4 h-4 text-destructive" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          </TabsContent>

          {/* Skills Tab */}
          <TabsContent value="skills">
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-2">Skills</h2>
              <p className="text-muted-foreground mb-6">Add your technical and soft skills</p>

              <div className="flex gap-4 mb-6">
                <div className="flex-1">
                  <Input
                    value={newSkill}
                    onChange={(e) => setNewSkill(e.target.value)}
                    placeholder="Enter a skill..."
                    onKeyDown={(e) => e.key === "Enter" && handleAddSkill()}
                  />
                </div>
                <Select
                  value={newSkillType}
                  onValueChange={(v) => setNewSkillType(v as "hard" | "soft")}
                >
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="hard">Hard Skill</SelectItem>
                    <SelectItem value="soft">Soft Skill</SelectItem>
                  </SelectContent>
                </Select>
                <Button onClick={handleAddSkill}>
                  <Plus className="w-4 h-4" />
                </Button>
              </div>

              <div className="space-y-4">
                <div>
                  <h3 className="font-medium mb-3 flex items-center gap-2">
                    <Wrench className="w-4 h-4" />
                    Hard Skills
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {skills.filter(s => s.skill_type === "hard").map((skill) => (
                      <Badge key={skill.id} variant="secondary" className="flex items-center gap-1 pl-3">
                        {skill.skill_name}
                        <button
                          onClick={() => skill.id && handleRemoveSkill(skill.id)}
                          className="ml-1 hover:text-destructive"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </Badge>
                    ))}
                    {skills.filter(s => s.skill_type === "hard").length === 0 && (
                      <span className="text-sm text-muted-foreground">No hard skills added</span>
                    )}
                  </div>
                </div>

                <Separator />

                <div>
                  <h3 className="font-medium mb-3 flex items-center gap-2">
                    <User className="w-4 h-4" />
                    Soft Skills
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {skills.filter(s => s.skill_type === "soft").map((skill) => (
                      <Badge key={skill.id} variant="outline" className="flex items-center gap-1 pl-3">
                        {skill.skill_name}
                        <button
                          onClick={() => skill.id && handleRemoveSkill(skill.id)}
                          className="ml-1 hover:text-destructive"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </Badge>
                    ))}
                    {skills.filter(s => s.skill_type === "soft").length === 0 && (
                      <span className="text-sm text-muted-foreground">No soft skills added</span>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>

          {/* Privacy Tab */}
          <TabsContent value="privacy">
            {userId && <ProfileManagement userId={userId} />}
          </TabsContent>
        </Tabs>
      </div>

      {/* Employment Dialog */}
      <Dialog open={showEmploymentDialog} onOpenChange={setShowEmploymentDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingEmployment?.id ? "Edit" : "Add"} Employment</DialogTitle>
          </DialogHeader>
          {editingEmployment && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Job Title</Label>
                <Input
                  value={editingEmployment.job_title}
                  onChange={(e) => setEditingEmployment(prev => prev ? { ...prev, job_title: e.target.value } : null)}
                />
              </div>
              <div className="space-y-2">
                <Label>Company</Label>
                <Input
                  value={editingEmployment.company_name}
                  onChange={(e) => setEditingEmployment(prev => prev ? { ...prev, company_name: e.target.value } : null)}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Start Date</Label>
                  <Input
                    type="date"
                    value={editingEmployment.start_date}
                    onChange={(e) => setEditingEmployment(prev => prev ? { ...prev, start_date: e.target.value } : null)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>End Date</Label>
                  <Input
                    type="date"
                    value={editingEmployment.end_date}
                    disabled={editingEmployment.is_current}
                    onChange={(e) => setEditingEmployment(prev => prev ? { ...prev, end_date: e.target.value } : null)}
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={editingEmployment.is_current}
                  onCheckedChange={(checked) => setEditingEmployment(prev => prev ? { ...prev, is_current: checked, end_date: "" } : null)}
                />
                <Label>I currently work here</Label>
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea
                  value={editingEmployment.description}
                  onChange={(e) => setEditingEmployment(prev => prev ? { ...prev, description: e.target.value } : null)}
                  placeholder="Describe your responsibilities..."
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEmploymentDialog(false)}>Cancel</Button>
            <Button onClick={() => editingEmployment && handleSaveEmployment(editingEmployment)}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Education Dialog */}
      <Dialog open={showEducationDialog} onOpenChange={setShowEducationDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingEducation?.id ? "Edit" : "Add"} Education</DialogTitle>
          </DialogHeader>
          {editingEducation && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Institution</Label>
                <Input
                  value={editingEducation.institution}
                  onChange={(e) => setEditingEducation(prev => prev ? { ...prev, institution: e.target.value } : null)}
                />
              </div>
              <div className="space-y-2">
                <Label>Degree</Label>
                <Input
                  value={editingEducation.degree}
                  onChange={(e) => setEditingEducation(prev => prev ? { ...prev, degree: e.target.value } : null)}
                  placeholder="e.g., Bachelor of Science"
                />
              </div>
              <div className="space-y-2">
                <Label>Field of Study</Label>
                <Input
                  value={editingEducation.field_of_study}
                  onChange={(e) => setEditingEducation(prev => prev ? { ...prev, field_of_study: e.target.value } : null)}
                  placeholder="e.g., Computer Science"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Start Date</Label>
                  <Input
                    type="date"
                    value={editingEducation.start_date}
                    onChange={(e) => setEditingEducation(prev => prev ? { ...prev, start_date: e.target.value } : null)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>End Date</Label>
                  <Input
                    type="date"
                    value={editingEducation.end_date}
                    disabled={editingEducation.is_current}
                    onChange={(e) => setEditingEducation(prev => prev ? { ...prev, end_date: e.target.value } : null)}
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={editingEducation.is_current}
                  onCheckedChange={(checked) => setEditingEducation(prev => prev ? { ...prev, is_current: checked, end_date: "" } : null)}
                />
                <Label>Currently studying</Label>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEducationDialog(false)}>Cancel</Button>
            <Button onClick={() => editingEducation && handleSaveEducation(editingEducation)}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CandidateProfile;