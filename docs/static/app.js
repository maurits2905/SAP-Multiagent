const chatEl = document.getElementById("chat");
const inputEl = document.getElementById("input");
const debugEl = document.getElementById("debug");
const sendBtn = document.getElementById("send");
const clearBtn = document.getElementById("clear");

let history = [];

function addMsg(role, content) {
    const div = document.createElement("div");
    div.className = "msg";
    div.innerHTML = `<span class="role">${role}:</span> <span>${escapeHtml(content)}</span>`;
    chatEl.appendChild(div);
    chatEl.scrollTop = chatEl.scrollHeight;
}

function escapeHtml(str) {
    return str.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

async function send() {
    const msg = inputEl.value.trim();
    if (!msg) return;

    addMsg("User", msg);
    history.push({ role: "user", content: msg });
    inputEl.value = "";

    const res = await fetch("/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: msg, history })
    });

    const data = await res.json();
    addMsg("SAP AI", data.answer);
    history.push({ role: "assistant", content: data.answer });

    debugEl.textContent = JSON.stringify(data.debug, null, 2);
}

sendBtn.addEventListener("click", send);
clearBtn.addEventListener("click", () => {
    history = [];
    chatEl.innerHTML = "";
    debugEl.textContent = "";
});
inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send();
});
