import { describe, expect, it, vi } from "vitest";

vi.mock("../http", () => ({
    http: {
        get: vi.fn(),
        post: vi.fn(),
        patch: vi.fn(),
        delete: vi.fn(),
    },
}));

const { http } = await import("../http");
const { interviewsApi } = await import("../interviews");
const { auditApi } = await import("../audit");
const { organisationsApi } = await import("../organisations");
const { rolesApi } = await import("../roles");
const { storageApi } = await import("../storage");

describe("API endpoints", () => {
    it("targets interview lifecycle endpoints", () => {
        interviewsApi.start({ application_id: "app-1", recording_consent: true });
        expect(http.post).toHaveBeenCalledWith("/api/v1/interviews/start", {
            application_id: "app-1",
            recording_consent: true,
        });

        interviewsApi.complete("int-1", { duration_seconds: 120 });
        expect(http.post).toHaveBeenCalledWith("/api/v1/interviews/int-1/complete", {
            duration_seconds: 120,
        });
    });

    it("targets the AI interview endpoint", () => {
        interviewsApi.aiInterviewer({ interview_id: "int-1", messages: [] });
        expect(http.post).toHaveBeenCalledWith("/api/v1/interview/chat", {
            interview_id: "int-1",
            messages: [],
        });
    });

    it("targets the recruiter decision endpoint", () => {
        interviewsApi.getInterviewDecision("int-1");
        expect(http.get).toHaveBeenCalledWith("/api/v1/interviews/int-1/decision");
    });

    it("targets the recruiter skills assessment summary endpoint", () => {
        interviewsApi.getInterviewSkillsAssessmentSummary("int-1");
        expect(http.get).toHaveBeenCalledWith("/api/v1/interviews/int-1/skills-assessment-summary");
    });

    it("targets applications context endpoint", () => {
        interviewsApi.getContext("app-1");
        expect(http.get).toHaveBeenCalledWith("/api/v1/applications/app-1/context");
    });

    it("targets application listing endpoint", () => {
        interviewsApi.listCandidateApplications("cand-1");
        expect(http.get).toHaveBeenCalledWith("/api/v1/applications", { candidate_id: "cand-1" });
    });

    it("targets audit log endpoints", () => {
        auditApi.list("org-1");
        expect(http.get).toHaveBeenCalledWith("/api/v1/audit-log", { organisation_id: "org-1" });
        auditApi.create({ action: "update", entity_type: "application" });
        expect(http.post).toHaveBeenCalledWith("/api/v1/audit-log", {
            action: "update",
            entity_type: "application",
        });
    });

    it("targets blob upload url endpoint", () => {
        storageApi.createUploadUrl({
            file_name: "resume.pdf",
            content_type: "application/pdf",
            purpose: "candidate_cv",
        });
        expect(http.post).toHaveBeenCalledWith("/api/storage/upload-url", {
            file_name: "resume.pdf",
            content_type: "application/pdf",
            purpose: "candidate_cv",
        });
    });

    it("targets organisation endpoints", () => {
        organisationsApi.getCurrentMembership();
        expect(http.get).toHaveBeenCalledWith("/api/orgs/current");

        organisationsApi.updateRetention("org-1", 45);
        expect(http.patch).toHaveBeenCalledWith("/api/orgs/org-1/retention", {
            recording_retention_days: 45,
        });

        organisationsApi.getStats("org-1");
        expect(http.get).toHaveBeenCalledWith("/api/orgs/org-1/stats");
    });

    it("targets role listing endpoint", () => {
        rolesApi.listAll({ limit: 1 });
        expect(http.get).toHaveBeenCalledWith("/api/roles", { limit: 1 });
    });
});
