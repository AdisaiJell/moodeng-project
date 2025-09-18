from sqlalchemy import Column, ForeignKey, Integer, String, ARRAY, Date 
from sqlalchemy.orm import relationship
from database import Base

class Meta(Base):
    __tablename__ = "meta"

    metaId = Column(Integer, primary_key=True)
    factionName = Column(String)
    typeName = Column(String)
    publishedDate = Column(Date)
    effectiveDate = Column(Date)
    keyword = Column(ARRAY(String))  
    relateddoc = Column(ARRAY(String))

    factId = Column(Integer, ForeignKey("faction.factId"))  
    typeId = Column(Integer, ForeignKey("type.typeId"))  
    faction = relationship("Faction", back_populates='meta')  
    type = relationship("Type", back_populates='meta')  
    document = relationship("Document", back_populates="meta") 
