from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class Role(Base):
    __tablename__ = "role"

    roleId = Column(Integer, primary_key=True)
    roleName = Column(String)
    users = relationship("User", back_populates="role")

