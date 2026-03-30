// =====================
// CSRF TOKEN HANDLING
// =====================
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute("content");
}

// =====================
// LOGIN
// =====================
const loginForm = document.getElementById("loginForm");
const loginNotice = document.getElementById("loginNotice");

if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const formData = new FormData(loginForm);

        try {
            const res = await fetch("/api/login", {
                method: "POST",
                headers: {
                    "X-CSRF-Token": getCSRFToken()
                },
                body: formData
            });

            const data = await res.json();

            if (data.ok) {
                loginNotice.innerText = "Login successful";
                // update CSRF token immediately
                document.querySelector('meta[name="csrf-token"]')
                    .setAttribute("content", data.csrf_token);
                location.reload();
            } else {
                loginNotice.innerText = data.error;
            }
        } catch (err) {
            loginNotice.innerText = "Login failed";
        }
    });
}

// =====================
// LOGOUT
// =====================
const logoutBtn = document.getElementById("logoutBtn");

if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
        try {
            await fetch("/api/logout", {
                method: "POST",
                headers: {
                    "X-CSRF-Token": getCSRFToken()
                }
            });
            location.reload();
        } catch (err) {
            console.error("Logout failed:", err);
        }
    });
}

// =====================
// CREATE POST
// =====================
const postForm = document.getElementById("postForm");
const formNotice = document.getElementById("formNotice");

if (postForm) {
    postForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const formData = new FormData(postForm);

        try {
            const res = await fetch("/api/posts", {
                method: "POST",
                headers: {
                    "X-CSRF-Token": getCSRFToken()
                },
                body: formData
            });

            const data = await res.json();

            if (data.ok) {
                formNotice.innerText = "Post created successfully";
                postForm.reset();
                loadPosts();
            } else {
                formNotice.innerText = data.error;
            }
        } catch (err) {
            formNotice.innerText = "Error creating post";
        }
    });
}

// =====================
// LOAD POSTS
// =====================
async function loadPosts() {
    const postList = document.getElementById("postList");
    if (!postList) return;

    try {
        const res = await fetch("/api/posts");
        const data = await res.json();

        postList.innerHTML = "";

        data.items.forEach(post => {
            const div = document.createElement("div");
            div.className = "post-item";

            const title = document.createElement("h3");
            title.textContent = post.title;
            div.appendChild(title);

            const deleteBtn = document.createElement("button");
            deleteBtn.setAttribute("data-id", post.id);
            deleteBtn.className = "deleteBtn";
            deleteBtn.textContent = "Delete";
            div.appendChild(deleteBtn);

            postList.appendChild(div);
        });

        attachDeleteHandlers();
    } catch (err) {
        console.error("Error loading posts:", err);
        postList.innerHTML = "<p>Error loading posts</p>";
    }
}

// =====================
// DELETE POST
// =====================
function attachDeleteHandlers() {
    document.querySelectorAll(".deleteBtn").forEach(btn => {
        btn.addEventListener("click", async () => {
            const id = btn.getAttribute("data-id");

            try {
                const res = await fetch(`/api/posts/${id}`, {
                    method: "DELETE",
                    headers: {
                        "X-CSRF-Token": getCSRFToken()
                    }
                });

                const data = await res.json();

                if (data.ok) {
                    loadPosts();
                } else {
                    alert(data.error);
                }
            } catch (err) {
                alert("Error deleting post");
            }
        });
    });
}

// =====================
// INIT
// =====================
window.addEventListener("DOMContentLoaded", () => {
    loadPosts();
});