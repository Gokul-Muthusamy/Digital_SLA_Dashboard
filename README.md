# Digital SLA Compliance Dashboard

## Project Overview

The Digital SLA Compliance Dashboard is a role-based web application developed using Flask and SQLite to monitor, track, and manage service tickets with real-time Service Level Agreement (SLA) compliance. The system automates SLA monitoring, generates warning and breach alerts, and provides analytical dashboards to support effective service management.

This project is developed as a final-year academic project with a focus on real-time monitoring, automation, and professional dashboard design.

---

## Aim

To design and develop a web-based system that enables real-time SLA monitoring, automated alert generation, and performance analytics for service ticket management.

---

## Objectives

- Implement role-based authentication for User, Support, and Manager roles  
- Enable users to raise service tickets with defined SLA limits  
- Track ticket status and SLA compliance in real time  
- Generate automated SLA warning and breach alerts  
- Maintain alert history for auditing and analysis  
- Provide interactive dashboards for SLA monitoring  
- Ensure a responsive and professional user interface  

---

## User Roles and Functionalities

### User
- Raise service tickets  
- View ticket status and SLA progress  

### Support
- View open tickets  
- Resolve tickets  
- Update ticket status  

### Manager
- Monitor overall SLA compliance  
- View analytics dashboards  
- Track SLA met and breached tickets  
- View alert history  
- Monitor live SLA countdown timers  

---

## Key Features

- Role-based login system  
- Real-time SLA countdown (HH:MM:SS)  
- Color-coded SLA status indicators  
- Automated email alerts for SLA warning and breach  
- Persistent alert history  
- Interactive data visualization using Chart.js  
- Open vs Closed ticket analysis  
- SLA compliance monitoring dashboard  

---

## Technology Stack

### Frontend
- HTML  
- CSS  
- Bootstrap  
- JavaScript  
- Chart.js  

### Backend
- Python  
- Flask Framework  

### Database
- SQLite  

### Email Service
- SMTP (Gmail)  

---

## Database Design

### Users Table
- id (Primary Key)  
- username  
- password  
- role  

### Tickets Table
- id (Primary Key)  
- title  
- description  
- created_time  
- resolved_time  
- sla_hours  
- status  
- sla_status  
- raised_by  

### Alerts Table
- id (Primary Key)  
- ticket_id (Foreign Key)  
- alert_type (WARNING / BREACH)  
- alert_time  

---

## System Architecture

User / Support / Manager  
-> Web User Interface  
-> Flask Backend  
-> SQLite Database  
-> SLA Processing Logic  
-> Dashboard Visualization (Chart.js)  
-> Email Notification System 

<img width="1277" height="851" alt="image" src="https://github.com/user-attachments/assets/a8ba599d-6a94-4e19-a1e2-c54a9061233e" />

---

## Project Structure

Digital_SLA_Compliance_Dashboard/  
|-- backend/  
|   |-- app.py  
|   |-- init_db.py  
|   |-- insert_users.py  
|   |-- reset_database.py  
|   |-- database.db  
|   |-- routes/  
|-- frontend/  
|   |-- static/  
|   |-- templates/  
|-- requirements.txt  
|-- .env.example  
|-- README.md  
|-- .gitignore


Note: The database file (`backend/database.db`) is generated automatically during execution and is ignored in version control.

---

## Installation and Execution Steps

### Step 1: Clone the Repository
git clone https://github.com/Gokul-Muthusamy/Digital_SLA_dashboard.git
### Step 2: Navigate to Project Directory 
cd Digital_SLA_Compliance_Dashboard
### Step 3: Install Required Dependencies
pip install -r requirements.txt
### Step 4: Run the Application
python backend/app.py
### Step 5: Access the Application
Open a web browser and navigate to:

http://127.0.0.1:5000

---

## Public Deployment Notes

This project can be deployed publicly as a Flask web app.

### Recommended Hosting Pattern
- Host the Flask app on a Python web service
- Set environment variables for secrets and alerts
- Store the SQLite database on persistent disk storage

### Render Deployment
This repository includes a `render.yaml` file for Render deployment.

Required environment values:
- `FLASK_SECRET_KEY`
- `ALERT_DEFAULT_RECIPIENTS`

The database path is configured through:
- `DATABASE_PATH=/tmp/database.db`

Optional:
- `SEED_DEMO_USERS=true`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_IDS`

Note:
- The included `render.yaml` is configured for Render's free web tier
- Free Render services use an ephemeral filesystem, so SQLite data is reset whenever the service restarts or redeploys
- If you need persistent data on Render, switch to PostgreSQL or upgrade to a paid instance with a persistent disk
- Free Render services cannot send mail over SMTP ports such as `25`, `465`, or `587`
- Telegram bot alerts work on free Render by setting `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_IDS`

### Important
- Do not deploy with demo secrets or personal email passwords inside source code
- SQLite is acceptable for a small academic/demo deployment, but PostgreSQL is better for long-term production use
- If you redeploy without persistent disk storage, your data can be lost

---

## Demo Login Credentials

The following sample credentials are provided for demonstration and testing purposes.

### User
- Username: user1
- Password: user123

### Support
- Username: support1
- Password: support123

### Manager
- Username: manager1
- Password: manager123

---

### Database Reset (For Testing)
To clear all ticket and alert data:

python backend/reset_database.py










