import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "/api";
async function api(path, options = {}) {
  const token = localStorage.getItem("agencydesk_token");
  const headers = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.body instanceof FormData
      ? {}
      : { "Content-Type": "application/json" }),
    ...(options.headers || {}),
  };
  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (!response.ok) {
    const payload = await response
      .json()
      .catch(() => ({ detail: "Request failed" }));
    const detail =
      typeof payload.detail === "string"
        ? payload.detail
        : payload.detail?.message
          ? `${payload.detail.message}: ${payload.detail.task_ids?.join(", ") || ""}`
          : JSON.stringify(payload.detail);
    if (response.status === 401) {
      localStorage.clear();
      window.location.reload();
    }
    throw new Error(detail || "Request failed");
  }
  return response.json();
}

function Login({ onLogin }) {
  const [email, setEmail] = useState("admin@northstar.test");
  const [password, setPassword] = useState("AgencyDesk123!");
  const [agency, setAgency] = useState("");
  const [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault();
    try {
      const data = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password, agency_id: agency || null }),
      });
      localStorage.setItem("agencydesk_token", data.token);
      localStorage.setItem(
        "agencydesk_memberships",
        JSON.stringify(data.memberships),
      );
      onLogin(data);
    } catch (err) {
      setError(err.message);
    }
  }
  return (
    <main className="auth">
      <section className="card">
        <div className="eyebrow">AGENCYDESK</div>
        <h1>Work stays in its lane.</h1>
        <p className="muted">Sign in to an agency-scoped workspace.</p>
        <form onSubmit={submit}>
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <label>
            Agency context
            <input
              placeholder="Optional agency UUID for shared identities"
              value={agency}
              onChange={(e) => setAgency(e.target.value)}
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button>Sign in</button>
        </form>
      </section>
    </main>
  );
}

function App() {
  const memberships = JSON.parse(
    localStorage.getItem("agencydesk_memberships") || "[]",
  );
  const role = memberships[0]?.role || "";
  const isClient = role === "client_user";
  const isAdmin = role === "agency_admin";
  const [session, setSession] = useState(null);
  const [view, setView] = useState("work");
  const [projects, setProjects] = useState([]);
  const [selected, setSelected] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [comments, setComments] = useState([]);
  const [attachments, setAttachments] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [members, setMembers] = useState([]);
  const [search, setSearch] = useState("");
  const [comment, setComment] = useState("");
  const [minutes, setMinutes] = useState("");
  const [note, setNote] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [crm, setCrm] = useState({ leads: [], deals: [], contracts: [] });
  const [forms, setForms] = useState([]);
  const [automations, setAutomations] = useState([]);
  const [crmName, setCrmName] = useState("");
  const [crmEmail, setCrmEmail] = useState("");
  const [formName, setFormName] = useState("");
  const [responseText, setResponseText] = useState("");
  const [notifications, setNotifications] = useState([]);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDescription, setTaskDescription] = useState("");
  const [taskVisibility, setTaskVisibility] = useState(false);

  async function loadTasks(project, query = "") {
    setTasks(
      await api(
        `/projects/${project.id}/tasks${query ? `?q=${encodeURIComponent(query)}` : ""}`,
      ),
    );
  }
  async function loadProjects() {
    try {
      setError("");
      const list = await api("/projects");
      setProjects(list);
      if (list[0]) {
        setSelected(list[0]);
        await loadTasks(list[0]);
        setDashboard(await api(`/projects/${list[0].id}/dashboard`));
        if (isAdmin) setMembers(await api(`/projects/${list[0].id}/members`));
      }
    } catch (err) {
      setError(err.message);
    }
  }
  async function loadCrm() {
    if (!isClient)
      setCrm({
        leads: await api("/crm/leads"),
        deals: await api("/crm/deals"),
        contracts: await api("/crm/contracts"),
      });
  }
  async function loadForms() {
    setForms(await api("/intake/forms"));
  }
  async function loadAutomationData() {
    if (isAdmin) setAutomations(await api("/automations"));
  }
  async function loadNotifications() {
    setNotifications(await api("/notifications"));
  }
  async function chooseProject(project) {
    setSelected(project);
    setSelectedTask(null);
    setTasks(await api(`/projects/${project.id}/tasks`));
    setDashboard(await api(`/projects/${project.id}/dashboard`));
    if (isAdmin) setMembers(await api(`/projects/${project.id}/members`));
  }
  async function chooseTask(task) {
    try {
      setSelectedTask(task);
      setComments(await api(`/tasks/${task.id}/comments`));
      setAttachments(await api(`/tasks/${task.id}/attachments`));
    } catch (err) {
      setError(err.message);
    }
  }
  useEffect(() => {
    if (localStorage.getItem("agencydesk_token")) {
      loadProjects();
      loadForms();
      loadCrm();
      loadAutomationData();
      loadNotifications();
    }
  }, []);
  async function switchAgency(event) {
    try {
      const data = await api("/auth/switch", {
        method: "POST",
        body: JSON.stringify({ agency_id: event.target.value }),
      });
      localStorage.setItem("agencydesk_token", data.token);
      localStorage.setItem(
        "agencydesk_memberships",
        JSON.stringify(data.memberships),
      );
      setSession(data);
      location.reload();
    } catch (err) {
      setError(err.message);
    }
  }
  async function addComment(event) {
    event.preventDefault();
    try {
      await api(`/tasks/${selectedTask.id}/comments`, {
        method: "POST",
        body: JSON.stringify({ body: comment, is_client_visible: isClient }),
      });
      setComment("");
      await chooseTask(selectedTask);
      setMessage("Comment added");
    } catch (err) {
      setError(err.message);
    }
  }
  async function addTime(event) {
    event.preventDefault();
    try {
      await api(`/tasks/${selectedTask.id}/time`, {
        method: "POST",
        body: JSON.stringify({
          minutes: Number(minutes),
          note,
          work_date: new Date().toISOString().slice(0, 10),
        }),
      });
      setMinutes("");
      setNote("");
      setMessage("Time entry logged");
      if (selected)
        setDashboard(await api(`/projects/${selected.id}/dashboard`));
    } catch (err) {
      setError(err.message);
    }
  }
  async function upload(event) {
    event.preventDefault();
    try {
      await api(`/tasks/${selectedTask.id}/attachments`, {
        method: "POST",
        body: new FormData(event.currentTarget),
      });
      event.currentTarget.reset();
      await chooseTask(selectedTask);
      setMessage("File uploaded");
    } catch (err) {
      setError(err.message);
    }
  }
  async function approve(token, status) {
    try {
      await api(`/files/${token}/approval?status=${status}`, {
        method: "POST",
      });
      await chooseTask(selectedTask);
      setMessage(`File marked ${status}`);
    } catch (err) {
      setError(err.message);
    }
  }
  async function invite(event) {
    event.preventDefault();
    try {
      const data = await api("/invites", {
        method: "POST",
        body: JSON.stringify({
          email: inviteEmail,
          client_id: selected.client_id,
        }),
      });
      setInviteEmail("");
      setMessage(`Invite ready: ${data.token}`);
    } catch (err) {
      setError(err.message);
    }
  }
  async function removeMember(id) {
    try {
      await api(`/projects/${selected.id}/members/${id}/remove`, {
        method: "POST",
      });
      setMessage("Member removed");
      setMembers(await api(`/projects/${selected.id}/members`));
    } catch (err) {
      setError(err.message);
    }
  }
  async function addLead(event) {
    event.preventDefault();
    try {
      await api("/crm/leads", {
        method: "POST",
        body: JSON.stringify({ name: crmName, email: crmEmail }),
      });
      setCrmName("");
      setCrmEmail("");
      await loadCrm();
      setMessage("Lead created");
    } catch (err) {
      setError(err.message);
    }
  }
  async function addDeal(event) {
    event.preventDefault();
    try {
      await api("/crm/deals", {
        method: "POST",
        body: JSON.stringify({ name: crmName, value_cents: 0 }),
      });
      setCrmName("");
      await loadCrm();
      setMessage("Deal created");
    } catch (err) {
      setError(err.message);
    }
  }
  async function addContract(event) {
    event.preventDefault();
    try {
      await api("/crm/contracts", {
        method: "POST",
        body: JSON.stringify({ title: crmName }),
      });
      setCrmName("");
      await loadCrm();
      setMessage("Contract created");
    } catch (err) {
      setError(err.message);
    }
  }
  async function addForm(event) {
    event.preventDefault();
    try {
      await api("/intake/forms", {
        method: "POST",
        body: JSON.stringify({
          name: formName,
          client_id: selected?.client_id,
          fields: [{ name: "request", label: "How can we help?" }],
        }),
      });
      setFormName("");
      await loadForms();
      setMessage("Intake form created");
    } catch (err) {
      setError(err.message);
    }
  }
  async function submitResponse(event, form) {
    event.preventDefault();
    try {
      await api(`/intake/forms/${form.id}/responses`, {
        method: "POST",
        body: JSON.stringify({ response: responseText }),
      });
      setResponseText("");
      setMessage("Intake response submitted");
    } catch (err) {
      setError(err.message);
    }
  }
  async function addAutomation(event) {
    event.preventDefault();
    try {
      await api("/automations", {
        method: "POST",
        body: JSON.stringify({
          name: crmName,
          event_type: "task.created",
          action_type: "notify",
        }),
      });
      setCrmName("");
      await loadAutomationData();
      setMessage("Automation created");
    } catch (err) {
      setError(err.message);
    }
  }
  async function addTask(event) {
    event.preventDefault();
    try {
      await api(`/projects/${selected.id}/tasks`, {
        method: "POST",
        body: JSON.stringify({
          title: taskTitle,
          description: taskDescription,
          is_client_visible: taskVisibility,
        }),
      });
      setTaskTitle("");
      setTaskDescription("");
      setTaskVisibility(false);
      await chooseProject(selected);
      setMessage("Task created");
    } catch (err) {
      setError(err.message);
    }
  }
  async function updateStatus(event) {
    try {
      const updated = await api(`/tasks/${selectedTask.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: selectedTask.title,
          description: selectedTask.description,
          status: event.target.value,
          priority: selectedTask.priority,
          due_date: selectedTask.due_date,
          is_client_visible: selectedTask.is_client_visible,
          assignee_membership_id: selectedTask.assignee_membership_id || null,
        }),
      });
      setSelectedTask(updated);
      await loadTasks(selected, search);
      setMessage("Task status updated");
    } catch (err) {
      setError(err.message);
    }
  }
  async function moveTask(taskId, status) {
    const task = tasks.find((item) => item.id === taskId);
    if (!task || task.status === status) return;
    try {
      await api(`/tasks/${task.id}`, { method: "PATCH", body: JSON.stringify({ title: task.title, description: task.description, status, priority: task.priority, due_date: task.due_date, is_client_visible: task.is_client_visible, assignee_membership_id: task.assignee_membership_id || null }) });
      await loadTasks(selected, search);
      setMessage("Task moved");
    } catch (err) { setError(err.message); }
  }

  if (!session && !localStorage.getItem("agencydesk_token"))
    return (
      <Login
        onLogin={(data) => {
          setSession(data);
          loadProjects();
        }}
      />
    );
  return (
    <div className="app">
      <header>
        <div>
          <div className="eyebrow">AGENCYDESK</div>
          <h2>Client work, scoped by design</h2>
        </div>
        <div className="header-actions">
          <button
            className={view === "work" ? "" : "secondary"}
            onClick={() => setView("work")}
          >
            Work
          </button>
          {!isClient && (
            <button
              className={view === "crm" ? "" : "secondary"}
              onClick={() => {
                setView("crm");
                loadCrm();
              }}
            >
              CRM
            </button>
          )}
          <button
            className={view === "intake" ? "" : "secondary"}
            onClick={() => {
              setView("intake");
              loadForms();
            }}
          >
            Intake
          </button>
          {isAdmin && (
            <button
              className={view === "automations" ? "" : "secondary"}
              onClick={() => {
                setView("automations");
                loadAutomationData();
              }}
            >
              Automations
            </button>
          )}
          {memberships.length > 1 && (
            <select
              className="context"
              value={memberships[0].agency_id}
              onChange={switchAgency}
            >
              {memberships.map((m) => (
                <option key={m.agency_id} value={m.agency_id}>
                  {m.agency_id.slice(0, 8)} · {m.role}
                </option>
              ))}
            </select>
          )}
          <span className="pill">{role}</span>
          <button
            className="secondary"
            onClick={() => {
              localStorage.clear();
              location.reload();
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      {view === "work" ? (
        <main className="layout">
          <aside>
            <div className="section-label">PROJECTS</div>
            {projects.map((project) => (
              <button
                className={
                  selected?.id === project.id ? "project active" : "project"
                }
                key={project.id}
                onClick={() => chooseProject(project)}
              >
                <strong>{project.name}</strong>
                <small>{project.description || "No description"}</small>
              </button>
            ))}
          </aside>
          <section className="content">
            {error && <div className="error banner">{error}</div>}
            {message && <div className="success banner">{message}</div>}
            {selected ? (
              <>
                <div className="content-head">
                  <div>
                    <div className="eyebrow">PROJECT BOARD</div>
                    <h1>{selected.name}</h1>
                    <p className="muted">
                      {isClient
                        ? "Client-visible data only is requested from the API."
                        : "Agency-scoped work with internal visibility badges."}
                    </p>
                  </div>
                  <button onClick={loadProjects}>Refresh</button>
                </div>
                {dashboard && (
                  <div className="dashboard">
                    <strong>Dashboard</strong>
                    <span>
                      {Object.entries(dashboard.task_counts)
                        .map(([status, count]) => `${status}: ${count}`)
                        .join(" · ") || "No tasks"}
                    </span>
                    <span>{dashboard.hours_logged} hours logged</span>
                  </div>
                )}
                {!isClient && (
                  <section className="create-task card">
                    <strong>Create task</strong>
                    <form className="inline-form" onSubmit={addTask}>
                      <input required placeholder="Task title" value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} />
                      <input placeholder="Description" value={taskDescription} onChange={(e) => setTaskDescription(e.target.value)} />
                      <label className="check"><input type="checkbox" checked={taskVisibility} onChange={(e) => setTaskVisibility(e.target.checked)} /> Client visible</label>
                      <button>Create</button>
                    </form>
                  </section>
                )}
                {isAdmin && (
                  <section className="admin-tools">
                    <strong>Agency tools</strong>
                    <form className="inline-form" onSubmit={invite}>
                      <input
                        required
                        type="email"
                        placeholder="Invite client email"
                        value={inviteEmail}
                        onChange={(e) => setInviteEmail(e.target.value)}
                      />
                      <button>Invite / resend</button>
                    </form>
                    {members.map((member) => (
                      <div className="file" key={member.membership_id}>
                        <span>
                          {member.display_name} · {member.email}
                        </span>
                        <button
                          className="secondary"
                          onClick={() => removeMember(member.membership_id)}
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </section>
                )}
                <div className="toolbar">
                  <input
                    placeholder="Search visible tasks"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    onKeyDown={(e) =>
                      e.key === "Enter" && loadTasks(selected, search)
                    }
                  />
                  <button onClick={() => loadTasks(selected, search)}>
                    Search
                  </button>
                </div>
                <div className="board">
                  {["todo", "in_progress", "review", "done"].map((status) => (
                    <div className="column" key={status} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); moveTask(event.dataTransfer.getData("taskId"), status); }}>
                      <div className="column-title">
                        <span>{status.replace("_", " ")}</span>
                        <span className="count">
                          {
                            tasks.filter((task) => task.status === status)
                              .length
                          }
                        </span>
                      </div>
                      {tasks
                        .filter((task) => task.status === status)
                        .map((task) => (
                          <article
                            className="task"
                            key={task.id}
                            draggable={!isClient}
                            onDragStart={(event) => event.dataTransfer.setData("taskId", task.id)}
                            onClick={() => chooseTask(task)}
                          >
                            <div className="task-top">
                              <span
                                className={
                                  task.is_client_visible
                                    ? "badge visible"
                                    : "badge internal"
                                }
                              >
                                {task.is_client_visible
                                  ? "CLIENT VISIBLE"
                                  : "INTERNAL"}
                              </span>
                              <span className="priority">{task.priority}</span>
                            </div>
                            <h3>{task.title}</h3>
                            <p>{task.description}</p>
                            <button
                              className="link"
                              onClick={(e) => {
                                e.stopPropagation();
                                chooseTask(task);
                              }}
                            >
                              Open detail
                            </button>
                          </article>
                        ))}
                    </div>
                  ))}
                </div>
                {selectedTask && (
                  <section className="detail">
                    <div className="detail-head">
                      <div>
                        <div className="eyebrow">TASK DETAIL</div>
                        <h2>{selectedTask.title}</h2>
                      </div>
                      <button
                        className="secondary"
                        onClick={() => setSelectedTask(null)}
                      >
                        Close
                      </button>
                    </div>
                    <p>{selectedTask.description}</p>
                    {!isClient && (
                      <label className="status-control">Status
                        <select value={selectedTask.status} onChange={updateStatus}>
                          <option value="todo">Todo</option><option value="in_progress">In progress</option><option value="review">Review</option><option value="done">Done</option>
                        </select>
                      </label>
                    )}
                    <h3>Visible comments</h3>
                    {comments.map((item) => (
                      <p className="comment" key={item.id}>
                        {item.body}
                      </p>
                    ))}
                    <form className="inline-form" onSubmit={addComment}>
                      <input
                        required
                        placeholder="Add a comment"
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                      />
                      <button>Comment</button>
                    </form>
                    {!isClient && (
                      <>
                        <h3>Log time</h3>
                        <form className="inline-form" onSubmit={addTime}>
                          <input
                            required
                            type="number"
                            min="1"
                            placeholder="Minutes"
                            value={minutes}
                            onChange={(e) => setMinutes(e.target.value)}
                          />
                          <input
                            placeholder="Note"
                            value={note}
                            onChange={(e) => setNote(e.target.value)}
                          />
                          <button>Log</button>
                        </form>
                        <h3>Upload file</h3>
                        <form className="inline-form" onSubmit={upload}>
                          <input required type="file" name="upload" />
                          <label className="check">
                            <input
                              type="checkbox"
                              name="is_client_visible"
                              value="true"
                            />{" "}
                            Client visible
                          </label>
                          <button>Upload</button>
                        </form>
                      </>
                    )}
                    {attachments.length > 0 && (
                      <>
                        <h3>Files</h3>
                        {attachments.map((file) => (
                          <div className="file" key={file.external_token}>
                            <span>
                              {file.original_name} · {file.approval_status}
                            </span>
                            {isClient && (
                              <>
                                <button
                                  onClick={() =>
                                    approve(file.external_token, "approved")
                                  }
                                >
                                  Approve
                                </button>
                                <button
                                  className="secondary"
                                  onClick={() =>
                                    approve(
                                      file.external_token,
                                      "needs_changes",
                                    )
                                  }
                                >
                                  Needs changes
                                </button>
                              </>
                            )}
                          </div>
                        ))}
                      </>
                    )}
                  </section>
                )}
              </>
            ) : (
              <div className="empty">
                No projects are available in this agency context.
              </div>
            )}
          </section>
        </main>
      ) : (
        <main className="content standalone">
          {error && <div className="error banner">{error}</div>}
          {message && <div className="success banner">{message}</div>}
          {view === "crm" && (
            <>
              <h1>CRM</h1>
              <p className="muted">
                Agency-only leads, deals, and contracts. Client users cannot
                access this surface.
              </p>
              <div className="crm-grid">
                <section className="card">
                  <h3>Leads</h3>
                  <form onSubmit={addLead}>
                    <input
                      required
                      placeholder="Lead name"
                      value={crmName}
                      onChange={(e) => setCrmName(e.target.value)}
                    />
                    <input
                      placeholder="Email"
                      value={crmEmail}
                      onChange={(e) => setCrmEmail(e.target.value)}
                    />
                    <button>Create lead</button>
                  </form>
                  {crm.leads.map((row) => (
                    <p className="comment" key={row.id}>
                      {row.name} · {row.email} · {row.status}
                    </p>
                  ))}
                </section>
                <section className="card">
                  <h3>Deals</h3>
                  <form onSubmit={addDeal}>
                    <input
                      required
                      placeholder="Deal name"
                      value={crmName}
                      onChange={(e) => setCrmName(e.target.value)}
                    />
                    <button>Create deal</button>
                  </form>
                  {crm.deals.map((row) => (
                    <p className="comment" key={row.id}>
                      {row.name} · {row.status}
                    </p>
                  ))}
                </section>
                <section className="card">
                  <h3>Contracts</h3>
                  <form onSubmit={addContract}>
                    <input
                      required
                      placeholder="Contract title"
                      value={crmName}
                      onChange={(e) => setCrmName(e.target.value)}
                    />
                    <button>Create contract</button>
                  </form>
                  {crm.contracts.map((row) => (
                    <p className="comment" key={row.id}>
                      {row.title} · {row.status}
                    </p>
                  ))}
                </section>
              </div>
            </>
          )}
          {view === "intake" && (
            <>
              <h1>Client intake forms</h1>
              {isAdmin && (
                <form className="toolbar" onSubmit={addForm}>
                  <input
                    required
                    placeholder="New form name"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                  />
                  <button>Create form for selected client</button>
                </form>
              )}
              {forms.map((form) => (
                <section className="card" key={form.id}>
                  <h3>{form.name}</h3>
                  <p className="muted">
                    {form.fields?.[0]?.label || "Request details"}
                  </p>
                  {isClient && (
                    <form onSubmit={(e) => submitResponse(e, form)}>
                      <textarea
                        required
                        placeholder="Your response"
                        value={responseText}
                        onChange={(e) => setResponseText(e.target.value)}
                      />
                      <button>Submit intake</button>
                    </form>
                  )}
                </section>
              ))}
            </>
          )}
          {view === "automations" && (
            <>
              <h1>Automations & notifications</h1>
              <form className="toolbar" onSubmit={addAutomation}>
                <input
                  required
                  placeholder="Automation name"
                  value={crmName}
                  onChange={(e) => setCrmName(e.target.value)}
                />
                <button>Create notify automation</button>
              </form>
              {automations.map((row) => (
                <p className="comment" key={row.id}>
                  {row.name} · when {row.event_type} → {row.action_type} ·{" "}
                  {row.active ? "active" : "paused"}
                </p>
              ))}
              <h2>Notifications</h2>
              {notifications.length === 0 ? <p className="muted">No notifications yet.</p> : notifications.map((row) => <p className="comment" key={row.id}>{row.message}</p>)}
            </>
          )}
        </main>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
