const repoForm = document.querySelector("#repo-form");
const repoInput = document.querySelector("#repo-url");
const loadButton = document.querySelector("#load-button");
const repoStatus = document.querySelector("#repo-status");
const chatForm = document.querySelector("#chat-form");
const questionInput = document.querySelector("#question");
const sendButton = document.querySelector("#send-button");
const messagesEl = document.querySelector("#messages");

let repository = "";
let history = [];
let busy = false;

function apiUrl(path) {
  const baseUrl = window.APP_CONFIG?.apiBaseUrl?.trim();
  if (!baseUrl || baseUrl.includes("YOUR-RENDER-SERVICE")) {
    throw new Error("Set the deployed backend URL in frontend/config.js first.");
  }
  return `${baseUrl.replace(/\/+$/, "")}${path}`;
}

function setBusy(value) {
  busy = value;
  sendButton.disabled = value || !repository || !questionInput.value.trim();
  loadButton.disabled = value;
}

function addMessage(role, text, isError = false) {
  const bubble = document.createElement("div");
  bubble.className = `message ${role}${isError ? " error" : ""}`;
  bubble.textContent = text;
  messagesEl.append(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return bubble;
}

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.question;
    questionInput.dispatchEvent(new Event("input"));
    if (repository) chatForm.requestSubmit();
    else repoInput.focus();
  });
});

repoForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const value = repoInput.value.trim();
  try {
    const parsed = new URL(value);
    if (parsed.hostname !== "github.com" && parsed.hostname !== "www.github.com") {
      throw new Error("Please enter a github.com repository URL.");
    }
    if (parsed.pathname.split("/").filter(Boolean).length !== 2) {
      throw new Error("Use the repository's main URL, like github.com/owner/repo.");
    }
    repository = value;
    history = [];
    messagesEl.replaceChildren();
    repoStatus.textContent = `Connected to ${parsed.pathname.split("/").filter(Boolean).slice(0, 2).join("/")}`;
    questionInput.disabled = false;
    questionInput.focus();
    setBusy(false);
    addMessage("assistant", `Connected. What would you like to know about ${parsed.pathname.split("/").filter(Boolean).slice(0, 2).join("/ ")}?`);
  } catch (error) {
    repository = "";
    repoStatus.textContent = "Ready when you are";
    questionInput.disabled = true;
    setBusy(false);
    addMessage("assistant", error.message, true);
  }
});

questionInput.addEventListener("input", () => {
  questionInput.style.height = "auto";
  questionInput.style.height = `${Math.min(questionInput.scrollHeight, 110)}px`;
  sendButton.disabled = busy || !repository || !questionInput.value.trim();
});

questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    if (!sendButton.disabled) chatForm.requestSubmit();
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question || !repository || busy) return;

  addMessage("user", question);
  questionInput.value = "";
  questionInput.style.height = "auto";
  const pending = addMessage("assistant", "Looking through the repository…");
  pending.classList.add("typing");
  setBusy(true);

  try {
    const response = await fetch(apiUrl("/api/chat"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repository, question, history })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Request failed (${response.status}).`);
    pending.classList.remove("typing");
    pending.textContent = data.answer;
    history = [...history, { role: "user", content: question }, { role: "assistant", content: data.answer }].slice(-12);
  } catch (error) {
    pending.classList.add("error");
    pending.classList.remove("typing");
    pending.textContent = error.message || "Could not reach the AI service.";
  } finally {
    setBusy(false);
    questionInput.focus();
  }
});
