# Satge 1: Backend
The Mental Model First
Before writing a single line, here's how a backend developer thinks about this system:
Your backend is a data pipeline with rules. A request comes in → validate the shape of the data → run business logic → talk to the database → send back a response. Every file has exactly one job:

config.py — knows secrets
session.py — knows how to talk to the database
models/ — knows what the database tables look like
schemas/ — knows what data is allowed in and out of the API
services/ — knows the business rules (breach timers, ID generation, status logic)
api/ — knows which URL triggers which service function

Think of it like a restaurant: the router (api/) is the waiter, the service is the chef, the model is the recipe, the database is the pantry.
About Docker in this project specifically: You have PostgreSQL running inside a Docker container. Your FastAPI backend runs in your WSL2 terminal (not in Docker yet — we add that in Stage 4). Docker here is purely playing the role of "give me a database without installing PostgreSQL on my machine." When you run docker compose up -d, Docker reads docker-compose.yml, downloads the PostgreSQL image if it doesn't have it, starts a container, and exposes port 5432. Your FastAPI app connects to it exactly like it would connect to any PostgreSQL server — it doesn't know or care that it's inside a container.

Step 1 — docker-compose.yml (root of project)
Do this first. The database must exist before anything else can connect to it.Read the generated doc for referenceRead the generated doc for referenceGood. Now I have everything I need. Let me write all the files.Created 4 files, ran 2 commandsCreated 4 files, ran 2 commandsStep 2 — core/config.py
The thinking here: every secret or environment-specific value (database URL, secret key) lives in .env. Config.py reads that file once at startup and makes it available everywhere. If you hardcode localhost:5432 into 10 different files, changing it later is a nightmare. One config file means one place to change.Core/config.py — reads .env and exposes settingsCore/config.py — reads .env and exposes settingsStep 3 — db/base.py and db/session.py
base.py is the foundation all models inherit from. session.py creates the connection pool to PostgreSQL and a factory function that gives each request its own database session — and closes it cleanly when the request is done.Created 2 filesCreated 2 filesStep 4 — Models
The thinking: models are a 1-to-1 translation of your spec document into Python classes. Each class = one database table. Each class attribute = one column. The foreign key on StatusHistory pointing to TaskChunk is what lets you query "give me all history entries for REF-0042".Created 3 filesCreated 3 filesStep 5 — Alembic Setup
Alembic is a migration tool. Think of it as Git for your database schema. Every time you change a model, you generate a migration file that describes the change. Running alembic upgrade head applies all pending migrations to the real database. This means you never manually run CREATE TABLE SQL — Python generates it for you.Created 3 files, ran a commandCreated 3 files, ran a commandStep 6 — Schemas (Pydantic)
Schemas are the API's contract. A model defines what's in the database. A schema defines what's allowed through the API door. They look similar but serve completely different purposes. TaskChunkCreate says "here's what I accept from the user." TaskChunkRead says "here's what I send back." Never expose raw database models through the API — schemas give you control.Created 2 filesCreated 2 filesStep 7 — Services
This is the most important file. Services are where your spec document's rules live as code. The router just calls a service function. The service function does the real thinking: generate the REF-XXXX ID, set status, write history, check breach timers.Services/task_service.py — all business logicServices/task_service.py — all business logicContinue5:13 PMStep 8 — API RoutesCreated 2 filesCreated 2 filesStep 9 — main.py
This is the entry point. Think of it as the front door of your application — it creates the FastAPI app, registers all the routers, starts the background scheduler for breach checking, and creates database tables on first startup.Main.py — FastAPI application entry pointMain.py — FastAPI application entry pointStep 10 — requirements.txtRequirements.txt — all Python dependenciesRequirements.txt — all Python dependenciesNow let's write all the frontend files.