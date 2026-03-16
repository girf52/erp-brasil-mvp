from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from core.database import engine, Base, SessionLocal
from routers import health, auth, financeiro, vendas, fiscal, rh


def _seed_admin():
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    from models.user import User
    from core.security import hash_password
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "admin@erp.local").first():
            db.add(User(email="admin@erp.local", nome="Administrador", senha_hash=hash_password("admin123")))
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_admin()
    yield


app = FastAPI(title="ERP Brasil MVP", version="0.1.0", docs_url="/api/docs", redoc_url="/api/redoc", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api/auth")
app.include_router(financeiro.router)
app.include_router(vendas.router)
app.include_router(fiscal.router)
app.include_router(rh.router)
