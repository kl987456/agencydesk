# AgencyDesk architecture diagram

```mermaid
%%{init: {
  "theme": "base",
  "themeVariables": {
    "background": "#0b1020",
    "primaryColor": "#17213b",
    "primaryTextColor": "#f8fafc",
    "primaryBorderColor": "#64748b",
    "lineColor": "#94a3b8",
    "secondaryColor": "#111827",
    "tertiaryColor": "#1e293b",
    "clusterBkg": "#0f172a",
    "clusterBorder": "#475569",
    "fontFamily": "Inter, Arial, sans-serif"
  }
}}%%

flowchart LR
    U["Users<br/>Admin · Member · Client"]

    subgraph FE["FRONTEND — REACT + VITE"]
        Login["Login & Agency Context"]
        Work["Work Workspace"]
        Board["Project / Task Board"]
        Portal["Client Portal"]
        Detail["Task Detail"]
        IntakeUI["Intake Forms"]
        AutoUI["Automations"]
        CRMUI["Lightweight CRM"]
    end

    subgraph API["BACKEND — FASTAPI"]
        Auth["Authentication"]
        Context["Agency Context"]
        RBAC["Role Authorization"]
        ProjectAPI["Projects API"]
        TaskAPI["Tasks API"]
        CommentAPI["Comments API"]
        TimeAPI["Time Tracking API"]
        FileAPI["Files & Approval API"]
        DashAPI["Dashboard API"]
        InviteAPI["Invites API"]
        IntakeAPI["Intake API"]
        AutoAPI["Automation & Notification API"]
        CRMAPI["CRM API"]
    end

    subgraph SEC["TENANT SECURITY"]
        Scope["Agency-scoped queries"]
        Visibility["Client-visible filtering"]
        FK["Composite tenant-safe FKs"]
        RLS["PostgreSQL Row-Level Security"]
    end

    subgraph DB["POSTGRESQL DATABASE"]
        Identity[("Identities")]
        Membership[("Agency Memberships")]
        TenantData[("Agencies · Clients · Projects · Tasks")]
        Collaboration[("Comments · Time Entries")]
        FilesMeta[("File Metadata")]
        Bonus[("Intake · CRM · Automations")]
        Notifications[("Notifications")]
    end

    subgraph STORAGE["FILE STORAGE"]
        DevStorage["Local Storage<br/>Development"]
        ProdStorage["S3 / Azure Blob<br/>Production"]
    end

    subgraph QA["VERIFICATION"]
        Tests["Pytest Tests"]
        Browser["Browser E2E Checks"]
        Build["Frontend Production Build"]
    end

    U --> Login
    U --> Portal
    Login --> Auth
    Auth --> Context
    Context --> RBAC
    Work --> Board
    Board --> Detail
    Portal --> Board
    Detail --> CommentAPI
    Detail --> TimeAPI
    Detail --> FileAPI
    Work --> DashAPI
    Work --> InviteAPI
    IntakeUI --> IntakeAPI
    AutoUI --> AutoAPI
    CRMUI --> CRMAPI
    RBAC --> ProjectAPI
    RBAC --> TaskAPI
    RBAC --> CommentAPI
    RBAC --> TimeAPI
    RBAC --> FileAPI
    RBAC --> DashAPI
    RBAC --> InviteAPI
    Scope --> ProjectAPI
    Scope --> TaskAPI
    Scope --> CommentAPI
    Scope --> TimeAPI
    Scope --> FileAPI
    Scope --> DashAPI
    Scope --> IntakeAPI
    Scope --> AutoAPI
    Scope --> CRMAPI
    Visibility --> Portal
    FK --> DB
    RLS --> DB
    Auth --> Identity
    Context --> Membership
    ProjectAPI --> TenantData
    TaskAPI --> TenantData
    CommentAPI --> Collaboration
    TimeAPI --> Collaboration
    DashAPI --> TenantData
    DashAPI --> Collaboration
    FileAPI --> FilesMeta
    InviteAPI --> Membership
    IntakeAPI --> Bonus
    AutoAPI --> Bonus
    AutoAPI --> Notifications
    CRMAPI --> Bonus
    FileAPI --> DevStorage
    FileAPI -. production .-> ProdStorage
    Tests --> API
    Browser --> FE
    Build --> FE
```

## Presentation summary

The frontend sends requests to FastAPI. FastAPI resolves the identity, role, and active agency context before applying authorization and tenant-scoped filters. Client visibility is enforced for tasks, comments, files, and dashboards. Composite foreign keys and PostgreSQL Row-Level Security provide database-level tenant protection. Files use local storage in development and can move to S3 or Azure Blob Storage in production.
