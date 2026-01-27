import { http } from "./http";

export const interviewsApi = {
  aiInterviewer(payload: Record<string, unknown>) {
    return http.post<{ reply: string; usage_tokens?: number }>("/api/v1/interview/chat", payload);
  },
  getContext(applicationId: string) {
    return http.get<any>(`/api/v1/applications/${applicationId}/context`);
  },
  findActive(applicationId: string) {
    return http.get<any>("/api/v1/interviews/active", { application_id: applicationId });
  },
  create(payload: Record<string, unknown>) {
    return http.post<any>("/api/v1/interviews", payload);
  },
  update(interviewId: string, payload: Record<string, unknown>) {
    return http.patch<any>(`/api/v1/interviews/${interviewId}`, payload);
  },
  getById(interviewId: string) {
    return http.get<any>(`/api/v1/interviews/${interviewId}`);
  },
  getReport(interviewId: string) {
    return http.get<any>(`/api/v1/interviews/${interviewId}/report`);
  },
  getScore(interviewId: string) {
    return http.get<any>(`/api/v1/interviews/${interviewId}/score`);
  },
  listDimensions(interviewId: string) {
    return http.get<any[]>(`/api/v1/interviews/${interviewId}/dimensions`);
  },
  listTranscripts(interviewId: string) {
    return http.get<any[]>(`/api/v1/interviews/${interviewId}/transcripts`);
  },
  addTranscript(interviewId: string, payload: Record<string, unknown>) {
    return http.post<any>(`/api/v1/interviews/${interviewId}/transcripts`, payload);
  },
  saveScores(interviewId: string, payload: Record<string, unknown>) {
    return http.post<any>(`/api/v1/interviews/${interviewId}/scores`, payload);
  },
  updateScore(scoreId: string, payload: Record<string, unknown>) {
    return http.patch<any>(`/api/v1/interview-scores/${scoreId}`, payload);
  },
  updateApplication(applicationId: string, payload: Record<string, unknown>) {
    return http.patch<any>(`/api/v1/applications/${applicationId}`, payload);
  },
  listRoleApplications(roleId: string) {
    return http.get<any[]>(`/api/v1/roles/${roleId}/applications`);
  },
  listCandidateApplications(candidateId?: string) {
    return http.get<any[]>("/api/v1/applications", candidateId ? { candidate_id: candidateId } : undefined);
  },
};
