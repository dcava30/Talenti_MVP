import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/hooks/use-toast";
import { Building2, Globe, Mail, Loader2, CheckCircle2, ArrowRight } from "lucide-react";

const OrgOnboarding = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [step, setStep] = useState(1);
  
  // Form state
  const [orgName, setOrgName] = useState("");
  const [industry, setIndustry] = useState("");
  const [website, setWebsite] = useState("");
  const [description, setDescription] = useState("");
  const [billingEmail, setBillingEmail] = useState("");

  useEffect(() => {
    checkExistingOrg();
  }, []);

  const checkExistingOrg = async () => {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    const user = session?.user;

    if (!user) {
      navigate("/auth?type=organisation");
      return;
    }

    // Check if user already belongs to an org
    const { data: orgUser, error: orgUserError } = await supabase
      .from("org_users")
      .select("organisation_id")
      .eq("user_id", user.id)
      .maybeSingle();

    if (orgUserError) {
      console.error("[OrgOnboarding] org_users lookup failed:", {
        message: orgUserError.message,
        code: (orgUserError as any).code,
        details: (orgUserError as any).details,
        hint: (orgUserError as any).hint,
      });
    }

    if (orgUser?.organisation_id) {
      // User already has an org, redirect to dashboard
      navigate("/org");
      return;
    }

    // Pre-fill billing email
    setBillingEmail(user.email || "");
    setIsLoading(false);
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!orgName.trim()) {
      toast({
        title: "Organisation Name Required",
        description: "Please enter your organisation name.",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);

    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session?.user) throw new Error("Not authenticated");

      // Verify token is valid and ensure the client has an in-memory session
      const { data: userRes, error: userErr } = await supabase.auth.getUser();
      if (userErr || !userRes?.user) {
        throw new Error(userErr?.message || "Not authenticated");
      }

      try {
        await supabase.auth.setSession({
          access_token: session.access_token,
          refresh_token: session.refresh_token,
        });
      } catch {
        // ignore
      }

      const user = userRes.user;
      // Create organisation via backend function (avoids client-side RLS edge cases)
      const { data, error: fnError } = await supabase.functions.invoke("create-organisation", {
        body: {
          name: orgName,
          industry: industry || null,
          website: website || null,
          description: description || null,
          billing_email: billingEmail || null,
        },
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      if (fnError) throw fnError;

      const org = (data as any)?.organisation;
      if (!org?.id) throw new Error("Organisation creation failed");

      toast({
        title: "Organisation Created!",
        description: `Welcome to Talenti, ${orgName}!`,
      });

      navigate("/org");
    } catch (error: any) {
      const code = error?.code ? String(error.code) : "";
      const message = error?.message ? String(error.message) : "Unknown error";
      const details = error?.details ? String(error.details) : error?.hint ? String(error.hint) : "";

      console.error("[OrgOnboarding] Create org failed:", {
        code,
        message,
        details,
      });

      const friendly = [code ? `[${code}]` : null, message, details].filter(Boolean).join(" ");

      toast({
        title: "Failed to Create Organisation",
        description: friendly || "An error occurred. Please try again.",
        variant: "destructive",
      });

      // If this was an auth/RLS issue, a quick sign-out/in typically resolves it.
      if (message.toLowerCase().includes("row-level security")) {
        console.warn("[OrgOnboarding] RLS denial detected; session may be missing/expired.");
      }
    } finally {
      setIsSubmitting(false);
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
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/30 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold">T</span>
            </div>
            <span className="text-xl font-bold">Talenti</span>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-12 max-w-2xl">
        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-4 mb-12">
          <div className={`flex items-center gap-2 ${step >= 1 ? "text-primary" : "text-muted-foreground"}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              step >= 1 ? "bg-primary text-primary-foreground" : "bg-muted"
            }`}>
              {step > 1 ? <CheckCircle2 className="w-5 h-5" /> : "1"}
            </div>
            <span className="font-medium">Organisation</span>
          </div>
          <div className="w-12 h-0.5 bg-muted" />
          <div className={`flex items-center gap-2 ${step >= 2 ? "text-primary" : "text-muted-foreground"}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
              step >= 2 ? "bg-primary text-primary-foreground" : "bg-muted"
            }`}>
              {step > 2 ? <CheckCircle2 className="w-5 h-5" /> : "2"}
            </div>
            <span className="font-medium">Details</span>
          </div>
        </div>

        <Card className="p-8">
          <form onSubmit={handleCreateOrg}>
            {step === 1 && (
              <div className="space-y-6">
                <div className="text-center mb-8">
                  <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                    <Building2 className="w-8 h-8 text-primary" />
                  </div>
                  <h1 className="text-2xl font-bold mb-2">Set Up Your Organisation</h1>
                  <p className="text-muted-foreground">
                    Let's get started by creating your organisation profile
                  </p>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="orgName">Organisation Name *</Label>
                    <div className="relative">
                      <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        id="orgName"
                        placeholder="Acme Corporation"
                        value={orgName}
                        onChange={(e) => setOrgName(e.target.value)}
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="industry">Industry</Label>
                    <Select value={industry} onValueChange={setIndustry}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select your industry" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="technology">Technology</SelectItem>
                        <SelectItem value="finance">Finance & Banking</SelectItem>
                        <SelectItem value="healthcare">Healthcare</SelectItem>
                        <SelectItem value="retail">Retail & E-commerce</SelectItem>
                        <SelectItem value="manufacturing">Manufacturing</SelectItem>
                        <SelectItem value="education">Education</SelectItem>
                        <SelectItem value="consulting">Consulting</SelectItem>
                        <SelectItem value="media">Media & Entertainment</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="website">Website</Label>
                    <div className="relative">
                      <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        id="website"
                        type="url"
                        placeholder="https://www.example.com"
                        value={website}
                        onChange={(e) => setWebsite(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>
                </div>

                <Button 
                  type="button" 
                  className="w-full" 
                  onClick={() => setStep(2)}
                  disabled={!orgName.trim()}
                >
                  Continue
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-6">
                <div className="text-center mb-8">
                  <h1 className="text-2xl font-bold mb-2">Almost There!</h1>
                  <p className="text-muted-foreground">
                    Add a few more details about {orgName}
                  </p>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="description">Company Description</Label>
                    <Textarea
                      id="description"
                      placeholder="Tell candidates about your company, culture, and mission..."
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      rows={4}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="billingEmail">Billing Email</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        id="billingEmail"
                        type="email"
                        placeholder="billing@example.com"
                        value={billingEmail}
                        onChange={(e) => setBillingEmail(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      We'll send invoices and billing notifications to this email
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <Button 
                    type="button" 
                    variant="outline" 
                    className="flex-1"
                    onClick={() => setStep(1)}
                  >
                    Back
                  </Button>
                  <Button type="submit" className="flex-1" disabled={isSubmitting}>
                    {isSubmitting ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      "Create Organisation"
                    )}
                  </Button>
                </div>
              </div>
            )}
          </form>
        </Card>

        <p className="text-center text-sm text-muted-foreground mt-6">
          You can update these details anytime from your organisation settings
        </p>
      </div>
    </div>
  );
};

export default OrgOnboarding;
