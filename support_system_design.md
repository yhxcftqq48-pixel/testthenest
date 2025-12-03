# Support-Ticket-System Entwurf

## 1. Kontext & Ziel
- **Problemraum:** Zentraler Kanal, um Supportanfragen strukturiert aufzunehmen, zu priorisieren und nachzuverfolgen.
- **Abgrenzung:** Keine Wissensdatenbank, kein Chatbot. Fokus auf Ticket-Lifecycle (Anlage, Kommunikation, Abschluss) und einfache Dateianhänge.
- **Annahmen:**
  - Authentifizierte Nutzerinnen; Single-Sign-On via bestehenden IdP.
  - E-Mail-Benachrichtigungen werden extern bereitgestellt (Webhook/SMTP).
  - Dateianhänge werden in Object Storage (z. B. S3 kompatibel) verwaltet.
  - DSGVO: Daten bleiben in EU-Region; Löschkonzept erforderlich.
  - **Architektur-Startpunkt:** Monolith (Django + SPA/SSR-Frontend), API-first gestaltet, sodass spätere Module/Services per REST angebunden werden können.

## 2. Rollen & Berechtigungen
- **Nutzerin (Customer):** Tickets erstellen, eigenen Status/Verlauf sehen, Kommentare/Antworten geben, Anhänge hinzufügen, Ticket schließen anfragen.
- **Fachperson/Support:** Allen Tickets zugeordnet, Filter/Suche, kommentieren, Status ändern, Anhänge ansehen, Ticket abschließen.
- **Admin:** User-/Rollenverwaltung, SLA/Queue-Settings, systemweite Audit- und Löschvorgaben; kann Tickets neu zuordnen und wiederöffnen.
- **Berechtigungen:** JWT/OAuth2 Bearer Token. Ticketzugriff nach Rolle und Ownership; Feld-Level: Statusänderungen nur durch Support/Admin.

## 3. User Stories
- **Ticket erstellen:** Als Nutzerin möchte ich ein Ticket mit Kategorie, Priorität und Beschreibung anlegen, um Unterstützung zu bekommen.
- **Status einsehen:** Als Nutzerin möchte ich den Fortschritt und die letzten Kommentare sehen, um informiert zu bleiben.
- **Rückfragen beantworten:** Als Nutzerin möchte ich auf Rückfragen des Supports antworten und Dateien anhängen, damit das Ticket gelöst werden kann.
- **Abschluss bestätigen:** Als Nutzerin möchte ich ein Ticket als erledigt markieren oder eine Wiedereröffnung anstoßen.
- **Eingang sichten:** Als Fachperson möchte ich neue Tickets nach Priorität/Queue sehen, um sie zeitnah zu übernehmen.
- **Bearbeiten:** Als Fachperson möchte ich Kommentare hinterlassen, Status anpassen und interne Notizen pflegen, um den Fortschritt zu dokumentieren.
- **Abschließen:** Als Fachperson möchte ich Tickets abschließen und einen Lösungstext hinterlegen.
- **Administration:** Als Admin möchte ich SLAs/Kategorien pflegen und Tickets umhängen, um den Betrieb sicherzustellen.

## 4. UI-Flows (Low-Fi)
- **Nutzerin:**
  1. Dashboard → "Neues Ticket" → Formular (Kategorie, Priorität, Betreff, Beschreibung, Anhang) → Ticket-ID & Bestätigung.
  2. Ticket-Detail → Verlauf (Kommentare, Statushistorie) → neue Antwort/Anhang → Status zeigt "Offen", "In Bearbeitung", "Warten auf Nutzerin", "Gelöst".
  3. E-Mail/Inbox → Antwort-Link → öffnet Ticket-Detail → Nutzerin gibt Antwort ab.
- **Fachperson:**
  1. Queue-Übersicht → Filter (Status, Kategorie, Priorität, SLA-Fälligkeit) → Ticket-Detail.
  2. Ticket-Detail → Kommentar (öffentlich oder intern), Statusupdate, Zuweisung an Person/Team, Anhänge einsehen.
  3. Abschluss → Lösungstext → Status "Gelöst" oder "Geschlossen" → automatische Benachrichtigung an Nutzerin.

## 5. REST-API Entwurf
- **Ressourcen:** `tickets`, `comments`, `attachments`.
- **Endpunkte (Beispiele):**
  - `POST /api/tickets` – Ticket anlegen (Auth: Nutzerin/Admin/Support).
  - `GET /api/tickets` – List mit Filter (Status, Priorität, Kategorie, assignee, created_at, search).
  - `GET /api/tickets/{id}` – Ticket-Detail inkl. Kommentarpaginierung.
  - `PATCH /api/tickets/{id}` – Felder wie `status`, `assignee`, `priority`, `category` (nur Support/Admin) oder `subject`, `description` (Owner).
  - `POST /api/tickets/{id}/comments` – Kommentar anlegen (Typ: öffentlich/intern; intern nur Support/Admin sichtbar).
  - `POST /api/tickets/{id}/attachments` – Upload; Response enthält `attachment_id`, `url`, `content_type`, `size`.
  - `GET /api/tickets/{id}/attachments` – Liste der Anhänge (sichtbar gemäß Kommentar-Typ/Owner).
  - `POST /api/tickets/{id}/close` – Abschluss durch Support/Admin; optional `resolution_text`.
- **Payload Beispiele:**
  - Ticket anlegen:
    ```json
    {"subject": "VPN Problem", "description": "Kein Login möglich", "priority": "high", "category": "it", "attachments": ["upload-token-123"]}
    ```
  - Kommentar:
    ```json
    {"body": "Bitte Logfile anhängen", "visibility": "public"}
    ```
- **Fehlercodes:** `400` Validation, `401` Auth fehlt, `403` keine Rechte (z. B. interner Kommentar von Nutzerin), `404` Ticket/Attachment nicht gefunden, `409` Statuskonflikt (z. B. Abschluss eines schon geschlossenen Tickets).
- **AuthZ:** Rollenprüfung pro Endpunkt; Ownership-Check für Nutzerin; Visibility-Filter für Kommentare/Anhänge; Audit-Logging.

## 6. Datenmodell (Django/PostgreSQL)
- **Modelle:**
  - `User` (re-use vorhandenes Modell; Rollenfeld `role` mit Choices `customer`, `agent`, `admin`).
  - `Ticket`:
    - `subject` (CharField, 200), `description` (TextField), `category` (CharField, choices), `priority` (Enum: low/medium/high/urgent), `status` (Enum: open/in_progress/waiting_on_customer/resolved/closed).
    - `requester` (FK User, related_name="tickets"), `assignee` (FK User null, related_name="assigned_tickets"), `resolution_text` (TextField null), `closed_at` (DateTime null).
    - Audit: `created_at`, `updated_at`, `created_by` (FK User), `updated_by` (FK User).
    - SLA Felder: `due_at` (DateTime, nullable), `queue` (CharField) optional.
  - `Comment`:
    - `ticket` (FK), `author` (FK User), `body` (TextField), `visibility` (Enum: public/internal), `status_change` (nullable status enum snapshot), `is_system` (bool default False).
    - Audit: `created_at`, `updated_at`.
  - `Attachment`:
    - `ticket` (FK), optional `comment` (FK), `uploader` (FK User), `file_name`, `content_type`, `size`, `storage_key`, `checksum`.
    - Audit: `created_at`.
- **Relationen:** Ticket 1:n Comment, Ticket 1:n Attachment, Comment 1:n Attachment (optional); User 1:n Ticket (requester/assignee).
- **Validierungen:**
  - `priority`, `status`, `visibility` als Choices/Enum.
  - Status-Transitions: erlaubt z. B. `open → in_progress → waiting_on_customer → in_progress → resolved → closed`; `closed` nur durch Support/Admin.
  - `resolution_text` Pflicht bei Abschluss; `assignee` Pflicht vor Wechsel auf `in_progress`.
  - Anhänge: Max-Größe je File, erlaubte MIME-Typen, Virenscan-Hook.

## 7. Akzeptanzkriterien
- **Funktional:**
  - Nutzerin kann Ticket inkl. Anhang anlegen und danach Status/Verlauf sehen.
  - Support kann Ticket übernehmen, kommentieren (öffentlich/intern) und Status führen.
  - Abschluss sendet Benachrichtigung an Nutzerin und erzwingt Lösungstext.
  - Kommentare/Anhänge respektieren Sichtbarkeit.
  - Filter/Suche nach Status, Kategorie, Priorität, SLA-Due.
- **Barrierefreiheit:** WCAG 2.1 AA: Tastaturnutzung, Kontrast, Screenreader-Labels; Fokusreihenfolge in Formularen.
- **Security:** AuthN via JWT/OAuth2, AuthZ per Rolle/Ownership, CSRF-Schutz für Session-basiertes Frontend, Rate Limiting, Logging, Virenscan für Uploads, PII-Minimierung, Lösch-/Anonymisierungsroutinen.
- **Validierung:** serverseitige Feld-Validierung, klare Fehlermeldungen, Upload-Validierung (Typ/Größe), Status-Transitions geprüft.

## 8. Implementierungsstrategie: Monolith + API-first
- **Startarchitektur:** Django-Monolith mit gemeinsamem Repo für Backend und ein schlankes Frontend (SPA oder SSR) als erste Grundkomponente.
- **Auth/Identität zuerst:** Login/Signup/SSO-Flow, Session-Handling oder JWT-basierte Authentifizierung, Rollenverwaltung, Passwort-Reset/SSO-Callback als erste lauffähige Strecke.
- **API-first:** REST-Schnittstellen von Anfang an versioniert (`/api/v1/...`), klare Trennung von API- und HTML-Routes, OpenAPI-Schema, damit spätere Module (Mobile App, Integrationen) sofort andocken können.
- **Modularisierung im Monolithen:** Django-Apps für `accounts`, `tickets`, `notifications`, `attachments`; saubere Service-Layer/Serializers, damit bei Bedarf Teile in Services ausgelagert werden können.
- **Deployment:** Ein Artefakt (Container) für MVP; späteres Aufbrechen in Services möglich, da API stabil bleibt.

## 9. MVP Taskliste
- **Backend (Django):**
  0. **Auth-Basis:** User-Modell (Rollen), JWT/Session-Login, Refresh/Logout, Passwort-Reset oder SSO-Stub, einfache "whoami"-Route.
  1. Modelle + Migrations: Ticket, Comment, Attachment inkl. Choices, Auditfelder.
  2. Serializer + Permissions: rollen- & ownership-basiert; Visibility-Filter für Comments/Attachments.
  3. Views/ViewSets + URLs: Tickets (CRUD/PATCH), Comments (create/list), Attachments (create/list), Close-Endpoint.
  4. Services/Hooks: Status-Transition-Validator, Attachment-Storage-Adapter, Notification-Signal (Webhook/Email Stub).
  5. Tests: Modellvalidierung, Permissions, Status-Transitions, API-Endpunkte.
- **Frontend:**
  0. **Login-Flow:** Login-Formular (JWT/Session), Token/Session-Storage, Basis-Guarding für geschützte Routen, einfache Profil-/Logout-UI.
  1. Ticket-Formular (subject, description, category, priority, attachments upload-token-Handling).
  2. Ticket-Liste + Filter; Detailseite mit Verlauf (Kommentare/Statushistorie) und Antwortformular.
  3. Agent-Queue-Ansicht; Aktionen: Zuweisen, Status ändern, internen/öffentlichen Kommentar erstellen.
  4. API-Client-Layer (auth bearer token, error handling); Basic Notification UI (toasts).
- **Reihenfolge & minimale Lieferfähigkeit:**
  1. Auth-Strecke: Login/Logout + geschützte Basisroute (Dashboard) lauffähig.
  2. Backend Basis: Modelle + Ticket-Create/List/Detail + Comment Create/List (public) → ermöglicht End-to-End Anlage + Anzeige.
  3. Frontend Basis: Ticket-Formular + Detailansicht mit Kommentaren → Nutzerin kann Tickets erstellen und lesen (nach Login).
  4. Agent-Funktionen: Statuswechsel, interne Kommentare, Queue-Filter.
  5. Anhänge & Benachrichtigung: Upload/Download, Webhook/Email Stub.
  6. Hardening: Permissions, SLA/Due-Handling, Audit/Logging, Security/Rate Limiting.
