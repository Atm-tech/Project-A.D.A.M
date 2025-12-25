from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class OutletAlias(BaseModel):
    alias_id: int
    alias_name: str

    class Config:
        from_attributes = True


class OutletBase(BaseModel):
    outlet_name: str = Field(..., examples=["Big Bazaar Chennai"])
    city: Optional[str] = Field(default=None, examples=["Chennai"])
    state: Optional[str] = Field(default=None, examples=["Tamil Nadu"])
    is_active: bool = True


class OutletCreate(OutletBase):
    aliases: List[str] = []


class OutletUpdate(OutletBase):
    aliases: List[str] = []


class OutletOut(OutletBase):
    outlet_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    aliases: List[OutletAlias] = []

    class Config:
        from_attributes = True
