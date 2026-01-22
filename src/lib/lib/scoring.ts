import { supabase } from "@/integrations/supabase/client";

interface ScoreDimension {
  dimension: string;
  score: number;
  weight: number;
  evidence: string;
  cited_quotes: string[];
}

interface ScoringResult {
  success: boolean;
  interviewId: string;
  dimensions: ScoreDimension[];
  overall_score: number;
  narrative_summary: string;
  candidate_feedback: string;
  anti_cheat_risk_level: "low" | "medium" | "high";
  anti_cheat_notes?: string;
  error?: string;
}

export const triggerInterviewScoring = async (interviewId: string): Promise<ScoringResult | null> => {
  try {
    console.log("Fetching interview data for scoring:", interviewId);

    // Fetch interview with application, job role, and organization info
    const { data: interview, error: interviewError } = await supabase
      .from("interviews")
      .select(`
        id,
        application_id,
        applications!inner(
          job_role_id,
          job_roles!inner(
            title,
            description,
            requirements,
            scoring_rubric,
            organisations!inner(
              name,
              values_framework
            )
          )
        )
      `)
      .eq("id", interviewId)
      .single();

    if (interviewError || !interview) {
      console.error("Failed to fetch interview:", interviewError);
      return null;
    }

    // Fetch transcript segments
    const { data: transcripts, error: transcriptError } = await supabase
      .from("transcript_segments")
      .select("*")
      .eq("interview_id", interviewId)
      .order("start_time_ms", { ascending: true });

    if (transcriptError) {
      console.error("Failed to fetch transcripts:", transcriptError);
      return null;
    }

    if (!transcripts || transcripts.length === 0) {
      console.log("No transcripts available for scoring");
      return null;
    }

    // Access nested data safely
    const application = interview.applications as any;
    const jobRole = application?.job_roles;
    const organisation = jobRole?.organisations;
    const requirements = jobRole?.requirements as any;
    const scoringRubric = jobRole?.scoring_rubric as any;
    
    // Parse org values
    const valuesFramework = organisation?.values_framework as any;
    const orgValues = Array.isArray(valuesFramework) 
      ? valuesFramework 
      : (valuesFramework?.values || []);

    console.log("Scoring with custom rubric:", !!scoringRubric);
    console.log("Org values count:", orgValues?.length || 0);

    // Call scoring edge function with enhanced context
    const { data, error } = await supabase.functions.invoke("score-interview", {
      body: {
        interviewId,
        transcripts: transcripts.map(t => ({
          speaker: t.speaker,
          content: t.content,
          start_time_ms: t.start_time_ms,
        })),
        jobTitle: jobRole?.title || "Unknown Position",
        jobDescription: jobRole?.description,
        requirements: requirements ? {
          skills: requirements.skills || [],
          experience: requirements.experience || [],
          qualifications: requirements.qualifications || [],
          responsibilities: requirements.responsibilities || [],
        } : undefined,
        orgValues,
        scoringRubric,
      },
    });

    if (error) {
      console.error("Scoring function error:", error);
      return null;
    }

    const result = data as ScoringResult;

    if (!result.success) {
      console.error("Scoring failed:", result.error);
      return null;
    }

    console.log("Scoring completed successfully:", result.overall_score);

    // Save scores to database
    await saveScoresToDatabase(interviewId, result);

    return result;
  } catch (error) {
    console.error("Error triggering scoring:", error);
    return null;
  }
};

const saveScoresToDatabase = async (interviewId: string, result: ScoringResult): Promise<void> => {
  try {
    // Save individual dimension scores
    const dimensionInserts = result.dimensions.map(dim => ({
      interview_id: interviewId,
      dimension: dim.dimension,
      score: dim.score,
      weight: dim.weight,
      evidence: dim.evidence,
      cited_quotes: dim.cited_quotes,
    }));

    const { error: dimError } = await supabase
      .from("score_dimensions")
      .insert(dimensionInserts);

    if (dimError) {
      console.error("Failed to save dimension scores:", dimError);
    }

    // Save overall score
    const { error: scoreError } = await supabase
      .from("interview_scores")
      .upsert({
        interview_id: interviewId,
        overall_score: result.overall_score,
        narrative_summary: result.narrative_summary,
        candidate_feedback: result.candidate_feedback,
        anti_cheat_risk_level: result.anti_cheat_risk_level,
        scored_by: "ai",
        model_version: "gemini-2.5-flash",
        prompt_version: "v2.0",
        rubric_version: "v2.0",
      }, {
        onConflict: "interview_id",
      });

    if (scoreError) {
      console.error("Failed to save interview score:", scoreError);
    }

    // Update application status to 'scoring' -> 'reviewed'
    const { data: interview } = await supabase
      .from("interviews")
      .select("application_id")
      .eq("id", interviewId)
      .single();

    if (interview) {
      await supabase
        .from("applications")
        .update({ status: "reviewed" })
        .eq("id", interview.application_id);
    }

    console.log("Scores saved to database successfully");
  } catch (error) {
    console.error("Error saving scores:", error);
  }
};

export const getInterviewScore = async (interviewId: string) => {
  // Fetch interview score
  const { data: score, error: scoreError } = await supabase
    .from("interview_scores")
    .select("*")
    .eq("interview_id", interviewId)
    .maybeSingle();

  if (scoreError) {
    console.error("Error fetching interview score:", scoreError);
    return null;
  }

  if (!score) return null;

  // Fetch dimensions separately
  const { data: dimensions, error: dimError } = await supabase
    .from("score_dimensions")
    .select("*")
    .eq("interview_id", interviewId);

  if (dimError) {
    console.error("Error fetching score dimensions:", dimError);
  }

  return {
    ...score,
    score_dimensions: dimensions || [],
  };
};