# ⚡ BitsXBytes

### The Digital Home for College Technology Communities

<p align="center">
  <strong>Connect • Build • Learn • Collaborate • Grow</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-In%20Development-3B82F6?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Frontend-Next.js-black?style=for-the-badge&logo=next.js" />
  <img src="https://img.shields.io/badge/Backend-Django-092E20?style=for-the-badge&logo=django" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL-336791?style=for-the-badge&logo=postgresql" />
  <img src="https://img.shields.io/badge/Platform-PWA-5A0FC8?style=for-the-badge" />
</p>

---

## 🌐 What is BitsXBytes?

**BitsXBytes (BxB)** is a technology-focused social and collaboration platform designed for college students.

It brings together the fragmented parts of a college technology ecosystem into one place:

```text
             ┌─────────────────────────┐
             │       BITSXBYTES        │
             │      College Tech       │
             │       Ecosystem         │
             └────────────┬────────────┘
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
   👥 PEOPLE          🚀 PROJECTS        🧠 LEARNING
       │                  │                  │
       ▼                  ▼                  ▼
   🤝 TEAMS           💻 BUILDING       📚 DISCUSSIONS
       │                  │                  │
       └──────────────────┼──────────────────┘
                          ▼
                    🌐 COMMUNITY
```

BitsXBytes aims to make it easier for students to:

* Find people with similar interests
* Discover and join projects
* Build teams
* Participate in events and challenges
* Learn together
* Share technical work
* Discover opportunities
* Build a visible technical identity
* Connect with other students across their college ecosystem

---

# 🧭 The Problem

College students often use multiple disconnected platforms.

```text
       ┌──────────────┐
       │   Instagram  │
       │ Entertainment│
       └──────┬───────┘
              │
       ┌──────▼───────┐
       │   LinkedIn   │
       │ Professional │
       └──────┬───────┘
              │
       ┌──────▼───────┐
       │    GitHub    │
       │     Code     │
       └──────┬───────┘
              │
       ┌──────▼───────┐
       │   Discord    │
       │   Community  │
       └──────┬───────┘
              │
              ▼
       Fragmented Student
          Experience
```

The problem isn't the lack of platforms.

The problem is **fragmentation**.

Students need a place where their:

> **people + projects + skills + learning + events + collaboration**

can exist inside one connected ecosystem.

---

# 💡 The BitsXBytes Idea

Instead of creating another static college website, BitsXBytes is being designed as a **student technology network**.

```text
                       BITSXBYTES
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
      DISCOVER           BUILD             LEARN
         │                 │                 │
         ▼                 ▼                 ▼
       PEOPLE          PROJECTS          DISCUSSIONS
       SKILLS             │             RESOURCES
       TEAMS              ▼             CHALLENGES
       EVENTS           TEAMS
         │                 │                 │
         └─────────────────┼─────────────────┘
                           ▼
                       CONNECT
                           │
                           ▼
                      COLLABORATE
                           │
                           ▼
                       CREATE
                           │
                           ▼
                       DISCOVER
```

This creates a continuous community loop:

### 🔄 Discover → Participate → Connect → Create → Get Recognized → Discover

---

# 🎯 Core Product Areas

| Area             | Purpose                                          |
| ---------------- | ------------------------------------------------ |
| 👤 Profiles      | Build a technical identity                       |
| 👥 People        | Discover students with similar interests         |
| 🤝 Teams         | Find teammates for projects and competitions     |
| 🚀 Projects      | Showcase and collaborate on projects             |
| 🧠 Discussions   | Ask questions and exchange knowledge             |
| 📚 Learning      | Learn together through resources and communities |
| 🏆 Challenges    | Participate in technical challenges              |
| 📅 Events        | Discover and participate in events               |
| 🔔 Notifications | Stay updated with community activity             |
| 🔎 Search        | Find people, projects and opportunities          |

---

# 🏗️ System Architecture

```text
                         ┌─────────────────────┐
                         │       USER          │
                         │  Desktop / Mobile   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │       NEXT.JS PWA         │
                    │                           │
                    │  UI • Routing • State     │
                    │  Responsive Experience    │
                    └─────────────┬─────────────┘
                                  │
                              REST API
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │      DJANGO + DRF         │
                    │                           │
                    │ Authentication           │
                    │ Profiles                 │
                    │ Social Graph             │
                    │ Projects                 │
                    │ Teams                    │
                    │ Events                   │
                    │ Discussions              │
                    │ Notifications            │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │       POSTGRESQL          │
                    │                           │
                    │ Users                     │
                    │ Profiles                  │
                    │ Content                   │
                    │ Relationships             │
                    │ Events                    │
                    │ Projects                  │
                    └───────────────────────────┘
```

---

# 🧩 Technology Stack

## Frontend

```text
Next.js
   │
   ├── React
   ├── TypeScript
   ├── App Router
   ├── Tailwind CSS
   └── PWA
```

## Backend

```text
Django
   │
   ├── Django REST Framework
   ├── Authentication
   ├── REST APIs
   ├── Business Logic
   └── Application Services
```

## Database

```text
PostgreSQL
   │
   ├── Users
   ├── Profiles
   ├── Social Relationships
   ├── Projects
   ├── Teams
   ├── Events
   └── Community Data
```

---

# 🔐 Authentication Architecture

Authentication is being designed as an independent foundation of the platform.

The current web authentication flow uses Django REST Framework and SimpleJWT.
Login returns a short-lived access token to the frontend, where it is kept in
memory only. The refresh token is issued only as the `bxb_refresh` HttpOnly
cookie; it is never returned in JSON or stored in browser storage. Reloading
the app refreshes the access token through that cookie. Registration, login,
refresh, and logout require a CSRF token from `/api/auth/csrf/` and send it in
the `X-CSRFToken` header. Email verification and resend requests use the same
CSRF protection. Refresh rotates and blacklists old refresh tokens; logout
blacklists the cookie token and expires the cookie.

The frontend and API use credentialed CORS with explicit allowed origins. Keep
them on the same site and use `AUTH_COOKIE_SAMESITE=Lax` where possible. For a
cross-site deployment, set `AUTH_COOKIE_SAMESITE=None`, serve both origins over
HTTPS, and configure the exact frontend origin in both `CORS_ALLOWED_ORIGINS`
and `CSRF_TRUSTED_ORIGINS`. The refresh cookie is Secure whenever Django
`DEBUG` is disabled.

Password reset requests always return the same response. For an active account
with a usable password, Django sends a reset link to the configured frontend
using its expiring, single-use password-reset token. The reset page submits the
UID, token, and confirmed new password to the API. Django applies the configured
password validators, consumes the token by updating the password, blacklists
the account's outstanding refresh tokens, and expires the browser's refresh
cookie. Access tokens are bound to a keyed password-version fingerprint, so
tokens issued before a password reset are rejected immediately. In development,
reset emails are written only to the local Django console; production should
configure SMTP credentials through environment variables.

New registrations start unverified and receive a signed email link that expires
after `EMAIL_VERIFICATION_TIMEOUT` seconds (24 hours by default). Verification
is required before login or authenticated API access; existing accounts remain
verified during the migration. The resend endpoint returns a generic response,
limits each account to one send per `EMAIL_VERIFICATION_RESEND_INTERVAL`
seconds, and also applies an IP-based DRF throttle. Development uses Django's
console email backend, so verification links appear in the backend terminal.

```text
                    AUTHENTICATION
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
       EMAIL             GOOGLE           GITHUB
      PASSWORD           OAuth             OAuth
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                     BXB USER ACCOUNT
                           │
                           ▼
                       PROFILE
                           │
                           ▼
                       ONBOARDING
                           │
                           ▼
                     BXB COMMUNITY
```

A single BxB account can eventually connect multiple authentication identities.

---

# 👤 User Journey

```text
┌──────────┐
│   JOIN   │
└────┬─────┘
     ▼
┌──────────────┐
│ AUTHENTICATE │
└──────┬───────┘
       ▼
┌──────────────┐
│ CREATE       │
│ PROFILE      │
└──────┬───────┘
       ▼
┌──────────────┐
│ SELECT       │
│ INTERESTS    │
└──────┬───────┘
       ▼
┌──────────────┐
│ DISCOVER     │
│ COMMUNITY    │
└──────┬───────┘
       ▼
┌─────────────────────────┐
│ PEOPLE • PROJECTS •     │
│ TEAMS • EVENTS •        │
│ DISCUSSIONS             │
└───────────┬─────────────┘
            ▼
       PARTICIPATE
            │
            ▼
         CREATE
            │
            ▼
        CONNECT
```

---

# 🧱 Backend Architecture

The backend is organized around independent Django applications.

```text
backend/
│
├── config/
│
├── users/
├── profiles/
├── social/
├── feed/
├── posts/
├── communities/
├── discussions/
├── projects/
├── teams/
├── events/
├── challenges/
├── gamification/
├── notifications/
├── search/
├── moderation/
└── analytics/
```

This modular architecture allows individual product areas to evolve independently.

---

# 🗃️ Data Model — High Level

```text
                         ┌──────────┐
                         │   USER   │
                         └────┬─────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
             PROFILE       IDENTITY       SESSION
                │
      ┌─────────┼──────────┐
      │         │          │
      ▼         ▼          ▼
   SKILLS   INTERESTS   EDUCATION
      │
      ▼
   PROJECTS
      │
      ▼
    TEAMS
      │
      ▼
   COMMUNITY
```

---

# 📱 PWA First

BitsXBytes is being developed as a **Progressive Web App**.

The goal is to provide:

```text
                 BITSXBYTES
                     │
          ┌──────────┴──────────┐
          │                     │
       DESKTOP                MOBILE
          │                     │
          └──────────┬──────────┘
                     ▼
```
