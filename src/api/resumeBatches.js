import { http } from "./http";

export const resumeBatchesApi = {
    create(payload) {
        return http.post("/api/v1/resume-batches", payload);
    },
    get(batchId) {
        return http.get(`/api/v1/resume-batches/${batchId}`);
    },
    listItems(batchId) {
        return http.get(`/api/v1/resume-batches/${batchId}/items`);
    },
    createItemUploadUrl(batchId, payload) {
        return http.post(`/api/v1/resume-batches/${batchId}/items/upload-url`, payload);
    },
    process(batchId) {
        return http.post(`/api/v1/resume-batches/${batchId}/process`);
    },
    updateItem(itemId, payload) {
        return http.patch(`/api/v1/resume-batches/items/${itemId}`, payload);
    },
    invite(batchId, payload) {
        return http.post(`/api/v1/resume-batches/${batchId}/invite`, payload);
    },
};
