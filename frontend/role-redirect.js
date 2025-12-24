const AUTH_KEY = "audit_auth";
const raw = localStorage.getItem(AUTH_KEY);
function goLogin() { window.location.href = "login.html"; }
if (!raw) {
  goLogin();
} else {
  try {
    const auth = JSON.parse(raw);
    if (!auth?.role) return goLogin();
    if (auth.role === "admin") {
      window.location.href = "index.html";
    } else {
      window.location.href = "audit.html";
    }
  } catch {
    goLogin();
  }
}
