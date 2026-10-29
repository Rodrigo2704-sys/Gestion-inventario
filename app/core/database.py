import os
from dotenv import load_dotenv
from sqlalchemy  import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base,sessionmaker

load_dotenv()

DB_HOST=os.getenv("BD_HOST","localhost")
DB_USER=os.getenv("DB_USER","root")
DB_PASSWORD=os.getenv("DB_PASSWORD","")
DB_NAME=os.getenv("DB_NAME","GestionVentas")
DB_PORT=int(os.getenv("DB_PORT",3306))

DATABASE_URL=URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    query={"charset":"utf8mb4"},
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # comprueba la conexión antes de usarla
    pool_recycle=1800,    # MySQL cierra conexiones inactivas; se renuevan cada 30 min
)
 
 #Definimos como sera el proceso de las peticiones al backend, Hasta que toda la lógica del backend termine sin ningún error, los datos no se guardan definitivamente en la base de datos.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
 
Base = declarative_base()
 
 
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()