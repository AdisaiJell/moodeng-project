from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "user"

    userId = Column(Integer, primary_key=True)
    userName = Column(String)
    email = Column(String, unique=True)
    image = Column(String, server_default="default_image.jpg")
    roleId = Column(Integer, ForeignKey("role.roleId"))
    factId = Column(Integer, ForeignKey("faction.factId", ondelete="SET NULL"))  
    role = relationship("Role", back_populates="users")
    faction = relationship("Faction", back_populates="users", passive_deletes=True)

