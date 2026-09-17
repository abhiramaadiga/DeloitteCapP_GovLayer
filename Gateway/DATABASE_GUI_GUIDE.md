# PostgreSQL Database GUI Web Viewers — Guide for Mentors & Evaluators

**Project**: Zero-Trust Agentic-AI Identity & Access Governor (BFSI Retail Banking)  
**Team**: The dab hands | PES University — Deloitte Capstone 2026  
**System of Record**: PostgreSQL 16 (`governance_db` on port `5432`)

---

## Quick Reference Summary

| Interface | URL | Login / Auth | Best Used For |
| :--- | :--- | :--- | :--- |
| **pgweb** (Recommended) | [http://localhost:8081](http://localhost:8081) | **Zero Login (Instant)** | **Mentor demo & immediate table/row inspection** — 1-click access |
| **pgAdmin 4** | [http://localhost:5050](http://localhost:5050) | Desktop Mode / `admin@deloitte.com` | Traditional enterprise DBA management and tree navigation |

---

## 1. Option 1: Instant Zero-Login Viewer (pgweb) — *Recommended for Demo*

**pgweb** is an ultra-fast, lightweight web-based PostgreSQL explorer running directly inside the Docker cluster. It is configured to automatically connect to `governance_db` on boot without prompting for credentials.

### Access URL
👉 **[http://localhost:8081](http://localhost:8081)**

### How to View Tables & Rows
1. Open your browser and navigate to **`http://localhost:8081`**.
2. Notice the left sidebar — all three project tables are immediately visible:
   - `audit_logs`: Live SOX-404, PCI-DSS, and Explainable AI (XAI) security decisions.
   - `banking_accounts`: Core banking balances (Rahul Sharma, Priya Patel, Vikram Malhotra).
   - `conversations`: Human-to-Agent prompts, responses, and RLHF flags.
3. **Click on any table name** in the left sidebar:
   - The right panel immediately loads all rows and columns in a clean spreadsheet-style grid.
   - View column data types, total row counts, and page through records.
4. **Ad-hoc SQL Queries**:
   - Click the **"Query"** tab at the top.
   - Execute queries like:
     ```sql
     SELECT * FROM audit_logs ORDER BY id DESC;
     SELECT * FROM banking_accounts;
     ```

---

## 2. Option 2: Enterprise pgAdmin 4 Interface

For mentors who specifically prefer the standard **pgAdmin 4** interface, pgAdmin 4 is containerized and pre-configured with auto-discovery so that the PostgreSQL cluster is automatically registered.

### Access URL
👉 **[http://localhost:5050](http://localhost:5050)**

### Credentials & Connection Details
- **pgAdmin Mode**: Desktop Mode (`PGADMIN_CONFIG_SERVER_MODE: False`) — Zero-login web interface
- **Pre-Registered Server Name**: `PostgreSQL Governor DB (governance_db)`
- **Host**: `postgres` (internal Docker network) / `localhost` (from host machine)
- **Port**: `5432`
- **Database User**: `governor_admin`
- **Database Name**: `governance_db`
- **Pre-Loaded Password**: `deloitte_secure_pass` (pre-configured in `.pgpass`, auto-authenticated)

### How to View Tables & Rows in pgAdmin
1. Open **`http://localhost:5050`** in your browser.
2. In the left **Object Explorer tree**, expand:
   ```text
   Servers
     └── PostgreSQL Governor DB (governance_db)
           └── Databases
                 └── governance_db
                       └── Schemas
                             └── public
                                   └── Tables
   ```
3. Because `.pgpass` is mounted and configured via `PGPASS_FILE`, pgAdmin connects directly without requiring manual password entry. (If prompted on legacy/first-time cached sessions, the password is `deloitte_secure_pass`).
4. Right-click on any table (`banking_accounts`, `audit_logs`, or `conversations`) and select:  
   **`View/Edit Data` ➔ `All Rows`**.
5. The data grid will open in the main panel displaying all rows and column values.

---

## 3. Pre-Populated Seed Data Verification

When viewing `banking_accounts`, the following seed records are pre-populated via `schema.sql`:

| account_id | customer_name | account_type | balance_inr | currency |
| :--- | :--- | :--- | :--- | :--- |
| `401` | Rahul Sharma | GOLD | ₹84,250.00 | INR |
| `402` | Priya Patel | PLATINUM | ₹312,400.00 | INR |
| `403` | Vikram Malhotra | SILVER | ₹15,000.00 | INR |

When transactions or agent chat requests are processed through the Zero-Trust Gateway PEP, new records are dynamically created in `audit_logs` and `conversations`.

---

## 4. How to Start the Services

From the project root (`D:\Work\Deloite_Capstone_Project\Gateway`):

```bash
# Start all infrastructure services including database and both GUI viewers:
docker compose up -d

# Or start only PostgreSQL and the GUI viewers:
docker compose up -d postgres pgweb pgadmin
```

To stop the services:
```bash
docker compose down
```
