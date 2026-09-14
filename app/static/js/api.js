/**
 * XgirlfriendGPT Frontend API Client Service
 */
export const API = {
    async getCompanions() {
        const res = await fetch("/api/v1/clone/list");
        if (!res.ok) throw new Error("Failed to fetch characters");
        return await res.json();
    },

    async getCompanionProfile(id) {
        const res = await fetch(`/api/v1/clone/profile/${id}`);
        if (!res.ok) throw new Error("Character profile not found");
        return await res.json();
    },

    async updateCompanionProfile(id, data) {
        const res = await fetch(`/api/v1/clone/profile/${id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error("Failed to update companion profile");
        return await res.json();
    },

    async getChatHistory(id) {
        const res = await fetch(`/api/v1/chat/history/${id}`);
        return res.ok ? await res.json() : [];
    },

    async postMessage(payload) {
        const res = await fetch("/api/v1/chat/message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error("Chat request failed");
        return await res.json();
    },

    async synthesizeVoice(text) {
        const res = await fetch("/api/v1/voice/synthesize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });
        if (!res.ok) throw new Error("Voice synthesis failed");
        return await res.json();
    },

    async generateSelfie(companionId, prompt) {
        const res = await fetch(`/api/v1/chat/selfie/${companionId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt })
        });
        if (!res.ok) throw new Error("Selfie generation failed");
        return await res.json();
    },

    async deleteCompanion(id) {
        const res = await fetch(`/api/v1/clone/${id}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Failed to delete character");
        return await res.json();
    }
};
