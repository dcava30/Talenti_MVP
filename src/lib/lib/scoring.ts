import { interviewsApi } from "@/api/interviews";
import { scoringApi } from "@/api/scoring";

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

    const interview = await interviewsApi.getById(interviewId);
    if (!interview) {
      console.error("Failed to fetch interview:", interviewId);
      return null;
    }

    const transcripts = await interviewsApi.listTranscripts(interviewId);

    if (!transcripts || transcripts.length === 0) {
      console.log("No transcripts available for scoring");
      return null;
    }

    // Access nested data safely
    const application = interview.application || interview.applications;
    const jobRole = application?.job_role || application?.job_roles;
    const organisation = jobRole?.organisation || jobRole?.organisations;
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
    const apiResult = await scoringApi.scoreInterview({
      interview_id: interviewId,
      transcript: transcripts.map(t => ({
        speaker: t.speaker,
        content: t.content,
        start_time_ms: t.start_time_ms,
      })),
      job_title: jobRole?.title || "Unknown Position",
      job_description: jobRole?.description,
      requirements: requirements ? {
        skills: requirements.skills || [],
        experience: requirements.experience || [],
        qualifications: requirements.qualifications || [],
        responsibilities: requirements.responsibilities || [],
      } : undefined,
      org_values: orgValues,
      scoring_rubric: scoringRubric,
    });

    const result: ScoringResult = {
      success: true,
      interviewId,
      dimensions: apiResult.dimensions || [],
      overall_score: apiResult.overall_score ?? apiResult.overall ?? 0,
      narrative_summary: apiResult.summary || apiResult.narrative_summary || "",
      candidate_feedback: apiResult.candidate_feedback || "",
      anti_cheat_risk_level: apiResult.anti_cheat_risk_level || "low",
      anti_cheat_notes: apiResult.anti_cheat_notes,
    };

    if (result.success === false) {
      console.error("Scoring failed:", result.error);
      return null;
    }

    console.log("Scoring completed successfully:", result.overall_score);

    // Save scores to database
    await saveScoresToDatabase(interviewId, result, interview);

    return result;
  } catch (error) {
    console.error("Error triggering scoring:", error);
    return null;
  }
};

const saveScoresToDatabase = async (
  interviewId: string,
  result: ScoringResult,
  interview?: Record<string, any>
): Promise<void> => {
  try {
    await interviewsApi.saveScores(interviewId, {
      interview_id: interviewId,
      overall_score: result.overall_score,
      narrative_summary: result.narrative_summary,
      candidate_feedback: result.candidate_feedback,
      anti_cheat_risk_level: result.anti_cheat_risk_level,
      scored_by: "ai",
      model_version: "gemini-2.5-flash",
      prompt_version: "v2.0",
      rubric_version: "v2.0",
      dimensions: result.dimensions,
    });

    const applicationId = interview?.application_id || interview?.application?.id;
    if (applicationId) {
      await interviewsApi.updateApplication(applicationId, { status: "reviewed" });
    }

    console.log("Scores saved to database successfully");
  } catch (error) {
    console.error("Error saving scores:", error);
  }
};

export const getInterviewScore = async (interviewId: string) => {
  const score = await interviewsApi.getScore(interviewId);
  if (!score) return null;

  const dimensions = await interviewsApi.listDimensions(interviewId);

  return {
    ...score,
    score_dimensions: dimensions || [],
  };
};
