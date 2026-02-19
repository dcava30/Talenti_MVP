import { http, request } from "./http";
export const candidatesApi = {
    getProfile(userId) {
        return http.get("/api/v1/candidates/profile", userId ? { user_id: userId } : undefined);
    },
    upsertProfile(payload) {
        return http.post("/api/v1/candidates/profile", payload);
    },
    updateProfile(userId, payload) {
        return http.patch(`/api/v1/candidates/${userId}/profile`, payload);
    },
    listEmployment(userId) {
        return http.get("/api/v1/candidates/employment", userId ? { user_id: userId } : undefined);
    },
    createEmployment(payload) {
        return http.post("/api/v1/candidates/employment", payload);
    },
    updateEmployment(employmentId, payload) {
        return http.patch(`/api/v1/candidates/employment/${employmentId}`, payload);
    },
    deleteEmployment(employmentId) {
        return http.delete(`/api/v1/candidates/employment/${employmentId}`);
    },
    listEducation(userId) {
        return http.get("/api/v1/candidates/education", userId ? { user_id: userId } : undefined);
    },
    createEducation(payload) {
        return http.post("/api/v1/candidates/education", payload);
    },
    updateEducation(educationId, payload) {
        return http.patch(`/api/v1/candidates/education/${educationId}`, payload);
    },
    deleteEducation(educationId) {
        return http.delete(`/api/v1/candidates/education/${educationId}`);
    },
    listSkills(userId) {
        return http.get("/api/v1/candidates/skills", userId ? { user_id: userId } : undefined);
    },
    createSkill(payload) {
        return http.post("/api/v1/candidates/skills", payload);
    },
    deleteSkill(skillId) {
        return http.delete(`/api/v1/candidates/skills/${skillId}`);
    },
    listApplications() {
        return http.get("/api/v1/candidates/applications");
    },
    listInvitations() {
        return http.get("/api/v1/candidates/invitations");
    },
    listFeedback() {
        return http.get("/api/v1/candidates/feedback");
    },
    createApplication(payload) {
        return http.post("/api/v1/candidates/applications", payload);
    },
    listPracticeInterviews() {
        return http.get("/api/v1/candidates/practice-interviews");
    },
    createPracticeInterview(payload) {
        return http.post("/api/v1/candidates/practice-interviews", payload);
    },
    updatePracticeInterview(practiceId, payload) {
        return http.patch(`/api/v1/candidates/practice-interviews/${practiceId}`, payload);
    },
    getPracticeInterview(practiceId) {
        return http.get(`/api/v1/candidates/practice-interviews/${practiceId}`);
    },
    listDeletionRequests() {
        return http.get("/api/v1/candidates/deletion-requests");
    },
    createDeletionRequest(payload) {
        return http.post("/api/v1/candidates/deletion-requests", payload);
    },
    deleteAccount(userId) {
        return http.delete(`/api/v1/candidates/${userId}`);
    },
    async uploadCv(file, candidateId) {
        const formData = new FormData();
        formData.append("file", file);
        if (candidateId) {
            formData.append("candidate_id", candidateId);
        }
        return request("/api/v1/candidates/cv", {
            method: "POST",
            body: formData,
        });
    },
};
