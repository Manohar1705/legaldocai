import api from "./client";

export async function registerUser({ email, password, full_name }) {
  const res = await api.post("/auth/register", { email, password, full_name });
  return res.data;
}

export async function loginUser({ email, password }) {
  const res = await api.post("/auth/login", { email, password });
  return res.data; // { access_token, token_type }
}

export async function getCurrentUser() {
  const res = await api.get("/auth/me");
  return res.data;
}
