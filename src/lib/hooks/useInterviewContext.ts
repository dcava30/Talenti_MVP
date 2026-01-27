import { useState, useEffect } from "react";
import { interviewsApi } from "@/api/interviews";

/**
 * Job role context for the AI interviewer.
 */
interface JobContext {
  /** Job title */
  title: string;
  /** Full job description */
  description: string;
  /** Structured requirements */
  requirements: {
    /** Required technical and soft skills */
    skills: string[];
    /** Required experience descriptions */
    experience: string[];
    /** Required qualifications/certifications */
    qualifications: string[];
    /** Key job responsibilities */
    responsibilities: string[];
  };
  /** Pre-configured interview questions */
  interviewQuestions: string[];
}

/**
 * Organisation context for the AI interviewer.
 */
interface OrgContext {
  /** Organisation name */
  name: string;
  /** Company values to assess for culture fit */
  values: string[];
  /** Industry sector */
  industry: string;
}

/**
 * Candidate context extracted from their profile.
 */
interface CandidateContext {
  /** Candidate's listed skills */
  skills: string[];
  /** Total years of work experience */
  experienceYears: number;
  /** Recent job titles */
  recentRoles: string[];
  /** Highest education level */
  educationLevel: string;
}

/**
 * Context-Augmented Generation (CAG) context for AI interviewer.
 * 
 * Combines job, organisation, and candidate information to provide
 * the AI with full context for conducting personalized interviews.
 */
interface CAGContext {
  /** Job role details and requirements */
  job: JobContext | null;
  /** Organisation information and values */
  org: OrgContext | null;
  /** Candidate profile and experience */
  candidate: CandidateContext | null;
  /** Competencies that have been covered in the interview */
  competenciesCovered: string[];
  /** Competencies still to be assessed */
  competenciesToCover: string[];
}

/**
 * Hook for loading and managing interview context (CAG).
 * 
 * Fetches job requirements, organisation values, and candidate
 * information to provide the AI interviewer with full context.
 * Tracks which competencies have been covered during the interview.
 * 
 * @param applicationId - The UUID of the application being interviewed
 * @returns Object with context data, loading state, and control functions
 * 
 * @example
 * ```tsx
 * const { context, isLoading, markCompetencyCovered } = useInterviewContext(appId);
 * 
 * // Pass context to AI
 * const aiResponse = await callAIInterviewer({
 *   context,
 *   candidateResponse: transcript,
 * });
 * 
 * // Mark competencies as covered
 * markCompetencyCovered("React Experience");
 * ```
 */
export const useInterviewContext = (applicationId: string | undefined) => {
  const [context, setContext] = useState<CAGContext>({
    job: null,
    org: null,
    candidate: null,
    competenciesCovered: [],
    competenciesToCover: [],
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (applicationId) {
      loadContext();
    } else {
      setIsLoading(false);
    }
  }, [applicationId]);

  /**
   * Loads all context data from the database.
   * Fetches application, job role, organisation, and candidate data.
   */
  const loadContext = async (): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);

      const contextData = await interviewsApi.getContext(applicationId);

      setContext({
        job: contextData?.job ?? null,
        org: contextData?.org ?? null,
        candidate: contextData?.candidate ?? null,
        competenciesCovered: contextData?.competencies_covered ?? [],
        competenciesToCover: contextData?.competencies_to_cover ?? [],
      });
    } catch (err) {
      console.error("Error loading interview context:", err);
      setError(err instanceof Error ? err.message : "Failed to load context");
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Marks a competency as covered during the interview.
   * Moves it from competenciesToCover to competenciesCovered.
   * 
   * @param competency - The competency name to mark as covered
   */
  const markCompetencyCovered = (competency: string): void => {
    setContext(prev => ({
      ...prev,
      competenciesCovered: [...prev.competenciesCovered, competency],
      competenciesToCover: prev.competenciesToCover.filter(c => c !== competency),
    }));
  };

  return {
    /** The loaded CAG context */
    context,
    /** Whether context is still loading */
    isLoading,
    /** Error message if loading failed */
    error,
    /** Marks a competency as covered */
    markCompetencyCovered,
    /** Reloads the context data */
    reload: loadContext,
  };
};
