import { http } from "./http";
export const interviewsApi = {
    aiInterviewer(payload) {
        return http.post("/api/v1/interview/chat", payload);
    },
    getContext(applicationId) {
        return http.get(`/api/v1/applications/${applicationId}/context`);
    },
    findActive(applicationId) {
        return http.get("/api/v1/interviews/active", { application_id: applicationId });
    },
    create(payload) {
        return http.post("/api/v1/interviews", payload);
    },
    update(interviewId, payload) {
        return http.patch(`/api/v1/interviews/${interviewId}`, payload);
    },
    getById(interviewId) {
        return http.get(`/api/v1/interviews/${interviewId}`);
    },
    getReport(interviewId) {
        return http.get(`/api/v1/interviews/${interviewId}/report`);
    },
    getScore(interviewId) {
        return http.get(`/api/v1/interviews/${interviewId}/score`);
    },
    listDimensions(interviewId) {
        return http.get(`/api/v1/interviews/${interviewId}/dimensions`);
    },
    listTranscripts(interviewId) {
        return http.get(`/api/v1/interviews/${interviewId}/transcripts`);
    },
    addTranscript(interviewId, payload) {
        return http.post(`/api/v1/interviews/${interviewId}/transcripts`, payload);
    },
    saveScores(interviewId, payload) {
        return http.post(`/api/v1/interviews/${interviewId}/scores`, payload);
    },
    updateScore(scoreId, payload) {
        return http.patch(`/api/v1/interview-scores/${scoreId}`, payload);
    },
    updateApplication(applicationId, payload) {
        return http.patch(`/api/v1/applications/${applicationId}`, payload);
    },
    listRoleApplications(roleId) {
        return http.get(`/api/v1/roles/${roleId}/applications`);
    },
    listCandidateApplications(candidateId) {
        return http.get("/api/v1/applications", candidateId ? { candidate_id: candidateId } : undefined);
    },
};
