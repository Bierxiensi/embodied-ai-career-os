# Technical Design


## Architecture


User


↓

Next.js


↓

FastAPI


↓

Agent Layer


↓

Database



---

# Components


## Frontend


Next.js

负责：

- Dashboard
- Skill visualization
- Task


---

## Backend


FastAPI

负责：

- API
- Business Logic


---

## Agent


LangGraph


Agents:


Supervisor

Career Agent

Planner Agent

Reviewer Agent


---

## Database


PostgreSQL


Tables:


users

career_goal

skills

tasks

projects

learning_logs



---

# Deployment


Docker Compose


Services:


frontend

backend

postgres

redis

chromadb
