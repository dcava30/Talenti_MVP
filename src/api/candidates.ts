import { http, request } from "./http";

export interface CandidateProfilePayload {
  user_id?: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  suburb?: string;
  postcode?: string;
  state?: string;
  country?: string;
  work_rights?: string;
  availability?: string;
  work_mode?: string;
  gpa_wam?: number | null;
  portfolio_url?: string;
  linkedin_url?: string;
  cv_file_path?: string;
  cv_uploaded_at?: string;
  profile_visibility?: string;
  paused_at?: string | null;
  visibility_settings?: Record<string, unknown>;
}

export const candidatesApi = {
  getProfile(userId?: string) {
    return http.get<any>("/api/v1/candidates/profile", userId ? { user_id: userId } : undefined);
  },
  upsertProfile(payload: CandidateProfilePayload) {
    return http.post<any>("/api/v1/candidates/profile", payload);
  },
  updateProfile(userId: string, payload: CandidateProfilePayload) {
    return http.patch<any>(`/api/v1/candidates/${userId}/profile`, payload);
  },
  listEmployment(userId?: string) {
    return http.get<any[]>("/api/v1/candidates/employment", userId ? { user_id: userId } : undefined);
  },
  createEmployment(payload: Record<string, unknown>) {
    return http.post<any>("/api/v1/candidates/employment", payload);
  },
  updateEmployment(employmentId: string, payload: Record<string, unknown>) {
    return http.patch<any>(`/api/v1/candidates/employment/${employmentId}`, payload);
  },
  deleteEmployment(employmentId: string) {
    return http.delete<void>(`/api/v1/candidates/employment/${employmentId}`);
  },
  listEducation(userId?: string) {
    return http.get<any[]>("/api/v1/candidates/education", userId ? { user_id: userId } : undefined);
  },
  createEducation(payload: Record<string, unknown>) {
    return http.post<any>("/api/v1/candidates/education", payload);
  },
  updateEducation(educationId: string, payload: Record<string, unknown>) {
    return http.patch<any>(`/api/v1/candidates/education/${educationId}`, payload);
  },
  deleteEducation(educationId: string) {
    return http.delete<void>(`/api/v1/candidates/education/${educationId}`);
  },
  listSkills(userId?: string) {
    return http.get<any[]>("/api/v1/candidates/skills", userId ? { user_id: userId } : undefined);
  },
  createSkill(payload: Record<string, unknown>) {
    return http.post<any>("/api/v1/candidates/skills", payload);
  },
  deleteSkill(skillId: string) {
    return http.delete<void>(`/api/v1/candidates/skills/${skillId}`);
  },
  listApplications() {
    return http.get<any[]>("/api/v1/candidates/applications");
  },
  listInvitations() {
    return http.get<any[]>("/api/v1/candidates/invitations");
  },
  listFeedback() {
    return http.get<any[]>("/api/v1/candidates/feedback");
  },
  createApplication(payload: Record<string, unknown>) {
    return http.post<any>("/api/v1/candidates/applications", payload);
  },
  listPracticeInterviews() {
    return http.get<any[]>("/api/v1/candidates/practice-interviews");
  },
  createPracticeInterview(payload: Record<string, unknown>) {
    return http.post<any>("/api/v1/candidates/practice-interviews", payload);
  },
  updatePracticeInterview(practiceId: string, payload: Record<string, unknown>) {
    return http.patch<any>(`/api/v1/candidates/practice-interviews/${practiceId}`, payload);
  },
  getPracticeInterview(practiceId: string) {
    return http.get<any>(`/api/v1/candidates/practice-interviews/${practiceId}`);
  },
  listDeletionRequests() {
    return http.get<any[]>("/api/v1/candidates/deletion-requests");
  },
  createDeletionRequest(payload: Record<string, unknown>) {
    return http.post<any>("/api/v1/candidates/deletion-requests", payload);
  },
  deleteAccount(userId: string) {
    return http.delete<void>(`/api/v1/candidates/${userId}`);
  },
  async uploadCv(file: File, candidateId?: string) {
    const formData = new FormData();
    formData.append("file", file);
    if (candidateId) {
      formData.append("candidate_id", candidateId);
    }
    return request<any>("/api/v1/candidates/cv", {
      method: "POST",
      body: formData,
    });
  },
};
