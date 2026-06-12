import os
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import models
import ai_service
from database import engine, get_db
import bcrypt

load_dotenv()

#-------------------------------------------
#              Bootstrap 
#-------------------------------------------

models.Base.metadata.create_all(bind = engine)
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "change-me-in-production-please"))

# Enforce clean absolute directory path mechanics for production stability
base_dir = os.path.dirname(os.path.abspath(__file__))

# Configure absolute pathing for templates
templates = Jinja2Templates(directory=os.path.join(base_dir, "templates"))

# Configure absolute pathing for static files (CSS, animations)
static_dir = os.path.join(base_dir, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


#-------------------------------------------
#           Authentication helpers 
#-------------------------------------------

def hash_password(plain: str) -> str:
    password_bytes = plain.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def get_current_user(request: Request, db: Session) -> models.User | None:
    """Returns the logged-in User object or None if the session is invalid"""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(models.User).filter(models.User.id == user_id).first()


#-------------------------------------------
#           Root / Dashboard 
#-------------------------------------------

@app.get("/", response_class = HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code = 302)

    review_sessions = (
        db.query(models.ReviewSession)
        .filter(models.ReviewSession.user_id == user.id)
        .order_by(models.ReviewSession.id.desc())
        .all()
    )

    return templates.TemplateResponse(
        request = request,
        name = "index.html",
        context = {
            "user": user,
            "sessions": review_sessions,
        },
    )


#-------------------------------------------
#           Registration 
#-------------------------------------------

@app.get("/register", response_class = HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request = request,
        name = "register.html",
        context = {"error": ""},
    )


@app.post("/register", response_class = HTMLResponse)
async def register_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(models.User)
        .filter((models.User.username == username) | (models.User.email == email))
        .first()
    )

    if existing:
        return templates.TemplateResponse(
            request = request,
            name = "register.html",
            context = {"error": "Username or email already in use."},
        )

    new_user = models.User(
        username = username,
        email = email,
        hashed_password = hash_password(password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    request.session["user_id"] = new_user.id
    return RedirectResponse("/", status_code = 302)


#-------------------------------------------
#           Login 
#-------------------------------------------

@app.get("/login", response_class = HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request = request,
        name = "login.html",
        context = {"error": ""},
    )


@app.post("/login", response_class = HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.username == username).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request = request,
            name = "login.html",
            context = {"error": "Invalid username or password"},
        )

    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=302)


#-------------------------------------------
#          Logout
#-------------------------------------------

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code = 302)


#-------------------------------------------
#          AI Submit
#-------------------------------------------

@app.post("/submit")
async def submit_issue(
    request: Request,
    language: str = Form(...),
    issue_description: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code = 302)

    review = models.ReviewSession(
        user_id = user.id,
        language = language,
        issue_description = issue_description,
        ai_status = "PENDING",
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    try:
        result = ai_service.analyze_issue(language, issue_description)
        review.ai_category = result["category"]
        review.ai_difficulty = result["difficulty"]
        review.ai_recommendation = result["recommendation"]
        review.ai_status = "SUCCESS"

    except Exception as e:
        review.ai_status = "FAILED"
        review.error_message = str(e)

    db.commit()
    return RedirectResponse("/", status_code = 302)