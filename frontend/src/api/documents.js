import api from "./client";

export async function listDocuments() {
  const res = await api.get("/documents");
  return res.data;
}

export async function getDocument(id) {
  const res = await api.get(`/documents/${id}`);
  return res.data;
}

export async function getChatHistory(id) {
  const res = await api.get(`/documents/${id}/chat`);
  return res.data;
}

export async function sendChatMessage(id, message) {
  const res = await api.post(`/documents/${id}/chat`, { message });
  return res.data;
}

export async function getSummary(id, { force = false } = {}) {
  const res = await api.post(`/documents/${id}/summary`, null, {
    params: force ? { force: true } : undefined,
  });
  return res.data;
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await api.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}
