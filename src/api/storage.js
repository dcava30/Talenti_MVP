import { http } from "./http";

export const storageApi = {
    createUploadUrl(payload) {
        return http.post("/api/storage/upload-url", payload);
    },
};
