import time
from database import Base,DATABASE_URL,SessionLocal
from sqlalchemy import create_engine
from models import *
from controllers import role_controller, type_controller, faction_controller, user_controller
from schemas import RoleCreate, TypeCreate, FactionCreate, UserCreate

MAX_RETRIES = 30
SLEEP_INTERVAL = 2

def wait_for_db_ready():
    engine = create_engine(DATABASE_URL)
    for i in range(MAX_RETRIES):
        try:
            conn = engine.connect()
            conn.close()
            print("Database is ready.")
            return engine
        except Exception as e:
            print(f"Waiting for database... ({i + 1}/{MAX_RETRIES})")
            time.sleep(SLEEP_INTERVAL)
    raise Exception("❌ Database is not ready after retries.")

def init_db():
    engine = wait_for_db_ready()
    Base.metadata.create_all(bind=engine)
    db_session = SessionLocal()
    try:
        # add role
        roles:RoleCreate = []
        admin = RoleCreate(roleId=1, roleName='admin')
        staff = RoleCreate(roleId=2, roleName='staff')
        roles.extend([admin, staff])
        for role in roles:   
            role_controller.create_role(db_session, role)
            
        # add type
        types:TypeCreate = []
        type1 = TypeCreate(typeId=1, typeName='ข้อบังคับ')
        type2 = TypeCreate(typeId=2, typeName='ระเบียบ')
        type3 = TypeCreate(typeId=3, typeName='ประกาศ')
        types.extend([type1, type2, type3])
        for type in types:   
            type_controller.create_type(db_session, type)
            
        # add Faction
        factions:FactionCreate = []
        faction1 = FactionCreate(factId=1, factionName='กองคลัง')
        faction2 = FactionCreate(factId=2, factionName='มหาวิทยาลัย')
        faction3 = FactionCreate(factId=3, factionName='กองทะเบียน')
        factions.extend([faction1, faction2, faction3])
        for faction in factions:   
            faction_controller.create_faction(db_session, faction)
    except Exception as e:
        print("Error: ", e)
        db_session.rollback()
    finally:
        try:
            # add User
            image = "default_image.jpg"
            users: UserCreate = []
            user1 = UserCreate(userName="Jell", email="65160311@go.buu.ac.th", roleId=1, factId=1)
            user2 = UserCreate(userName="Phone", email="65160149@go.buu.ac.th", roleId=1, factId=1)
            user3 = UserCreate(userName="Nut", email="65160165@go.buu.ac.th", roleId=1, factId=1)
            user4 = UserCreate(userName="Praew", email="65160083@go.buu.ac.th", roleId=1, factId=1)
            user5 = UserCreate(userName="Mind", email="65160082@go.buu.ac.th", roleId=1, factId=1)
            user6 = UserCreate(userName="Bright", email="65160171@go.buu.ac.th", roleId=1, factId=1)
            user7 = UserCreate(userName="Eing", email="65160313@go.buu.ac.th", roleId=1, factId=1)
            users.extend([user1, user2, user3, user4, user5, user6, user7])
            for user in users:
                user_controller.create_user(db_session, user, image)
        except Exception as e:
            print("Error: ", e)
        finally:
            db_session.close()
 
 
 
init_db()

    