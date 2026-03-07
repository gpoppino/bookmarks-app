from fastapi import FastAPI, HTTPException, Depends, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Table, ForeignKey, or_
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship

from jose import JWTError, jwt
import bcrypt as bcrypt_lib

# ==========================================
# DATABASE SETUP
# ==========================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./bookmarks.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# AUTH CONFIG
# ==========================================
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

# ==========================================
# MODELS
# ==========================================
bookmark_tag_association = Table(
    'bookmark_tag', Base.metadata,
    Column('bookmark_id', Integer, ForeignKey('bookmarks.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    bookmarks = relationship("BookmarkDB", back_populates="user")

class TagDB(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class BookmarkDB(Base):
    __tablename__ = "bookmarks"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("UserDB", back_populates="bookmarks")
    tags = relationship("TagDB", secondary=bookmark_tag_association, backref="bookmarks")

Base.metadata.create_all(bind=engine)

# ==========================================
# FASTAPI APP
# ==========================================
app = FastAPI(title="Bookmarks API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# SCHEMAS
# ==========================================
class BookmarkRequest(BaseModel):
    url: str
    tags: List[str] = []

class UserRegisterRequest(BaseModel):
    username: str
    password: str

class UserLoginRequest(BaseModel):
    username: str
    password: str

# ==========================================
# HELPERS
# ==========================================
def hash_password(password: str) -> str:
    return bcrypt_lib.hashpw(password.encode(), bcrypt_lib.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt_lib.checkpw(plain.encode(), hashed.encode())

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + expires_delta
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)) -> UserDB:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def fetch_bookmark_metadata(url: str) -> dict:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title_tag = soup.find('title')
        title = title_tag.string.strip() if title_tag and title_tag.string else "No title found"

        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc:
            meta_desc = soup.find('meta', attrs={'property': 'og:description'})
        description = meta_desc['content'].strip() if meta_desc and meta_desc.get('content') else "No description available"

        return {"success": True, "url": url, "title": title, "description": description}
    except requests.exceptions.RequestException as e:
        return {"success": False, "url": url, "error": str(e)}

def serialize_bookmark(b: BookmarkDB) -> dict:
    return {
        "id": b.id,
        "url": b.url,
        "title": b.title,
        "description": b.description,
        "created_at": b.created_at,
        "tags": [t.name for t in b.tags]
    }

# ==========================================
# AUTH ENDPOINTS
# ==========================================

@app.post("/api/auth/register", status_code=201)
async def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(UserDB).filter(UserDB.username == request.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")
    user = UserDB(
        username=request.username,
        hashed_password=hash_password(request.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "created_at": user.created_at}


@app.post("/api/auth/login")
async def login(request: UserLoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == request.username).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS),
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
    return {"id": user.id, "username": user.username, "created_at": user.created_at}


@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"success": True}


@app.get("/api/auth/me")
async def me(current_user: UserDB = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "created_at": current_user.created_at}


# ==========================================
# ENDPOINTS
# ==========================================

@app.get("/api/bookmarks")
async def get_bookmarks(
    skip: int = 0,
    limit: int = 50,
    tag: Optional[str] = Query(None, description="Filter by tag name"),
    search: Optional[str] = Query(None, description="Search in title, description, or URL"),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    query = db.query(BookmarkDB).filter(BookmarkDB.user_id == current_user.id)

    if tag:
        query = query.filter(BookmarkDB.tags.any(TagDB.name == tag.lower()))

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                BookmarkDB.title.ilike(term),
                BookmarkDB.description.ilike(term),
                BookmarkDB.url.ilike(term),
            )
        )

    bookmarks = (
        query
        .order_by(BookmarkDB.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [serialize_bookmark(b) for b in bookmarks]


@app.post("/api/bookmarks", status_code=201)
async def create_bookmark(
    request: BookmarkRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    existing = db.query(BookmarkDB).filter(
        BookmarkDB.url == request.url,
        BookmarkDB.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bookmark already exists")

    metadata = fetch_bookmark_metadata(request.url)
    if not metadata["success"]:
        raise HTTPException(status_code=400, detail=metadata["error"])

    new_bookmark = BookmarkDB(
        url=metadata["url"],
        title=metadata["title"],
        description=metadata["description"],
        user_id=current_user.id,
    )

    for tag_name in request.tags:
        clean_tag = tag_name.strip().lower()
        if not clean_tag:
            continue
        db_tag = db.query(TagDB).filter(TagDB.name == clean_tag).first()
        if not db_tag:
            db_tag = TagDB(name=clean_tag)
        new_bookmark.tags.append(db_tag)

    db.add(new_bookmark)
    db.commit()
    db.refresh(new_bookmark)

    return serialize_bookmark(new_bookmark)


@app.delete("/api/bookmarks/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    bookmark = db.query(BookmarkDB).filter(
        BookmarkDB.id == bookmark_id,
        BookmarkDB.user_id == current_user.id
    ).first()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(bookmark)
    db.commit()

    return {"success": True, "message": f"Bookmark {bookmark_id} deleted"}


@app.get("/api/tags")
async def get_all_tags(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    user_bookmarks = db.query(BookmarkDB).filter(BookmarkDB.user_id == current_user.id).all()
    seen = {}
    for b in user_bookmarks:
        for t in b.tags:
            seen[t.id] = t
    tags = sorted(seen.values(), key=lambda t: t.name)
    return [{"id": t.id, "name": t.name} for t in tags]


@app.get("/health")
async def health_check():
    return {"status": "ok"}
