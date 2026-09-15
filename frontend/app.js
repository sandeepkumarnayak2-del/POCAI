let accessToken = null;

const loginSection = document.getElementById("loginSection");
const mainSection = document.getElementById("mainSection");
const loginForm = document.getElementById("loginForm");
const loginError = document.getElementById("loginError");
const logoutBtn = document.getElementById("logoutBtn");
const userInfo = document.getElementById("userInfo");

const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const chatMessages = document.getElementById("chatMessages");
const sendBtn = document.getElementById("sendBtn");
const charCount = document.getElementById("charCount");

const ticketsList = document.getElementById("ticketsList");
const approvalsList = document.getElementById("approvalsList");

const refreshTickets = document.getElementById("refreshTickets");
const refreshApprovals = document.getElementById("refreshApprovals");

const apiStatus = document.getElementById("apiStatus");
const environment = document.getElementById("environment");
const llmProvider = document.getElementById("llmProvider");


loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    loginError.classList.add("hidden");

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    try {
        const response = await fetch("/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Login failed");
        }

        accessToken = data.access_token;

        loginSection.classList.add("hidden");
        mainSection.classList.remove("hidden");
        logoutBtn.classList.remove("hidden");

        userInfo.textContent = username;

        await loadStatus();
        await loadTickets();
        await loadApprovals();

        messageInput.focus();

    } catch (error) {
        loginError.textContent = error.message;
        loginError.classList.remove("hidden");
    }
});


logoutBtn.addEventListener("click", () => {
    accessToken = null;

    mainSection.classList.add("hidden");
    loginSection.classList.remove("hidden");
    logoutBtn.classList.add("hidden");

    userInfo.textContent = "";

    chatMessages.innerHTML = `
        <div class="message assistant">
            <div class="message-label">Max</div>
            <div class="message-content">
                Hello! I can help with IT issues, internal documentation
                and service desk tickets.
            </div>
        </div>
    `;

    ticketsList.innerHTML = "";
    approvalsList.innerHTML = "";
});


async function apiRequest(url, options = {}) {
    const headers = options.headers || {};

    if (accessToken) {
        headers["Authorization"] = `Bearer ${accessToken}`;
    }

    options.headers = headers;

    const response = await fetch(url, options);

    if (response.status === 401) {
        accessToken = null;
        throw new Error("Your session has expired. Please login again.");
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.detail || "Request failed");
    }

    return data;
}


chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const message = messageInput.value.trim();

    if (!message) {
        return;
    }

    addMessage("user", message);

    messageInput.value = "";
    updateCharacterCount();

    sendBtn.disabled = true;
    sendBtn.textContent = "Thinking...";

    try {
        const data = await apiRequest("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message
            })
        });

        addMessage(
            "assistant",
            data.reply || "The assistant did not return a response."
        );

        if (data.approval_id) {
            await loadApprovals();

            addMessage(
                "assistant",
                `This action requires approval. Approval ID: ${data.approval_id}`
            );
        }

        await loadTickets();

    } catch (error) {
        addMessage("assistant", `Error: ${error.message}`);

    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = "Send";
        messageInput.focus();
    }
});


function addMessage(type, text) {
    const message = document.createElement("div");
    message.className = `message ${type}`;

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = type === "user" ? "You" : "Max";

    const content = document.createElement("div");
    content.className = "message-content";
    content.textContent = text;

    message.appendChild(label);
    message.appendChild(content);

    chatMessages.appendChild(message);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}


messageInput.addEventListener("input", updateCharacterCount);

function updateCharacterCount() {
    charCount.textContent = `${messageInput.value.length} / 1000`;
}


async function loadTickets() {
    ticketsList.innerHTML = '<p class="muted">Loading...</p>';

    try {
        const data = await apiRequest("/tickets");

        const tickets = Array.isArray(data)
            ? data
            : data.tickets || [];

        if (tickets.length === 0) {
            ticketsList.innerHTML =
                '<p class="muted">No tickets found.</p>';
            return;
        }

        ticketsList.innerHTML = "";

        tickets.forEach((ticket) => {
            const item = document.createElement("div");
            item.className = "ticket";

            const title = document.createElement("div");
            title.className = "ticket-title";
            title.textContent =
                ticket.title ||
                ticket.subject ||
                `Ticket #${ticket.id}`;

            const meta = document.createElement("div");
            meta.className = "ticket-meta";
            meta.textContent =
                `#${ticket.id} · ${ticket.status || "unknown"}`;

            const badge = document.createElement("span");
            badge.className = "badge";
            badge.textContent = ticket.priority || "normal";

            item.appendChild(title);
            item.appendChild(meta);
            item.appendChild(badge);

            ticketsList.appendChild(item);
        });

    } catch (error) {
        ticketsList.innerHTML =
            `<p class="error">${escapeHtml(error.message)}</p>`;
    }
}


async function loadApprovals() {
    approvalsList.innerHTML = '<p class="muted">Loading...</p>';

    try {
        const data = await apiRequest("/approvals");

        const approvals = Array.isArray(data)
            ? data
            : data.approvals || [];

        if (approvals.length === 0) {
            approvalsList.innerHTML =
                '<p class="muted">No pending approvals.</p>';
            return;
        }

        approvalsList.innerHTML = "";

        approvals.forEach((approval) => {
            const item = document.createElement("div");
            item.className = "approval";

            const text = document.createElement("div");
            text.className = "approval-text";

            text.textContent =
                approval.description ||
                approval.action ||
                `Approval #${approval.id}`;

            const actions = document.createElement("div");
            actions.className = "approval-actions";

            const approveBtn = document.createElement("button");
            approveBtn.textContent = "Approve";
            approveBtn.className = "primary-btn";

            const rejectBtn = document.createElement("button");
            rejectBtn.textContent = "Reject";
            rejectBtn.className = "secondary-btn";

            approveBtn.addEventListener("click", () => {
                handleApproval(approval.id, true);
            });

            rejectBtn.addEventListener("click", () => {
                handleApproval(approval.id, false);
            });

            actions.appendChild(approveBtn);
            actions.appendChild(rejectBtn);

            item.appendChild(text);
            item.appendChild(actions);

            approvalsList.appendChild(item);
        });

    } catch (error) {
        approvalsList.innerHTML =
            `<p class="error">${escapeHtml(error.message)}</p>`;
    }
}


async function handleApproval(approvalId, approve) {
    try {
        await apiRequest(`/approvals/${approvalId}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                approve: approve
            })
        });

        await loadApprovals();
        await loadTickets();

        addMessage(
            "assistant",
            approve
                ? "The requested action was approved."
                : "The requested action was rejected."
        );

    } catch (error) {
        addMessage(
            "assistant",
            `Approval error: ${error.message}`
        );
    }
}


async function loadStatus() {
    try {
        const response = await fetch("/status");
        const data = await response.json();

        apiStatus.textContent = "Online";
        environment.textContent = data.environment || "-";
        llmProvider.textContent = data.llm_provider || "-";

    } catch (error) {
        apiStatus.textContent = "Unavailable";
    }
}


refreshTickets.addEventListener("click", loadTickets);
refreshApprovals.addEventListener("click", loadApprovals);


function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}