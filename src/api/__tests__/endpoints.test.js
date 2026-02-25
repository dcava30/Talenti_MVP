import { describe, expect, it, vi } from "vitest";

vi.mock("../http", () => ({
    http: {
        get: vi.fn(),
        post: vi.fn(),
        patch: vi.fn(),
        delete: vi.fn(),
    },
    request: vi.fn(),
}));

const { http, request } = await import("../http");
const { interviewsApi } = await import("../interviews");
const { candidatesApi } = await import("../candidates");
const { auditApi } = await import("../audit");
const { organisationsApi } = await import("../organisations");
const { rolesApi } = await import("../roles");

describe("API endpoints", () => {
    it("targets the AI interview endpoint", () => {
        interviewsApi.aiInterviewer({ interview_id: "int-1", messages: [] });
        expect(http.post).toHaveBeenCalledWith("/api/v1/interview/chat", {
            interview_id: "int-1",
            messages: [],
        });
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

    it("targets candidate CV upload endpoint", () => {
        request.mockClear();
        request.mockImplementation(() => Promise.resolve());
        const file = new Blob(["resume"], { type: "text/plain" });
        candidatesApi.uploadCv(file);
        expect(request).toHaveBeenCalledWith("/api/v1/candidates/cv", {
            method: "POST",
            body: expect.any(FormData),
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
